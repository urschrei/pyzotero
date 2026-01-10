"""Zotero API client for Pyzotero.

This module contains the main Zotero class which provides methods for
interacting with the Zotero API.
"""

from __future__ import annotations

import copy
import json
import re
import time
from pathlib import Path, PurePosixPath
from urllib.parse import (
    parse_qs,
    parse_qsl,
    quote,
    unquote,
    urlencode,
    urlparse,
    urlunparse,
)

import httpx
import whenever
from httpx import Request

import pyzotero as pz

from . import errors as ze
from ._decorators import backoff_check, cleanwrap, retrieve, ss_wrap, tcache
from ._upload import Zupload
from ._utils import (
    DEFAULT_ITEM_LIMIT,
    DEFAULT_NUM_ITEMS,
    DEFAULT_TIMEOUT,
    ONE_HOUR,
    build_url,
    chunks,
    get_backoff_duration,
    merge_params,
    token,
)
from .errors import error_handler
from .filetransport import Client as File_Client

__author__ = "Stephan Hügel"
__api_version__ = "3"


class Zotero:
    """Zotero API methods.

    A full list of methods can be found here:
    http://www.zotero.org/support/dev/server_api
    """

    def __init__(
        self,
        library_id=None,
        library_type=None,
        api_key=None,
        preserve_json_order=False,
        locale="en-US",
        local=False,
        client=None,
    ):
        self.client = None
        """Store Zotero credentials"""
        if not local:
            self.endpoint = "https://api.zotero.org"
            self.local = False
        else:
            self.endpoint = "http://localhost:23119/api"
            self.local = True
        if library_id is not None and library_type:
            self.library_id = library_id
            # library_type determines whether query begins w. /users or /groups
            self.library_type = library_type + "s"
        else:
            err = "Please provide both the library ID and the library type"
            raise ze.MissingCredentialsError(err)
        # api_key is not required for public individual or group libraries
        self.api_key = api_key
        if preserve_json_order:
            import warnings  # noqa: PLC0415

            warnings.warn(
                "preserve_json_order is deprecated and will be removed in a future version. "
                "Python 3.7+ dicts preserve insertion order automatically.",
                DeprecationWarning,
                stacklevel=2,
            )
        self.locale = locale
        self.url_params = None
        self.tag_data = False
        self.request = None
        self.snapshot = False
        self.client = client or httpx.Client(
            headers=self.default_headers(),
            follow_redirects=True,
        )
        # these aren't valid item fields, so never send them to the server
        self.temp_keys = {"key", "etag", "group_id", "updated"}
        # determine which processor to use for the parsed content
        self.fmt = re.compile(r"(?<=format=)\w+")
        self.content = re.compile(r"(?<=content=)\w+")
        # JSON by default
        self.formats = {
            "application/atom+xml": "atom",
            "application/x-bibtex": "bibtex",
            "application/json": "json",
            "text/html": "snapshot",
            "text/plain": "plain",
            "text/markdown": "plain",
            "application/pdf; charset=utf-8": "pdf",
            "application/pdf": "pdf",
            "application/msword": "doc",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
            "application/zip": "zip",
            "application/epub+zip": "zip",
            "audio/mpeg": "mp3",
            "video/mp4": "mp4",
            "audio/x-wav": "wav",
            "video/x-msvideo": "avi",
            "application/octet-stream": "octet",
            "application/x-tex": "tex",
            "application/x-texinfo": "texinfo",
            "image/jpeg": "jpeg",
            "image/png": "png",
            "image/gif": "gif",
            "image/tiff": "tiff",
            "application/postscript": "postscript",
            "application/rtf": "rtf",
        }
        self.processors = {
            "bib": self._bib_processor,
            "citation": self._citation_processor,
            "bibtex": self._bib_processor,
            "bookmarks": self._bib_processor,
            "coins": self._bib_processor,
            "csljson": self._csljson_processor,
            "mods": self._bib_processor,
            "refer": self._bib_processor,
            "rdf_bibliontology": self._bib_processor,
            "rdf_dc": self._bib_processor,
            "rdf_zotero": self._bib_processor,
            "ris": self._bib_processor,
            "tei": self._bib_processor,
            "wikipedia": self._bib_processor,
            "json": self._json_processor,
            "html": self._bib_processor,
        }
        self.links = None
        self.self_link = {}
        self.templates = {}
        self.savedsearch = None
        # backoff handling: timestamp when backoff expires (0.0 = no backoff)
        self.backoff_until = 0.0

    def __del__(self):
        """Remove client before cleanup."""
        # this isn't guaranteed to run, but that's OK
        if c := self.client:
            c.close()

    @property
    def __version__(self):
        """Return the version of the pyzotero library."""
        return pz.__version__

    def _check_for_component(self, url, component):
        """Check a url path query fragment for a specific query parameter."""
        return bool(parse_qs(url).get(component))

    def _striplocal(self, url):
        """Remove the leading '/api' substring from urls if running in local mode."""
        if self.local:
            parsed = urlparse(url)
            purepath = PurePosixPath(unquote(parsed.path))
            newpath = "/".join(purepath.parts[2:])
            replaced = parsed._replace(path="/" + newpath)
            return urlunparse(replaced)
        return url

    def _set_backoff(self, duration):
        """Set backoff expiration time."""
        self.backoff_until = time.time() + float(duration)

    def _check_backoff(self):
        """Wait if backoff is active."""
        remainder = self.backoff_until - time.time()
        if remainder > 0.0:
            time.sleep(remainder)

    def default_headers(self):
        """Return headers that are always OK to include."""
        _headers = {
            "User-Agent": f"Pyzotero/{pz.__version__}",
            "Zotero-API-Version": f"{__api_version__}",
        }
        if self.api_key:
            _headers["Authorization"] = f"Bearer {self.api_key}"
        return _headers

    def _cache(self, response, key):
        """Add a retrieved template to the cache for 304 checking.

        Accepts a dict and key name, adds the retrieval time, and adds both
        to self.templates as a new dict using the specified key.
        """
        # cache template and retrieval time for subsequent calls
        try:
            thetime = whenever.ZonedDateTime.now("Europe/London").py_datetime()
        except AttributeError:
            thetime = whenever.ZonedDateTime.now("Europe/London").py_datetime()
        self.templates[key] = {"tmplt": response.json(), "updated": thetime}
        return copy.deepcopy(response.json())

    @cleanwrap
    def _cleanup(self, to_clean, allow=()):
        """Remove keys we added for internal use."""
        # this item's been retrieved from the API, we only need the 'data' entry
        if to_clean.keys() == ["links", "library", "version", "meta", "key", "data"]:
            to_clean = to_clean["data"]
        return {
            k: v for k, v in to_clean.items() if k in allow or k not in self.temp_keys
        }

    def _retrieve_data(self, request: str | None = None, params=None):
        """Retrieve Zotero items via the API.

        Combine endpoint and request to access the specific resource.
        Returns a JSON document.
        """
        if request is None:
            request = ""
        full_url = build_url(self.endpoint, request)
        # ensure that we wait if there's an active backoff
        self._check_backoff()
        # don't set locale if the url already contains it
        # we always add a locale if it's a "standalone" or first call
        needs_locale = not self.links or not self._check_for_component(
            self.links.get("next"),
            "locale",
        )
        if needs_locale:
            if params:
                params["locale"] = self.locale
            else:
                params = {"locale": self.locale}
        # we now have to merge self.url_params (default params, and those supplied by the user)
        if not params:
            params = {}
        if not self.url_params:
            self.url_params = {}
        merged_params = {**self.url_params, **params}
        # our incoming url might be from the "links" dict, in which case it will contain url parameters.
        # Unfortunately, httpx doesn't like to merge query parameters in the url string and passed params
        # so we strip the url params, combining them with our existing url_params
        final_url, final_params = merge_params(full_url, merged_params)
        # file URI errors are raised immediately so we have to try here
        try:
            self.request = self.client.get(
                url=final_url,
                params=final_params,
                headers=self.default_headers(),
                timeout=DEFAULT_TIMEOUT,
            )
            self.request.encoding = "utf-8"
            # The API doesn't return this any more, so we have to cheat
            self.self_link = self.request.url
        except httpx.UnsupportedProtocol:
            # File URI handler logic
            fc = File_Client()
            response = fc.get(
                url=final_url,
                params=final_params,
                headers=self.default_headers(),
                timeout=DEFAULT_TIMEOUT,
                follow_redirects=True,
            )
            self.request = response
            # since we'll be writing bytes, we need to set this to a type that will trigger the bytes processor
            self.request.headers["Content-Type"] = "text/plain"
        try:
            self.request.raise_for_status()
        except httpx.HTTPError as exc:
            error_handler(self, self.request, exc)
        backoff = get_backoff_duration(self.request.headers)
        if backoff:
            self._set_backoff(backoff)
        return self.request

    def _extract_links(self):
        """Extract self, first, next, last links from a request response."""
        extracted = {}
        try:
            for key, value in self.request.links.items():
                parsed = urlparse(value["url"])
                fragment = urlunparse(("", "", parsed.path, "", parsed.query, ""))
                extracted[key] = fragment
            # add a 'self' link
            parsed = urlparse(str(self.self_link))
            # strip 'format' query parameter and rebuild query string
            query_params = [(k, v) for k, v in parse_qsl(parsed.query) if k != "format"]
            # rebuild url fragment with just path and query (consistent with other links)
            extracted["self"] = urlunparse(
                ("", "", parsed.path, "", urlencode(query_params), "")
            )
        except KeyError:
            # No links present, because it's a single item
            return None
        else:
            return extracted

    def _updated(self, url, payload, template=None):
        """Call to see if a template request returns 304.

        Accepts:
        - a string to combine with the API endpoint
        - a dict of format values, in case they're required by 'url'
        - a template name to check for

        As per the API docs, a template less than 1 hour old is
        assumed to be fresh, and will immediately return False if found.
        """
        # If the template is more than an hour old, try a 304
        if (
            abs(
                whenever.ZonedDateTime.now("Europe/London").py_datetime()
                - self.templates[template]["updated"],
            ).seconds
            > ONE_HOUR
        ):
            query = build_url(
                self.endpoint,
                url.format(u=self.library_id, t=self.library_type, **payload),
            )
            headers = {
                "If-Modified-Since": payload["updated"].strftime(
                    "%a, %d %b %Y %H:%M:%S %Z",
                ),
            }
            # perform the request, and check whether the response returns 304
            self._check_backoff()
            req = self.client.get(query, headers=headers)
            try:
                req.raise_for_status()
            except httpx.HTTPError as exc:
                error_handler(self, req, exc)
            backoff = get_backoff_duration(self.request.headers)
            if backoff:
                self._set_backoff(backoff)
            return req.status_code == httpx.codes.NOT_MODIFIED
        # Still plenty of life left in't
        return False

    def add_parameters(self, **params):
        """Add URL parameters.

        Also ensure that only valid format/content combinations are requested.
        """
        # Preserve constructor-level parameters (like locale) while allowing method-level overrides
        if self.url_params is None:
            self.url_params = {}

        # Store existing params to preserve things like locale
        preserved_params = self.url_params.copy()

        # we want JSON by default
        if not params.get("format"):
            params["format"] = "json"
        # non-standard content must be retrieved as Atom
        if params.get("content"):
            params["format"] = "atom"
        # TODO: rewrite format=atom, content=json request
        if "limit" not in params or params.get("limit") == 0:
            params["limit"] = DEFAULT_ITEM_LIMIT
        # Need ability to request arbitrary number of results for version
        # response
        # -1 value is hack that works with current version
        elif params["limit"] == -1 or params["limit"] is None:
            del params["limit"]
        # bib format can't have a limit
        if params.get("format") == "bib":
            params.pop("limit", None)

        # Merge preserved params with new params (new params override existing ones)
        self.url_params = {**preserved_params, **params}

    def _build_query(self, query_string, no_params=False):
        """Set request parameters.

        Will always add the user ID if it hasn't been specifically set by an API method.
        """
        try:
            query = quote(query_string.format(u=self.library_id, t=self.library_type))
        except KeyError as err:
            errmsg = f"There's a request parameter missing: {err}"
            raise ze.ParamNotPassedError(errmsg) from None
        # Add the URL parameters and the user key, if necessary
        if no_params is False and not self.url_params:
            self.add_parameters()
        return query

    @retrieve
    def publications(self):
        """Return the contents of My Publications."""
        if self.library_type != "users":
            msg = "This API call does not exist for group libraries"
            raise ze.CallDoesNotExistError(msg)
        query_string = "/{t}/{u}/publications/items"
        return self._build_query(query_string)

    # The following methods are Zotero Read API calls
    def num_items(self):
        """Return the total number of top-level items in the library."""
        query = "/{t}/{u}/items/top"
        return self._totals(query)

    def count_items(self):
        """Return the count of all items in a group / library."""
        query = "/{t}/{u}/items"
        return self._totals(query)

    def num_collectionitems(self, collection):
        """Return the total number of items in the specified collection."""
        query = f"/{self.library_type}/{self.library_id}/collections/{collection.upper()}/items"
        return self._totals(query)

    def _totals(self, query):
        """General method for returning total counts."""
        self.add_parameters(limit=1)
        query = self._build_query(query)
        self._retrieve_data(query)
        self.url_params = None
        # extract the 'total items' figure
        return int(self.request.headers["Total-Results"])

    @retrieve
    def key_info(self, **kwargs):
        """Retrieve info about the permissions associated with the key."""
        query_string = f"/keys/{self.api_key}"
        return self._build_query(query_string)

    @retrieve
    def items(self, **kwargs):
        """Get user items."""
        query_string = "/{t}/{u}/items"
        return self._build_query(query_string)

    @retrieve
    def settings(self, **kwargs):
        """Get synced user settings."""
        query_string = "/{t}/{u}/settings"
        return self._build_query(query_string)

    @retrieve
    def fulltext_item(self, itemkey, **kwargs):
        """Get full-text content for an item."""
        query_string = (
            f"/{self.library_type}/{self.library_id}/items/{itemkey}/fulltext"
        )
        return self._build_query(query_string)

    @backoff_check
    def set_fulltext(self, itemkey, payload):
        """Set full-text data for an item.

        <itemkey> should correspond to an existing attachment item.
        payload should be a dict containing three keys:
        'content': the full-text content and either
        For text documents, 'indexedChars' and 'totalChars' OR
        For PDFs, 'indexedPages' and 'totalPages'.
        """
        headers = {"Content-Type": "application/json"}
        return self.client.put(
            url=build_url(
                self.endpoint,
                f"/{self.library_type}/{self.library_id}/items/{itemkey}/fulltext",
            ),
            headers=headers,
            json=payload,
        )

    def new_fulltext(self, since):
        """Retrieve list of full-text content items and versions newer than <since>."""
        query_string = f"/{self.library_type}/{self.library_id}/fulltext"
        headers = {}
        params = {"since": since}
        self._check_backoff()
        resp = self.client.get(
            build_url(self.endpoint, query_string),
            params=params,
            headers=headers,
        )
        try:
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            error_handler(self, resp, exc)
        backoff = get_backoff_duration(self.request.headers)
        if backoff:
            self._set_backoff(backoff)
        return resp.json()

    def item_versions(self, **kwargs):
        """Return dict associating item keys to versions.

        Accepts a since= parameter in kwargs to limit the data to those updated since.
        """
        if "limit" not in kwargs:
            kwargs["limit"] = None
        kwargs["format"] = "versions"
        return self.items(**kwargs)

    def collection_versions(self, **kwargs):
        """Return dict associating collection keys to versions.

        Accepts a since= parameter in kwargs to limit the data to those updated since.
        """
        if "limit" not in kwargs:
            kwargs["limit"] = None
        kwargs["format"] = "versions"
        return self.collections(**kwargs)

    def last_modified_version(self, **kwargs):
        """Get the last modified user or group library version."""
        # This MUST be a multiple-object request, limit param notwithstanding
        self.items(limit=1)
        lmv = self.request.headers.get("last-modified-version", 0)
        return int(lmv)

    @retrieve
    def top(self, **kwargs):
        """Get user top-level items."""
        query_string = "/{t}/{u}/items/top"
        return self._build_query(query_string)

    @retrieve
    def trash(self, **kwargs):
        """Get all items in the trash."""
        query_string = "/{t}/{u}/items/trash"
        return self._build_query(query_string)

    @retrieve
    def searches(self, **kwargs):
        """Get saved searches."""
        query_string = "/{t}/{u}/searches"
        return self._build_query(query_string)

    @retrieve
    def deleted(self, **kwargs):
        """Get all deleted items (requires since= parameter)."""
        if "limit" not in kwargs:
            # Currently deleted API doesn't respect limit leaving it out by
            # default preserves compat
            kwargs["limit"] = None
        query_string = "/{t}/{u}/deleted"
        return self._build_query(query_string)

    @retrieve
    def item(self, item, **kwargs):
        """Get a specific item."""
        query_string = f"/{self.library_type}/{self.library_id}/items/{item.upper()}"
        return self._build_query(query_string)

    @retrieve
    def file(self, item, **kwargs):
        """Get the file from a specific item."""
        query_string = (
            f"/{self.library_type}/{self.library_id}/items/{item.upper()}/file"
        )
        return self._build_query(query_string, no_params=True)

    def dump(self, itemkey, filename=None, path=None):
        """Dump a file attachment to disk, with optional filename and path."""
        if not filename:
            filename = self.item(itemkey)["data"]["filename"]
        pth = Path(path) / filename if path else Path(filename)
        file = self.file(itemkey)
        if self.snapshot:
            self.snapshot = False
            pth = pth.parent / (pth.name + ".zip")
        with pth.open("wb") as f:
            f.write(file)

    @retrieve
    def children(self, item, **kwargs):
        """Get a specific item's child items."""
        query_string = (
            f"/{self.library_type}/{self.library_id}/items/{item.upper()}/children"
        )
        return self._build_query(query_string)

    @retrieve
    def collection_items(self, collection, **kwargs):
        """Get a specific collection's items."""
        query_string = f"/{self.library_type}/{self.library_id}/collections/{collection.upper()}/items"
        return self._build_query(query_string)

    @retrieve
    def collection_items_top(self, collection, **kwargs):
        """Get a specific collection's top-level items."""
        query_string = f"/{self.library_type}/{self.library_id}/collections/{collection.upper()}/items/top"
        return self._build_query(query_string)

    @retrieve
    def collection_tags(self, collection, **kwargs):
        """Get a specific collection's tags."""
        query_string = f"/{self.library_type}/{self.library_id}/collections/{collection.upper()}/tags"
        return self._build_query(query_string)

    @retrieve
    def collection(self, collection, **kwargs):
        """Get user collection."""
        query_string = (
            f"/{self.library_type}/{self.library_id}/collections/{collection.upper()}"
        )
        return self._build_query(query_string)

    @retrieve
    def collections(self, **kwargs):
        """Get user collections."""
        query_string = "/{t}/{u}/collections"
        return self._build_query(query_string)

    def all_collections(self, collid=None):
        """Retrieve all collections and subcollections.

        Works for top-level collections or for a specific collection.
        Works at all collection depths.
        """
        all_collections = []

        def subcoll(clct):
            """Recursively add collections to a flat master list."""
            all_collections.append(clct)
            if clct["meta"].get("numCollections", 0) > 0:
                # add collection to master list & recur with all child collections
                for c in self.everything(self.collections_sub(clct["data"]["key"])):
                    subcoll(c)

        # select all top-level collections or a specific collection and children
        if collid:
            toplevel = [self.collection(collid)]
        else:
            toplevel = self.everything(self.collections_top())
        for collection in toplevel:
            subcoll(collection)
        return all_collections

    @retrieve
    def collections_top(self, **kwargs):
        """Get top-level user collections."""
        query_string = "/{t}/{u}/collections/top"
        return self._build_query(query_string)

    @retrieve
    def collections_sub(self, collection, **kwargs):
        """Get subcollections for a specific collection."""
        query_string = f"/{self.library_type}/{self.library_id}/collections/{collection.upper()}/collections"
        return self._build_query(query_string)

    @retrieve
    def groups(self, **kwargs):
        """Get user groups."""
        query_string = "/users/{u}/groups"
        return self._build_query(query_string)

    @retrieve
    def tags(self, **kwargs):
        """Get tags."""
        query_string = "/{t}/{u}/tags"
        self.tag_data = True
        return self._build_query(query_string)

    @retrieve
    def item_tags(self, item, **kwargs):
        """Get tags for a specific item."""
        query_string = (
            f"/{self.library_type}/{self.library_id}/items/{item.upper()}/tags"
        )
        self.tag_data = True
        return self._build_query(query_string)

    def all_top(self, **kwargs):
        """Retrieve all top-level items."""
        return self.everything(self.top(**kwargs))

    @retrieve
    def follow(self):
        """Return the result of the call to the URL in the 'Next' link."""
        if n := self.links.get("next"):
            return self._striplocal(n)
        return None

    def iterfollow(self):
        """Return generator for self.follow()."""
        # use same criterion as self.follow()
        while True:
            if self.links.get("next"):
                yield self.follow()
            else:
                return

    def makeiter(self, func):
        """Return a generator of func's results."""
        if self.links is None or "self" not in self.links:
            msg = "makeiter() requires a previous API call with pagination links"
            raise RuntimeError(msg)
        # reset the link. This results in an extra API call, yes
        self.links["next"] = self.links["self"]
        return self.iterfollow()

    def everything(self, query):
        """Retrieve all items in the library for a particular query.

        This method will override the 'limit' parameter if it's been set.
        """
        try:
            items = []
            items.extend(query)
            while self.links.get("next"):
                items.extend(self.follow())
        except TypeError:
            # we have a bibliography object ughh
            items = copy.deepcopy(query)
            while self.links.get("next"):
                items.entries.extend(self.follow().entries)
        return items

    def get_subset(self, subset):
        """Retrieve a subset of items.

        Accepts a single argument: a list of item IDs.
        """
        if len(subset) > DEFAULT_NUM_ITEMS:
            err = f"You may only retrieve {DEFAULT_NUM_ITEMS} items per call"
            raise ze.TooManyItemsError(err)
        # remember any url parameters that have been set
        params = self.url_params
        retr = []
        for itm in subset:
            retr.append(self.item(itm))
            self.url_params = params
        # clean up URL params when we're finished
        self.url_params = None
        return retr

    # The following methods process data returned by Read API calls
    def _json_processor(self, retrieved):
        """Format and return data from API calls which return Items."""
        # send entries to _tags_data if there's no JSON
        try:
            items = [json.loads(e["content"][0]["value"]) for e in retrieved.entries]
        except KeyError:
            return self._tags_data(retrieved)
        return items

    def _csljson_processor(self, retrieved):
        """Return a list of dicts which are dumped CSL JSON."""
        items = [
            json.loads(entry["content"][0]["value"]) for entry in retrieved.entries
        ]
        self.url_params = None
        return items

    def _bib_processor(self, retrieved):
        """Return a list of strings formatted as HTML bibliography entries."""
        items = [bib["content"][0]["value"] for bib in retrieved.entries]
        self.url_params = None
        return items

    def _citation_processor(self, retrieved):
        """Return a list of strings formatted as HTML citation entries."""
        items = [cit["content"][0]["value"] for cit in retrieved.entries]
        self.url_params = None
        return items

    def _tags_data(self, retrieved):
        """Format and return data from API calls which return Tags."""
        self.url_params = None
        return [t["tag"] for t in retrieved]

    # The following methods are Write API calls
    def item_template(self, itemtype, linkmode=None):
        """Get a template for a new item."""
        # if we have a template and it hasn't been updated since we stored it
        template_name = f"item_template_{itemtype}_{linkmode or ''}"
        params = {"itemType": itemtype}
        # Set linkMode parameter for API request if itemtype is attachment
        if itemtype == "attachment":
            params["linkMode"] = linkmode
        self.add_parameters(**params)
        query_string = "/items/new"
        if self.templates.get(template_name) and not self._updated(
            query_string,
            self.templates[template_name],
            template_name,
        ):
            return copy.deepcopy(self.templates[template_name]["tmplt"])
        # otherwise perform a normal request and cache the response
        retrieved = self._retrieve_data(query_string)
        return self._cache(retrieved, template_name)

    def _attachment_template(self, attachment_type):
        """Return a new attachment template of the required type.

        Types: imported_file, imported_url, linked_file, linked_url
        """
        return self.item_template("attachment", linkmode=attachment_type)

    def _attachment(self, payload, parentid=None):
        """Create attachments.

        Accepts a list of one or more attachment template dicts
        and an optional parent Item ID. If this is specified,
        attachments are created under this ID.
        """
        attachment = Zupload(self, payload, parentid)
        return attachment.upload()

    @ss_wrap
    def show_operators(self):
        """Show available saved search operators."""
        return self.savedsearch.operators

    @ss_wrap
    def show_conditions(self):
        """Show available saved search conditions."""
        return self.savedsearch.conditions_operators.keys()

    @ss_wrap
    def show_condition_operators(self, condition):
        """Show available operators for a given saved search condition."""
        # dict keys of allowed operators for the current condition
        permitted_operators = self.savedsearch.conditions_operators.get(condition)
        # transform these into values
        return {self.savedsearch.operators.get(op) for op in permitted_operators}

    @ss_wrap
    def saved_search(self, name, conditions):
        """Create a saved search.

        conditions is a list of dicts containing search conditions and must
        contain the following str keys: condition, operator, value
        """
        self.savedsearch._validate(conditions)
        payload = [{"name": name, "conditions": conditions}]
        headers = {"Zotero-Write-Token": token()}
        self._check_backoff()
        req = self.client.post(
            url=build_url(
                self.endpoint,
                f"/{self.library_type}/{self.library_id}/searches",
            ),
            headers=headers,
            json=payload,
        )
        self.request = req
        try:
            req.raise_for_status()
        except httpx.HTTPError as exc:
            error_handler(self, req, exc)
        backoff = get_backoff_duration(self.request.headers)
        if backoff:
            self._set_backoff(backoff)
        return req.json()

    @ss_wrap
    def delete_saved_search(self, keys):
        """Delete one or more saved searches.

        Pass a list of one or more unique search keys.
        """
        headers = {"Zotero-Write-Token": token()}
        self._check_backoff()
        req = self.client.delete(
            url=build_url(
                self.endpoint,
                f"/{self.library_type}/{self.library_id}/searches",
            ),
            headers=headers,
            params={"searchKey": ",".join(keys)},
        )
        self.request = req
        try:
            req.raise_for_status()
        except httpx.HTTPError as exc:
            error_handler(self, req, exc)
        backoff = get_backoff_duration(self.request.headers)
        if backoff:
            self._set_backoff(backoff)
        return req.status_code

    def upload_attachments(self, attachments, parentid=None, basedir=None):
        """Upload files to the already created (but never uploaded) attachments."""
        return Zupload(self, attachments, parentid, basedir=basedir).upload()

    def add_tags(self, item, *tags):
        """Add one or more tags to a retrieved item, then update it on the server.

        Accepts a dict, and one or more tags to add to it.
        Returns the updated item from the server.
        """
        # Make sure there's a tags field, or add one
        if not item.get("data", {}).get("tags"):
            item["data"]["tags"] = []
        for tag in tags:
            item["data"]["tags"].append({"tag": f"{tag}"})
        # make sure everything's OK
        self.check_items([item])
        return self.update_item(item)

    def check_items(self, items):
        """Check that items to be created contain no invalid dict keys.

        Accepts a single argument: a list of one or more dicts.
        The retrieved fields are cached and re-used until a 304 call fails.
        """
        params = {"locale": self.locale, "timeout": DEFAULT_TIMEOUT}
        query_string = "/itemFields"
        r = Request(
            "GET",
            build_url(self.endpoint, query_string),
            params=params,
        )
        response = self.client.send(r)
        # now split up the URL
        result = urlparse(str(response.url))
        # construct cache key
        cachekey = result.path + "_" + result.query
        if self.templates.get(cachekey) and not self._updated(
            query_string,
            self.templates[cachekey],
            cachekey,
        ):
            template = {t["field"] for t in self.templates[cachekey]["tmplt"]}
        else:
            template = {t["field"] for t in self.item_fields()}
        # add fields we know to be OK
        template |= {
            "path",
            "tags",
            "notes",
            "itemType",
            "creators",
            "mimeType",
            "linkMode",
            "note",
            "charset",
            "dateAdded",
            "version",
            "collections",
            "dateModified",
            "relations",
            #  attachment items
            "parentItem",
            "mtime",
            "contentType",
            "md5",
            "filename",
            "inPublications",
            # annotation fields
            "annotationText",
            "annotationColor",
            "annotationType",
            "annotationPageLabel",
            "annotationPosition",
            "annotationSortIndex",
            "annotationComment",
            "annotationAuthorName",
        }
        template |= set(self.temp_keys)
        processed_items = []
        for pos, item in enumerate(items):
            if set(item) == {"links", "library", "version", "meta", "key", "data"}:
                itm = item["data"]
            else:
                itm = item
            to_check = set(itm.keys())
            difference = to_check.difference(template)
            if difference:
                err = f"Invalid keys present in item {pos + 1}: {' '.join(i for i in difference)}"
                raise ze.InvalidItemFieldsError(err)
            processed_items.append(itm)
        return processed_items

    @tcache
    def item_types(self):
        """Get all available item types."""
        # Check for a valid cached version
        params = {"locale": self.locale}
        query_string = "/itemTypes"
        return query_string, params

    @tcache
    def creator_fields(self):
        """Get localised creator fields."""
        # Check for a valid cached version
        params = {"locale": self.locale}
        query_string = "/creatorFields"
        return query_string, params

    @tcache
    def item_type_fields(self, itemtype):
        """Get all valid fields for an item."""
        params = {"itemType": itemtype, "locale": self.locale}
        query_string = "/itemTypeFields"
        return query_string, params

    @tcache
    def item_creator_types(self, itemtype):
        """Get all available creator types for an item."""
        params = {"itemType": itemtype, "locale": self.locale}
        query_string = "/itemTypeCreatorTypes"
        return query_string, params

    @tcache
    def item_fields(self):
        """Get all available item fields."""
        # Check for a valid cached version
        params = {"locale": self.locale}
        query_string = "/itemFields"
        return query_string, params

    @staticmethod
    def item_attachment_link_modes():
        """Get all available link mode types.

        Note: No viable REST API route was found for this, so I tested and built
        a list from documentation found here:
        https://www.zotero.org/support/dev/web_api/json
        """
        return ["imported_file", "imported_url", "linked_file", "linked_url"]

    def create_items(self, payload, parentid=None, last_modified=None):
        """Create new Zotero items.

        Accepts two arguments:
            a list containing one or more item dicts
            an optional parent item ID.
        Note that this can also be used to update existing items.
        """
        if len(payload) > DEFAULT_NUM_ITEMS:
            msg = f"You may only create up to {DEFAULT_NUM_ITEMS} items per call"
            raise ze.TooManyItemsError(msg)
        # TODO: strip extra data if it's an existing item
        headers = {"Zotero-Write-Token": token(), "Content-Type": "application/json"}
        if last_modified is not None:
            headers["If-Unmodified-Since-Version"] = str(last_modified)
        to_send = list(self._cleanup(*payload, allow=("key")))
        self._check_backoff()
        req = self.client.post(
            url=build_url(
                self.endpoint,
                f"/{self.library_type}/{self.library_id}/items",
            ),
            content=json.dumps(to_send),
            headers=headers,
        )
        self.request = req
        try:
            req.raise_for_status()
        except httpx.HTTPError as exc:
            error_handler(self, req, exc)
        resp = req.json()
        backoff = get_backoff_duration(self.request.headers)
        if backoff:
            self._set_backoff(backoff)
        if parentid:
            # we need to create child items using PATCH
            # TODO: handle possibility of item creation + failed parent attachment
            uheaders = {
                "If-Unmodified-Since-Version": req.headers["last-modified-version"],
            }
            for value in resp["success"].values():
                payload = {"parentItem": parentid}
                self._check_backoff()
                presp = self.client.patch(
                    url=build_url(
                        self.endpoint,
                        f"/{self.library_type}/{self.library_id}/items/{value}",
                    ),
                    json=payload,
                    headers=dict(uheaders),
                )
                self.request = presp
                try:
                    presp.raise_for_status()
                except httpx.HTTPError as exc:
                    error_handler(self, presp, exc)
                backoff = get_backoff_duration(presp.headers)
                if backoff:
                    self._set_backoff(backoff)
        return resp

    def create_collection(self, payload, last_modified=None):
        """Alias for create_collections to preserve backward compatibility."""
        return self.create_collections(payload, last_modified)

    def create_collections(self, payload, last_modified=None):
        """Create new Zotero collections.

        Accepts one argument, a list of dicts containing the following keys:
        'name': the name of the collection
        'parentCollection': OPTIONAL, the parent collection to which you wish to add this
        """
        # no point in proceeding if there's no 'name' key
        for item in payload:
            if "name" not in item:
                msg = "The dict you pass must include a 'name' key"
                raise ze.ParamNotPassedError(msg)
            # add a blank 'parentCollection' key if it hasn't been passed
            if "parentCollection" not in item:
                item["parentCollection"] = ""
        headers = {"Zotero-Write-Token": token()}
        if last_modified is not None:
            headers["If-Unmodified-Since-Version"] = str(last_modified)
        self._check_backoff()
        req = self.client.post(
            url=build_url(
                self.endpoint,
                f"/{self.library_type}/{self.library_id}/collections",
            ),
            headers=headers,
            content=json.dumps(payload),
        )
        self.request = req
        try:
            req.raise_for_status()
        except httpx.HTTPError as exc:
            error_handler(self, req, exc)
        backoff = get_backoff_duration(req.headers)
        if backoff:
            self._set_backoff(backoff)
        return req.json()

    @backoff_check
    def update_collection(self, payload, last_modified=None):
        """Update a Zotero collection property such as 'name'.

        Accepts one argument, a dict containing collection data retrieved
        using e.g. 'collections()'.
        """
        modified = payload["version"]
        if last_modified is not None:
            modified = last_modified
        key = payload["key"]
        headers = {"If-Unmodified-Since-Version": str(modified)}
        headers.update({"Content-Type": "application/json"})
        return self.client.put(
            url=build_url(
                self.endpoint,
                f"/{self.library_type}/{self.library_id}/collections/{key}",
            ),
            headers=headers,
            content=json.dumps(payload),
        )

    def attachment_simple(self, files, parentid=None):
        """Add attachments using filenames as title.

        Args:
            files: One or more file paths to add as attachments.
            parentid: Optional Item ID to create child attachments.

        """
        orig = self._attachment_template("imported_file")
        to_add = [orig.copy() for _ in files]
        for idx, tmplt in enumerate(to_add):
            tmplt["title"] = Path(files[idx]).name
            tmplt["filename"] = files[idx]
        if parentid:
            return self._attachment(to_add, parentid)
        return self._attachment(to_add)

    def attachment_both(self, files, parentid=None):
        """Add child attachments using title, filename.

        Args:
            files: One or more lists or tuples containing (title, file path).
            parentid: Optional Item ID to create child attachments.

        """
        orig = self._attachment_template("imported_file")
        to_add = [orig.copy() for _ in files]
        for idx, tmplt in enumerate(to_add):
            tmplt["title"] = files[idx][0]
            tmplt["filename"] = files[idx][1]
        if parentid:
            return self._attachment(to_add, parentid)
        return self._attachment(to_add)

    @backoff_check
    def update_item(self, payload, last_modified=None):
        """Update an existing item.

        Accepts one argument, a dict containing Item data.
        """
        to_send = self.check_items([payload])[0]
        modified = payload["version"] if last_modified is None else last_modified
        ident = payload["key"]
        headers = {"If-Unmodified-Since-Version": str(modified)}
        return self.client.patch(
            url=build_url(
                self.endpoint,
                f"/{self.library_type}/{self.library_id}/items/{ident}",
            ),
            headers=headers,
            content=json.dumps(to_send),
        )

    def update_items(self, payload):
        """Update existing items.

        Accepts one argument, a list of dicts containing Item data.
        """
        to_send = [self.check_items([p])[0] for p in payload]
        # the API only accepts 50 items at a time, so we have to split anything longer
        for chunk in chunks(to_send, DEFAULT_NUM_ITEMS):
            self._check_backoff()
            req = self.client.post(
                url=build_url(
                    self.endpoint,
                    f"/{self.library_type}/{self.library_id}/items/",
                ),
                json=chunk,
            )
            self.request = req
            try:
                req.raise_for_status()
            except httpx.HTTPError as exc:
                error_handler(self, req, exc)
            backoff = get_backoff_duration(req.headers)
            if backoff:
                self._set_backoff(backoff)
        return True

    def update_collections(self, payload):
        """Update existing collections.

        Accepts one argument, a list of dicts containing Collection data.
        """
        to_send = [self.check_items([p])[0] for p in payload]
        # the API only accepts 50 items at a time, so we have to split anything longer
        for chunk in chunks(to_send, DEFAULT_NUM_ITEMS):
            self._check_backoff()
            req = self.client.post(
                url=build_url(
                    self.endpoint,
                    f"/{self.library_type}/{self.library_id}/collections/",
                ),
                json=chunk,
            )
            self.request = req
            try:
                req.raise_for_status()
            except httpx.HTTPError as exc:
                error_handler(self, req, exc)
            backoff = get_backoff_duration(req.headers)
            if backoff:
                self._set_backoff(backoff)
        return True

    @backoff_check
    def addto_collection(self, collection, payload):
        """Add item to a collection.

        Accepts two arguments: The collection ID, and an item dict.
        """
        ident = payload["key"]
        modified = payload["version"]
        # add the collection data from the item
        modified_collections = payload["data"]["collections"] + [collection]
        headers = {"If-Unmodified-Since-Version": str(modified)}
        return self.client.patch(
            url=build_url(
                self.endpoint,
                f"/{self.library_type}/{self.library_id}/items/{ident}",
            ),
            json={"collections": modified_collections},
            headers=headers,
        )

    @backoff_check
    def deletefrom_collection(self, collection, payload):
        """Delete an item from a collection.

        Accepts two arguments: The collection ID, and an item dict.
        """
        ident = payload["key"]
        modified = payload["version"]
        # strip the collection data from the item
        modified_collections = [
            c for c in payload["data"]["collections"] if c != collection
        ]
        headers = {"If-Unmodified-Since-Version": str(modified)}
        return self.client.patch(
            url=build_url(
                self.endpoint,
                f"/{self.library_type}/{self.library_id}/items/{ident}",
            ),
            json={"collections": modified_collections},
            headers=headers,
        )

    @backoff_check
    def delete_tags(self, *payload):
        """Delete a group of tags.

        Pass in up to 50 tags, or use *[tags].
        """
        if len(payload) > DEFAULT_NUM_ITEMS:
            msg = f"Only {DEFAULT_NUM_ITEMS} tags or fewer may be deleted"
            raise ze.TooManyItemsError(msg)
        modified_tags = " || ".join(list(payload))
        # first, get version data by getting one tag
        self.tags(limit=1)
        headers = {
            "If-Unmodified-Since-Version": self.request.headers[
                "last-modified-version"
            ],
        }
        return self.client.delete(
            url=build_url(
                self.endpoint,
                f"/{self.library_type}/{self.library_id}/tags",
            ),
            params={"tag": modified_tags},
            headers=headers,
        )

    @backoff_check
    def delete_item(self, payload, last_modified=None):
        """Delete Items from a Zotero library.

        Accepts a single argument:
            a dict containing item data
            OR a list of dicts containing item data
        """
        params = None
        if isinstance(payload, list):
            params = {"itemKey": ",".join([p["key"] for p in payload])}
            if last_modified is not None:
                modified = last_modified
            else:
                modified = payload[0]["version"]
            url = build_url(
                self.endpoint,
                f"/{self.library_type}/{self.library_id}/items",
            )
        else:
            ident = payload["key"]
            if last_modified is not None:
                modified = last_modified
            else:
                modified = payload["version"]
            url = build_url(
                self.endpoint,
                f"/{self.library_type}/{self.library_id}/items/{ident}",
            )
        headers = {"If-Unmodified-Since-Version": str(modified)}
        return self.client.delete(url=url, params=params, headers=headers)

    @backoff_check
    def delete_collection(self, payload, last_modified=None):
        """Delete a Collection from a Zotero library.

        Accepts a single argument:
            a dict containing item data
            OR a list of dicts containing item data
        """
        params = None
        if isinstance(payload, list):
            params = {"collectionKey": ",".join([p["key"] for p in payload])}
            if last_modified is not None:
                modified = last_modified
            else:
                modified = payload[0]["version"]
            url = build_url(
                self.endpoint,
                f"/{self.library_type}/{self.library_id}/collections",
            )
        else:
            ident = payload["key"]
            if last_modified is not None:
                modified = last_modified
            else:
                modified = payload["version"]
            url = build_url(
                self.endpoint,
                f"/{self.library_type}/{self.library_id}/collections/{ident}",
            )
        headers = {"If-Unmodified-Since-Version": str(modified)}
        return self.client.delete(url=url, params=params, headers=headers)


__all__ = ["Zotero"]
