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
from ._utils import MAX_RETRY_ATTEMPTS, build_url, get_backoff_duration, token
from .errors import error_handler

if TYPE_CHECKING:
    from collections.abc import Callable

    from ._client import Zotero
    from ._types import JsonDict


class Zupload:
    """Zotero file attachment helper.

    Receives a Zotero instance, file(s) to upload, and optional parent ID.
    """

    def __init__(
        self,
        zinstance: Zotero,
        payload: list[JsonDict],
        parentid: str | None = None,
        basedir: str | Path | None = None,
    ) -> None:
        super().__init__()
        self.zinstance = zinstance
        self.payload = payload
        self.parentid = parentid
        self.basedir = Path() if basedir is None else Path(basedir)

    def _check_response(self, req: httpx.Response) -> None:
        """Raise on HTTP error and record any server-supplied backoff."""
        try:
            req.raise_for_status()
        except httpx.HTTPError as exc:
            error_handler(self.zinstance, req, exc)
        backoff = get_backoff_duration(req.headers)
        if backoff:
            self.zinstance._set_backoff(backoff)

    def _post_with_retry(self, send: Callable[[], httpx.Response]) -> httpx.Response:
        """Issue a request via ``send``, retrying while the server rate-limits us.

        On 429, error_handler records the server's backoff instead of raising;
        _check_backoff waits it out before the next attempt. This stops a
        rate-limited step from being mistaken for a successful one (#352).
        """
        for _ in range(MAX_RETRY_ATTEMPTS):
            self.zinstance._check_backoff()
            req = send()
            self._check_response(req)
            if req.status_code != httpx.codes.TOO_MANY_REQUESTS:
                return req
        msg = f"Still rate-limited after {MAX_RETRY_ATTEMPTS} attempts. Try again later"
        raise ze.TooManyRetriesError(msg)

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

    @staticmethod
    def _outgoing(item: JsonDict) -> JsonDict:
        """Return a copy of an attachment item that's safe to send to the API.

        Zupload resolves ``filename`` against ``basedir`` in order to read the
        local file, so callers pass a path. The API rejects a stored-file item
        whose ``filename`` contains a directory path ("Stored-file filename
        cannot contain a directory path"), so the outgoing copy contains the
        basename only. See #341.
        """
        filename = item.get("filename")
        if not filename:
            return item
        return {**item, "filename": Path(filename).name}

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
        to_send = json.dumps([self._outgoing(item) for item in self.payload])
        req = self._post_with_retry(
            lambda: self.zinstance.client.post(
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
        )
        data = req.json()
        for k in data["success"]:
            self.payload[int(k)]["key"] = data["success"][k]
        return data

    def _get_auth(
        self, attachment: str, reg_key: str, md5: str | None = None
    ) -> dict[str, Any]:
        """Step 1: get upload authorisation for a file."""
        att_path = Path(attachment)
        stat = att_path.stat()
        mtypes = mimetypes.guess_type(attachment)
        digest = hashlib.md5()  # noqa: S324
        with att_path.open("rb") as att:
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
            "filename": att_path.name,
            "filesize": stat.st_size,
            "mtime": str(int(stat.st_mtime * 1000)),
            "contentType": mtypes[0] or "application/octet-stream",
            "charset": mtypes[1],
            "params": 1,
        }
        auth_req = self._post_with_retry(
            lambda: self.zinstance.client.post(
                url=build_url(
                    self.zinstance.endpoint,
                    f"/{self.zinstance.library_type}/{self.zinstance.library_id}/items/{reg_key}/file",
                ),
                data=data,
                headers=auth_headers,
            )
        )
        return auth_req.json()

    def _upload_file(
        self,
        authdata: dict[str, Any],
        attachment: str,
        reg_key: str,
        md5: str | None = None,
    ) -> None:
        """Step 2: auth successful, and file not on server.

        See zotero.org/support/dev/server_api/file_upload#a_full_upload

        reg_key and md5 aren't used here, but we pass them through to Step 3.
        """
        upload_dict = authdata["params"]
        # pass tuple of tuples (not dict!), to ensure key comes first
        upload_list = [("key", upload_dict.pop("key"))]
        for key, value in upload_dict.items():
            upload_list.append((key, value))
        upload_list.append(("file", Path(attachment).read_bytes()))
        upload_pairs = tuple(upload_list)

        def send() -> httpx.Response:
            # We use a fresh httpx POST because we don't want our existing Pyzotero headers
            # for a call to the storage upload URL (currently S3)
            try:
                return httpx.post(
                    url=authdata["url"],
                    files=upload_pairs,
                    headers={"User-Agent": f"Pyzotero/{pz.__version__}"},
                    timeout=self.zinstance.upload_timeout,
                )
            except httpx.ConnectError:
                msg = "ConnectionError"
                raise ze.UploadError(msg) from None
            except httpx.TimeoutException:
                msg = "Upload timed out. Try increasing upload_timeout when creating the Zotero instance."
                raise ze.UploadError(msg) from None

        self._post_with_retry(send)
        # now check the responses
        return self._register_upload(authdata, reg_key, md5=md5)

    def _register_upload(
        self, authdata: dict[str, Any], reg_key: str, md5: str | None = None
    ) -> None:
        """Step 3: upload successful, so register it.

        For a new file we send ``If-None-Match: *``; when replacing an existing
        file's contents we must instead send ``If-Match: <previous md5>``, matching
        the header used in Step 1. The Zotero API returns 412 otherwise (see #322).
        """
        reg_headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if md5:
            reg_headers["If-Match"] = md5
        else:
            reg_headers["If-None-Match"] = "*"
        reg_data = {"upload": authdata.get("uploadKey")}
        self._post_with_retry(
            lambda: self.zinstance.client.post(
                url=build_url(
                    self.zinstance.endpoint,
                    f"/{self.zinstance.library_type}/{self.zinstance.library_id}/items/{reg_key}/file",
                ),
                data=reg_data,
                headers=reg_headers,
            )
        )

    def upload(self) -> dict[str, list]:
        """File upload functionality.

        Goes through upload steps 0 - 3 (private class methods), and returns
        a dict noting success, failure, or unchanged
        (returning the payload entries with that property as a list for each status).

        Entries the server rejected at step 0 are returned under ``failure``
        with the server's reason attached as an ``error`` key.
        """
        result: dict[str, list] = {"success": [], "failure": [], "unchanged": []}
        prelim = self._create_prelim()
        rejected = prelim.get("failed") or {} if prelim else {}
        for idx, item in enumerate(self.payload):
            if "key" not in item:
                reason = rejected.get(str(idx))
                result["failure"].append({**item, "error": reason} if reason else item)
                continue
            attach = str(self.basedir.joinpath(item["filename"]))
            authdata = self._get_auth(attach, item["key"], md5=item.get("md5", None))
            # no need to keep going if the file exists
            if authdata.get("exists"):
                result["unchanged"].append(item)
                continue
            self._upload_file(authdata, attach, item["key"], md5=item.get("md5", None))
            result["success"].append(item)
        return result


__all__ = ["Zupload"]
