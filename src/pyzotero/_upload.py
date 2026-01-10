"""File upload functionality for Pyzotero.

This module contains the Zupload class for handling file attachments
and uploads to the Zotero API.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

import pyzotero as pz

from . import errors as ze
from ._utils import build_url, get_backoff_duration, token
from .errors import error_handler

if TYPE_CHECKING:
    from ._client import Zotero


class Zupload:
    """Zotero file attachment helper.

    Receives a Zotero instance, file(s) to upload, and optional parent ID.
    """

    def __init__(
        self,
        zinstance: Zotero,
        payload: list[dict],
        parentid: str | None = None,
        basedir: str | Path | None = None,
    ) -> None:
        super().__init__()
        self.zinstance = zinstance
        self.payload = payload
        self.parentid = parentid
        if basedir is None:
            self.basedir = Path()
        elif isinstance(basedir, Path):
            self.basedir = basedir
        else:
            self.basedir = Path(basedir)

    def _verify(self, payload: list[dict]) -> None:
        """Ensure that all files to be attached exist.

        open()'s better than exists(), cos it avoids a race condition.
        """
        if not payload:  # Check payload has nonzero length
            raise ze.ParamNotPassedError
        for templt in payload:
            filepath = self.basedir.joinpath(templt["filename"])
            try:
                with filepath.open():
                    pass
            except OSError:
                msg = f"The file at {filepath!s} couldn't be opened or found."
                raise ze.FileDoesNotExistError(msg) from None

    def _create_prelim(self) -> dict | None:
        """Step 0: Register intent to upload files."""
        self._verify(self.payload)
        if "key" in self.payload[0] and self.payload[0]["key"]:
            if next((i for i in self.payload if "key" not in i), False):
                msg = "Can't pass payload entries with and without keys to Zupload"
                raise ze.UnsupportedParamsError(msg)
            return None  # Don't do anything if payload comes with keys
        # Set contentType for each attachment if not already provided
        for item in self.payload:
            if not item.get("contentType"):
                filepath = str(self.basedir.joinpath(item["filename"]))
                detected_type = mimetypes.guess_type(filepath)[0]
                item["contentType"] = detected_type or "application/octet-stream"
        liblevel = "/{t}/{u}/items"
        # Create one or more new attachments
        headers = {"Zotero-Write-Token": token(), "Content-Type": "application/json"}
        # If we have a Parent ID, add it as a parentItem
        if self.parentid:
            for child in self.payload:
                child["parentItem"] = self.parentid
        to_send = json.dumps(self.payload)
        self.zinstance._check_backoff()
        req = self.zinstance.client.post(
            url=build_url(
                self.zinstance.endpoint,
                liblevel.format(
                    t=self.zinstance.library_type,
                    u=self.zinstance.library_id,
                ),
            ),
            content=to_send,
            headers=headers,
        )
        try:
            req.raise_for_status()
        except httpx.HTTPError as exc:
            error_handler(self.zinstance, req, exc)
        backoff = get_backoff_duration(req.headers)
        if backoff:
            self.zinstance._set_backoff(backoff)
        data = req.json()
        for k in data["success"]:
            self.payload[int(k)]["key"] = data["success"][k]
        return data

    def _get_auth(
        self, attachment: str, reg_key: str, md5: str | None = None
    ) -> dict[str, Any]:
        """Step 1: get upload authorisation for a file."""
        mtypes = mimetypes.guess_type(attachment)
        digest = hashlib.md5()  # noqa: S324
        with Path(attachment).open("rb") as att:
            for chunk in iter(lambda: att.read(8192), b""):
                digest.update(chunk)
        auth_headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if not md5:
            auth_headers["If-None-Match"] = "*"
        else:
            # docs specify that for existing file we use this
            auth_headers["If-Match"] = md5
        data = {
            "md5": digest.hexdigest(),
            "filename": Path(attachment).name,
            "filesize": Path(attachment).stat().st_size,
            "mtime": str(int(Path(attachment).stat().st_mtime * 1000)),
            "contentType": mtypes[0] or "application/octet-stream",
            "charset": mtypes[1],
            "params": 1,
        }
        self.zinstance._check_backoff()
        auth_req = self.zinstance.client.post(
            url=build_url(
                self.zinstance.endpoint,
                f"/{self.zinstance.library_type}/{self.zinstance.library_id}/items/{reg_key}/file",
            ),
            data=data,
            headers=auth_headers,
        )
        try:
            auth_req.raise_for_status()
        except httpx.HTTPError as exc:
            error_handler(self.zinstance, auth_req, exc)
        backoff = get_backoff_duration(auth_req.headers)
        if backoff:
            self.zinstance._set_backoff(backoff)
        return auth_req.json()

    def _upload_file(
        self, authdata: dict[str, Any], attachment: str, reg_key: str
    ) -> None:
        """Step 2: auth successful, and file not on server.

        See zotero.org/support/dev/server_api/file_upload#a_full_upload

        reg_key isn't used, but we need to pass it through to Step 3.
        """
        upload_dict = authdata["params"]
        # pass tuple of tuples (not dict!), to ensure key comes first
        upload_list = [("key", upload_dict.pop("key"))]
        for key, value in upload_dict.items():
            upload_list.append((key, value))
        upload_list.append(("file", Path(attachment).open("rb").read()))
        upload_pairs = tuple(upload_list)
        try:
            self.zinstance._check_backoff()
            # We use a fresh httpx POST because we don't want our existing Pyzotero headers
            # for a call to the storage upload URL (currently S3)
            upload = httpx.post(
                url=authdata["url"],
                files=upload_pairs,
                headers={"User-Agent": f"Pyzotero/{pz.__version__}"},
            )
        except httpx.ConnectError:
            msg = "ConnectionError"
            raise ze.UploadError(msg) from None
        try:
            upload.raise_for_status()
        except httpx.HTTPError as exc:
            error_handler(self.zinstance, upload, exc)
        backoff = get_backoff_duration(upload.headers)
        if backoff:
            self.zinstance._set_backoff(backoff)
        # now check the responses
        return self._register_upload(authdata, reg_key)

    def _register_upload(self, authdata: dict[str, Any], reg_key: str) -> None:
        """Step 3: upload successful, so register it."""
        reg_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "If-None-Match": "*",
        }
        reg_data = {"upload": authdata.get("uploadKey")}
        self.zinstance._check_backoff()
        upload_reg = self.zinstance.client.post(
            url=build_url(
                self.zinstance.endpoint,
                f"/{self.zinstance.library_type}/{self.zinstance.library_id}/items/{reg_key}/file",
            ),
            data=reg_data,
            headers=reg_headers,
        )
        try:
            upload_reg.raise_for_status()
        except httpx.HTTPError as exc:
            error_handler(self.zinstance, upload_reg, exc)
        backoff = get_backoff_duration(upload_reg.headers)
        if backoff:
            self.zinstance._set_backoff(backoff)

    def upload(self) -> dict[str, list]:
        """File upload functionality.

        Goes through upload steps 0 - 3 (private class methods), and returns
        a dict noting success, failure, or unchanged
        (returning the payload entries with that property as a list for each status).
        """
        result: dict[str, list] = {"success": [], "failure": [], "unchanged": []}
        self._create_prelim()
        for item in self.payload:
            if "key" not in item:
                result["failure"].append(item)
                continue
            attach = str(self.basedir.joinpath(item["filename"]))
            authdata = self._get_auth(attach, item["key"], md5=item.get("md5", None))
            # no need to keep going if the file exists
            if authdata.get("exists"):
                result["unchanged"].append(item)
                continue
            self._upload_file(authdata, attach, item["key"])
            result["success"].append(item)
        return result


__all__ = ["Zupload"]
