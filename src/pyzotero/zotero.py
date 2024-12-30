# pylint: disable=R0904
"""
zotero.py

Created by Stephan Hügel on 2011-02-28

This file is part of Pyzotero.
"""

__author__ = "Stephan Hügel"
__api_version__ = "3"

import copy
import datetime
import hashlib
import io
import json
import mimetypes
import os
import re
import threading
import time
import uuid
import zipfile
from collections import OrderedDict
from functools import wraps
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

import bibtexparser
import feedparser
import httpx
import pytz
from httpx import Request

import pyzotero as pz

from . import zotero_errors as ze

# Avoid hanging the application if there's no server response
timeout = 30


def build_url(base_url, path, args_dict=None):
    """Build a valid URL so we don't have to worry about string concatenation errors and
    leading / trailing slashes etc.
    Returns a list in the structure of urlparse.ParseResult"""
    if base_url.endswith("/"):
        base_url = base_url[:-1]
    url_parts = list(urlparse(base_url))
    url_parts[2] += path
    if args_dict:
        url_parts[4] = urlencode(args_dict)
    return urlunparse(url_parts)


def token():
    """Return a unique 32-char write-token"""
    return str(uuid.uuid4().hex)


def cleanwrap(func):
    """Wrapper for Zotero._cleanup"""

    def enc(self, *args, **kwargs):
        """Send each item to _cleanup()"""
        return (func(self, item, **kwargs) for item in args)

    return enc


def chunks(iterable, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(iterable), n):
        yield iterable[i : i + n]


def tcache(func):
    """Take care of the URL building and caching for template functions"""

    @wraps(func)
    def wrapped_f(self, *args, **kwargs):
        """Calls the decorated function to get query string and params,
        builds URL, retrieves template, caches result, and returns template
        """
        query_string, params = func(self, *args, **kwargs)
        params["timeout"] = timeout
        r = Request(
            "GET",
            build_url(self.endpoint, query_string),
            params=params,
        )
        with httpx.Client() as client:
            response = client.send(r)

        # now split up the URL
        result = urlparse(str(response.url))
        # construct cache key
        cachekey = f"{result.path}_{result.query}"
        if self.templates.get(cachekey) and not self._updated(
            query_string, self.templates[cachekey], cachekey
        ):
            return self.templates[cachekey]["tmplt"]
        # otherwise perform a normal request and cache the response
        retrieved = self._retrieve_data(query_string, params=params)
        return self._cache(retrieved, cachekey)

    return wrapped_f


def backoff_check(func):
    """
    Perform backoff processing
    func must return a Requests GET / POST / PUT / PATCH / DELETE etc
    This is is intercepted: we first check for an active backoff
    and wait if need be.
    After the response is received, we do normal error checking
    and set a new backoff if necessary, before returning

    Use with functions that are intended to return True
    """

    @wraps(func)
    def wrapped_f(self, *args, **kwargs):
        self._check_backoff()
        # resp is a Requests response object
        resp = func(self, *args, **kwargs)
        try:
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            error_handler(self, resp, exc)
        self.request = resp
        backoff = resp.headers.get("backoff") or resp.headers.get("retry-after")
        if backoff:
            self._set_backoff(backoff)

        return True

    return wrapped_f


def retrieve(func):
    """
    Decorator for Zotero read API methods; calls _retrieve_data() and passes
    the result to the correct processor, based on a lookup
    """

    @wraps(func)
    def wrapped_f(self, *args, **kwargs):
        """
        Returns result of _retrieve_data()

        func's return value is part of a URI, and it's this
        which is intercepted and passed to _retrieve_data:
        '/users/123/items?key=abc123'
        """
        if kwargs:
            self.add_parameters(**kwargs)
        retrieved = self._retrieve_data(func(self, *args))
        # we now always have links in the header response
        self.links = self._extract_links()
        # determine content and format, based on url params
        content = (
            self.content.search(str(self.request.url))
            and self.content.search(str(self.request.url)).group(0)
            or "bib"
        )
        # JSON by default
        formats = {
            "application/atom+xml": "atom",
            "application/x-bibtex": "bibtex",
            "application/json": "json",
            "text/html": "snapshot",
            "text/plain": "plain",
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
        # select format, or assume JSON
        content_type_header = self.request.headers["Content-Type"].lower() + ";"
        fmt = formats.get(
            # strip "; charset=..." segment
            content_type_header[0 : content_type_header.index(";")],
            "json",
        )
        # clear all query parameters
        self.url_params = None
        # Zotero API returns plain-text attachments as zipped content
        # We can inspect the redirect header to check whether Zotero compressed the file
        if fmt == "zip":
            if (
                self.request.history
                and self.request.history[0].headers.get("Zotero-File-Compressed")
                == "Yes"
            ):
                z = zipfile.ZipFile(io.BytesIO(retrieved.content))
                namelist = z.namelist()
                file = z.read(namelist[0])
            else:
                file = retrieved.content
            return file
        # check to see whether it's tag data
        if "tags" in str(self.request.url):
            self.tag_data = False
            return self._tags_data(retrieved.json())
        if fmt == "atom":
            parsed = feedparser.parse(retrieved.text)
            # select the correct processor
            processor = self.processors.get(content)
            # process the content correctly with a custom rule
            return processor(parsed)
        if fmt == "snapshot":
            # we need to dump as a zip!
            self.snapshot = True
        if fmt == "bibtex":
            parser = bibtexparser.bparser.BibTexParser(
                common_strings=True, ignore_nonstandard_types=False
            )
            return parser.parse(retrieved.text)
        # it's binary, so return raw content
        elif fmt != "json":
            return retrieved.content
        # no need to do anything special, return JSON
        else:
            return retrieved.json()

    return wrapped_f


def ss_wrap(func):
    """ensure that a SavedSearch object exists"""

    def wrapper(self, *args, **kwargs):
        if not self.savedsearch:
            self.savedsearch = SavedSearch(self)
        return func(self, *args, **kwargs)

    return wrapper


class Zotero:
    """
    Zotero API methods
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
    ):
        self.client = None
        """Store Zotero credentials"""
        if not local:
            self.endpoint = "https://api.zotero.org"
            self.local = False
        else:
            self.endpoint = "http://localhost:23119/api"
            self.local = True
        if library_id and library_type:
            self.library_id = library_id
            # library_type determines whether query begins w. /users or /groups
            self.library_type = library_type + "s"
        else:
            raise ze.MissingCredentials(
                "Please provide both the library ID and the library type"
            )
        # api_key is not required for public individual or group libraries
        self.api_key = api_key
        self.preserve_json_order = preserve_json_order
        self.locale = locale
        self.url_params = None
        self.tag_data = False
        self.request = None
        self.snapshot = False
        self.client = httpx.Client(headers=self.default_headers())
        # these aren't valid item fields, so never send them to the server
        self.temp_keys = set(["key", "etag", "group_id", "updated"])
        # determine which processor to use for the parsed content
        self.fmt = re.compile(r"(?<=format=)\w+")
        self.content = re.compile(r"(?<=content=)\w+")
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
        # these are required for backoff handling
        self.backoff = False
        self.backoff_duration = 0.0

    def __del__(self):
        # this isn't guaranteed to run, but that's OK
        if c := self.client:
            c.close()

    def _check_for_component(self, url, component):
        """Check a url path query fragment for a specific query parameter"""
        if parse_qs(url).get(component):
            return True
        return False

    def _striplocal(self, url):
        """We need to remve the leading "/api" substring from urls if we're running in local mode"""
        if self.local:
            parsed = urlparse(url)
            purepath = PurePosixPath(unquote(parsed.path))
            newpath = "/".join(purepath.parts[2:])
            replaced = parsed._replace(path="/" + newpath)
            return urlunparse(replaced)
        return url

    def _set_backoff(self, duration):
        """
        Set a backoff
        Spins up a timer in a background thread which resets the backoff logic
        when it expires, then sets the time at which the backoff will expire.
        The latter step is required so that other calls can check whether there's
        an active backoff, because the threading.Timer method has no way
        of returning a duration
        """
        duration = float(duration)
        self.backoff = True
        threading.Timer(duration, self._reset_backoff).start()
        self.backoff_duration = time.time() + duration

    def _reset_backoff(self):
        self.backoff = False
        self.backoff_duration = 0.0

    def _check_backoff(self):
        """
        Before an API call is made, we check whether there's an active backoff.
        If there is, we check whether there's any time left on the backoff.
        If there is, we sleep for the remainder before returning
        """
        if self.backoff:
            remainder = self.backoff_duration - time.time()
            if remainder > 0.0:
                time.sleep(remainder)

    def default_headers(self):
        """
        It's always OK to include these headers
        """
        _headers = {
            "User-Agent": f"Pyzotero/{pz.__version__}",
            "Zotero-API-Version": f"{__api_version__}",
        }
        if self.api_key:
            _headers["Authorization"] = f"Bearer {self.api_key}"
        return _headers

    def _cache(self, response, key):
        """
        Add a retrieved template to the cache for 304 checking
        accepts a dict and key name, adds the retrieval time, and adds both
        to self.templates as a new dict using the specified key
        """
        # cache template and retrieval time for subsequent calls
        try:
            thetime = datetime.datetime.now(datetime.UTC).replace(
                tzinfo=pytz.timezone("GMT")
            )
        except AttributeError:
            thetime = thetime = datetime.datetime.utcnow().replace(
                tzinfo=pytz.timezone("GMT")
            )
        self.templates[key] = {"tmplt": response.json(), "updated": thetime}
        return copy.deepcopy(response.json())

    @cleanwrap
    def _cleanup(self, to_clean, allow=()):
        """Remove keys we added for internal use"""
        # this item's been retrieved from the API, we only need the 'data'
        # entry
        if to_clean.keys() == ["links", "library", "version", "meta", "key", "data"]:
            to_clean = to_clean["data"]
        return dict(
            [
                [k, v]
                for k, v in list(to_clean.items())
                if (k in allow or k not in self.temp_keys)
            ]
        )

    def _retrieve_data(self, request=None, params=None):
        """
        Retrieve Zotero items via the API
        Combine endpoint and request to access the specific resource
        Returns a JSON document
        """
        full_url = build_url(self.endpoint, request)
        # The API doesn't return this any more, so we have to cheat
        self.self_link = request
        # ensure that we wait if there's an active backoff
        self._check_backoff()
        # don't set locale if the url already contains it
        # we always add a locale if it's a "standalone" or first call
        needs_locale = not self.links or not self._check_for_component(
            self.links.get("next"), "locale"
        )
        if needs_locale:
            if params:
                params["locale"] = self.locale
            else:
                params = {"locale": self.locale}
        self.request = self.client.get(url=full_url, params=params)
        self.request.encoding = "utf-8"
        try:
            self.request.raise_for_status()
        except httpx.HTTPError as exc:
            error_handler(self, self.request, exc)
        backoff = self.request.headers.get("backoff") or self.request.headers.get(
            "retry-after"
        )
        if backoff:
            self._set_backoff(backoff)
        return self.request

    def _extract_links(self):
        """
        Extract self, first, next, last links from a request response
        """
        extracted = dict()
        try:
            for key, value in self.request.links.items():
                parsed = urlparse(value["url"])
                fragment = f"{parsed[2]}?{parsed[4]}"
                extracted[key] = fragment
            # add a 'self' link
            parsed = list(urlparse(self.self_link))
            # strip 'format' query parameter
            stripped = "&".join(
                ["=".join(p) for p in parse_qsl(parsed[4])[:2] if p[0] != "format"]
            )
            # rebuild url fragment
            # this is a death march
            extracted["self"] = urlunparse(
                [parsed[0], parsed[1], parsed[2], parsed[3], stripped, parsed[5]]
            )
            return extracted
        except KeyError:
            # No links present, because it's a single item
            return None

    def _updated(self, url, payload, template=None):
        """
        Generic call to see if a template request returns 304
        accepts:
        - a string to combine with the API endpoint
        - a dict of format values, in case they're required by 'url'
        - a template name to check for
        As per the API docs, a template less than 1 hour old is
        assumed to be fresh, and will immediately return False if found
        """
        # If the template is more than an hour old, try a 304
        if (
            abs(
                datetime.datetime.utcnow().replace(tzinfo=pytz.timezone("GMT"))
                - self.templates[template]["updated"]
            ).seconds
            > 3600
        ):
            query = build_url(
                self.endpoint,
                url.format(u=self.library_id, t=self.library_type, **payload),
            )
            headers = {
                "If-Modified-Since": payload["updated"].strftime(
                    "%a, %d %b %Y %H:%M:%S %Z"
                )
            }
            # perform the request, and check whether the response returns 304
            self._check_backoff()
            req = self.client.get(query, headers=headers)
            try:
                req.raise_for_status()
            except httpx.HTTPError as exc:
                error_handler(self, req, exc)
            backoff = self.request.headers.get("backoff") or self.request.headers.get(
                "retry-after"
            )
            if backoff:
                self._set_backoff(backoff)
            return req.status_code == 304
        # Still plenty of life left in't
        return False

    def add_parameters(self, **params):
        """
        Add URL parameters
        Also ensure that only valid format/content combinations are requested
        """
        self.url_params = None
        # we want JSON by default
        if not params.get("format"):
            params["format"] = "json"
        # non-standard content must be retrieved as Atom
        if params.get("content"):
            params["format"] = "atom"
        # TODO: rewrite format=atom, content=json request
        if "limit" not in params or params.get("limit") == 0:
            params["limit"] = 100
        # Need ability to request arbitrary number of results for version
        # response
        # -1 value is hack that works with current version
        elif params["limit"] == -1 or params["limit"] is None:
            del params["limit"]
        # bib format can't have a limit
        if params.get("format") == "bib":
            del params["limit"]
        self.url_params = urlencode(params, doseq=True)

    def _build_query(self, query_string, no_params=False):
        """
        Set request parameters. Will always add the user ID if it hasn't
        been specifically set by an API method
        """
        try:
            query = quote(query_string.format(u=self.library_id, t=self.library_type))
        except KeyError as err:
            raise ze.ParamNotPassed(f"There's a request parameter missing: {err}")
        # Add the URL parameters and the user key, if necessary
        if no_params is False:
            if not self.url_params:
                self.add_parameters()
            query = f"{query}?{self.url_params}"
        return query

    @retrieve
    def publications(self):
        """Return the contents of My Publications"""
        if self.library_type != "users":
            raise ze.CallDoesNotExist(
                "This API call does not exist for group libraries"
            )
        query_string = "/{t}/{u}/publications/items"
        return self._build_query(query_string)

    # The following methods are Zotero Read API calls
    def num_items(self):
        """Return the total number of top-level items in the library"""
        query = "/{t}/{u}/items/top"
        return self._totals(query)

    def count_items(self):
        """Return the count of all items in a group / library"""
        query = "/{t}/{u}/items"
        return self._totals(query)

    def num_collectionitems(self, collection):
        """Return the total number of items in the specified collection"""
        query = "/{t}/{u}/collections/{c}/items".format(
            u=self.library_id, t=self.library_type, c=collection.upper()
        )
        return self._totals(query)

    def _totals(self, query):
        """General method for returning total counts"""
        self.add_parameters(limit=1)
        query = self._build_query(query)
        self._retrieve_data(query)
        self.url_params = None
        # extract the 'total items' figure
        return int(self.request.headers["Total-Results"])

    @retrieve
    def key_info(self, **kwargs):
        """
        Retrieve info about the permissions associated with the
        key associated to the given Zotero instance
        """
        query_string = "/keys/{k}".format(k=self.api_key)
        return self._build_query(query_string)

    @retrieve
    def items(self, **kwargs):
        """Get user items"""
        query_string = "/{t}/{u}/items"
        return self._build_query(query_string)

    @retrieve
    def fulltext_item(self, itemkey, **kwargs):
        """Get full-text content for an item"""
        query_string = "/{t}/{u}/items/{itemkey}/fulltext".format(
            t=self.library_type, u=self.library_id, itemkey=itemkey
        )
        return self._build_query(query_string)

    @backoff_check
    def set_fulltext(self, itemkey, payload):
        """
        Set full-text data for an item
        <itemkey> should correspond to an existing attachment item.
        payload should be a dict containing three keys:
        'content': the full-text content and either
        For text documents, 'indexedChars' and 'totalChars' OR
        For PDFs, 'indexedPages' and 'totalPages'.
        """
        headers = {}
        headers.update({"Content-Type": "application/json"})
        return self.client.put(
            url=build_url(
                self.endpoint,
                "/{t}/{u}/items/{k}/fulltext".format(
                    t=self.library_type, u=self.library_id, k=itemkey
                ),
            ),
            headers=headers,
            content=json.dumps(payload),
        )

    def new_fulltext(self, since):
        """
        Retrieve list of full-text content items and versions which are newer
        than <since>
        """
        query_string = "/{t}/{u}/fulltext?since={version}".format(
            t=self.library_type, u=self.library_id, version=since
        )
        headers = {}
        self._check_backoff()
        resp = self.client.get(build_url(self.endpoint, query_string), headers=headers)
        try:
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            error_handler(self, resp, exc)
        backoff = self.request.headers.get("backoff") or self.request.headers.get(
            "retry-after"
        )
        if backoff:
            self._set_backoff(backoff)
        return resp.json()

    def item_versions(self, **kwargs):
        """
        Returns dict associating items keys (all no limit by default) to versions.
        Accepts a since= parameter in kwargs to limit the data to those updated since since=
        """
        if "limit" not in kwargs:
            kwargs["limit"] = None
        kwargs["format"] = "versions"
        return self.items(**kwargs)

    def collection_versions(self, **kwargs):
        """
        Returns dict associating collection keys (all no limit by default) to versions.
        Accepts a since= parameter in kwargs to limit the data to those updated since since=
        """
        if "limit" not in kwargs:
            kwargs["limit"] = None
        kwargs["format"] = "versions"
        return self.collections(**kwargs)

    def last_modified_version(self, **kwargs):
        """Get the last modified user or group library version"""
        # This MUST be a multiple-object request, limit param notwithstanding
        self.items(limit=1)
        lmv = self.request.headers.get("last-modified-version", 0)
        return int(lmv)

    @retrieve
    def top(self, **kwargs):
        """Get user top-level items"""
        query_string = "/{t}/{u}/items/top"
        return self._build_query(query_string)

    @retrieve
    def trash(self, **kwargs):
        """Get all items in the trash"""
        query_string = "/{t}/{u}/items/trash"
        return self._build_query(query_string)

    @retrieve
    def searches(self, **kwargs):
        """Get saved searches"""
        query_string = "/{t}/{u}/searches"
        return self._build_query(query_string)

    @retrieve
    def deleted(self, **kwargs):
        """Get all deleted items (requires since= parameter)"""
        if "limit" not in kwargs:
            # Currently deleted API doesn't respect limit leaving it out by
            # default preserves compat
            kwargs["limit"] = None
        query_string = "/{t}/{u}/deleted"
        return self._build_query(query_string)

    @retrieve
    def item(self, item, **kwargs):
        """Get a specific item"""
        query_string = "/{t}/{u}/items/{i}".format(
            u=self.library_id, t=self.library_type, i=item.upper()
        )
        return self._build_query(query_string)

    @retrieve
    def file(self, item, **kwargs):
        """Get the file from a specific item"""
        query_string = "/{t}/{u}/items/{i}/file".format(
            u=self.library_id, t=self.library_type, i=item.upper()
        )
        return self._build_query(query_string, no_params=True)

    def dump(self, itemkey, filename=None, path=None):
        """
        Dump a file attachment to disk, with optional filename and path
        """
        if not filename:
            filename = self.item(itemkey)["data"]["filename"]
        if path:
            pth = os.path.join(path, filename)
        else:
            pth = filename
        file = self.file(itemkey)
        if self.snapshot:
            self.snapshot = False
            pth = pth + ".zip"
        with open(pth, "wb") as f:
            f.write(file)

    @retrieve
    def children(self, item, **kwargs):
        """Get a specific item's child items"""
        query_string = "/{t}/{u}/items/{i}/children".format(
            u=self.library_id, t=self.library_type, i=item.upper()
        )
        return self._build_query(query_string)

    @retrieve
    def collection_items(self, collection, **kwargs):
        """Get a specific collection's items"""
        query_string = "/{t}/{u}/collections/{c}/items".format(
            u=self.library_id, t=self.library_type, c=collection.upper()
        )
        return self._build_query(query_string)

    @retrieve
    def collection_items_top(self, collection, **kwargs):
        """Get a specific collection's top-level items"""
        query_string = "/{t}/{u}/collections/{c}/items/top".format(
            u=self.library_id, t=self.library_type, c=collection.upper()
        )
        return self._build_query(query_string)

    @retrieve
    def collection_tags(self, collection, **kwargs):
        """Get a specific collection's tags"""
        query_string = "/{t}/{u}/collections/{c}/tags".format(
            u=self.library_id, t=self.library_type, c=collection.upper()
        )
        return self._build_query(query_string)

    @retrieve
    def collection(self, collection, **kwargs):
        """Get user collection"""
        query_string = "/{t}/{u}/collections/{c}".format(
            u=self.library_id, t=self.library_type, c=collection.upper()
        )
        return self._build_query(query_string)

    @retrieve
    def collections(self, **kwargs):
        """Get user collections"""
        query_string = "/{t}/{u}/collections"
        return self._build_query(query_string)

    def all_collections(self, collid=None):
        """
        Retrieve all collections and subcollections. Works for top-level collections
        or for a specific collection. Works at all collection depths.
        """
        all_collections = []

        def subcoll(clct):
            """recursively add collections to a flat master list"""
            all_collections.append(clct)
            if clct["meta"].get("numCollections", 0) > 0:
                # add collection to master list & recur with all child
                # collections
                [
                    subcoll(c)
                    for c in self.everything(self.collections_sub(clct["data"]["key"]))
                ]

        # select all top-level collections or a specific collection and
        # children
        if collid:
            toplevel = [self.collection(collid)]
        else:
            toplevel = self.everything(self.collections_top())
        [subcoll(collection) for collection in toplevel]
        return all_collections

    @retrieve
    def collections_top(self, **kwargs):
        """Get top-level user collections"""
        query_string = "/{t}/{u}/collections/top"
        return self._build_query(query_string)

    @retrieve
    def collections_sub(self, collection, **kwargs):
        """Get subcollections for a specific collection"""
        query_string = "/{t}/{u}/collections/{c}/collections".format(
            u=self.library_id, t=self.library_type, c=collection.upper()
        )
        return self._build_query(query_string)

    @retrieve
    def groups(self, **kwargs):
        """Get user groups"""
        query_string = "/users/{u}/groups"
        return self._build_query(query_string)

    @retrieve
    def tags(self, **kwargs):
        """Get tags"""
        query_string = "/{t}/{u}/tags"
        self.tag_data = True
        return self._build_query(query_string)

    @retrieve
    def item_tags(self, item, **kwargs):
        """Get tags for a specific item"""
        query_string = "/{t}/{u}/items/{i}/tags".format(
            u=self.library_id, t=self.library_type, i=item.upper()
        )
        self.tag_data = True
        return self._build_query(query_string)

    def all_top(self, **kwargs):
        """Retrieve all top-level items"""
        return self.everything(self.top(**kwargs))

    @retrieve
    def follow(self):
        """Return the result of the call to the URL in the 'Next' link"""
        if n := self.links.get("next"):
            newurl = self._striplocal(n)
            print(newurl)
            return newurl
        return

    def iterfollow(self):
        """Generator for self.follow()"""
        # use same criterion as self.follow()
        while True:
            if self.links.get("next"):
                yield self.follow()
            else:
                return

    def makeiter(self, func):
        """Return a generator of func's results"""
        # reset the link. This results in an extra API call, yes
        self.links["next"] = self.links["self"]
        return self.iterfollow()

    def everything(self, query):
        """
        Retrieve all items in the library for a particular query
        This method will override the 'limit' parameter if it's been set
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
        """
        Retrieve a subset of items
        Accepts a single argument: a list of item IDs
        """
        if len(subset) > 50:
            raise ze.TooManyItems("You may only retrieve 50 items per call")
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
        """Format and return data from API calls which return Items"""
        json_kwargs = {}
        if self.preserve_json_order:
            json_kwargs["object_pairs_hook"] = OrderedDict
        # send entries to _tags_data if there's no JSON
        try:
            items = [
                json.loads(e["content"][0]["value"], **json_kwargs)
                for e in retrieved.entries
            ]
        except KeyError:
            return self._tags_data(retrieved)
        return items

    def _csljson_processor(self, retrieved):
        """Return a list of dicts which are dumped CSL JSON"""
        items = []
        json_kwargs = {}
        if self.preserve_json_order:
            json_kwargs["object_pairs_hook"] = OrderedDict
        for csl in retrieved.entries:
            items.append(json.loads(csl["content"][0]["value"], **json_kwargs))
        self.url_params = None
        return items

    def _bib_processor(self, retrieved):
        """Return a list of strings formatted as HTML bibliography entries"""
        items = []
        for bib in retrieved.entries:
            items.append(bib["content"][0]["value"])
        self.url_params = None
        return items

    def _citation_processor(self, retrieved):
        """Return a list of strings formatted as HTML citation entries"""
        items = []
        for cit in retrieved.entries:
            items.append(cit["content"][0]["value"])
        self.url_params = None
        return items

    def _tags_data(self, retrieved):
        """Format and return data from API calls which return Tags"""
        self.url_params = None
        return [t["tag"] for t in retrieved]

    # The following methods are Write API calls
    def item_template(self, itemtype, linkmode=None):
        """Get a template for a new item"""
        # if we have a template and it hasn't been updated since we stored it
        template_name = f"item_template_{itemtype}_{linkmode or ''}"
        query_string = f"/items/new?itemType={itemtype}"
        if self.templates.get(template_name) and not self._updated(
            query_string, self.templates[template_name], template_name
        ):
            return copy.deepcopy(self.templates[template_name]["tmplt"])

        # Set linkMode parameter for API request if itemtype is attachment
        if itemtype == "attachment":
            query_string = f"{query_string}&linkMode={linkmode}"

        # otherwise perform a normal request and cache the response
        retrieved = self._retrieve_data(query_string)
        return self._cache(retrieved, template_name)

    def _attachment_template(self, attachment_type):
        """
        Return a new attachment template of the required type:
        imported_file
        imported_url
        linked_file
        linked_url
        """
        return self.item_template("attachment&linkMode=" + attachment_type)

    def _attachment(self, payload, parentid=None):
        """
        Create attachments
        accepts a list of one or more attachment template dicts
        and an optional parent Item ID. If this is specified,
        attachments are created under this ID
        """
        attachment = Zupload(self, payload, parentid)
        res = attachment.upload()
        return res

    @ss_wrap
    def show_operators(self):
        """Show available saved search operators"""
        return self.savedsearch.operators

    @ss_wrap
    def show_conditions(self):
        """Show available saved search conditions"""
        return self.savedsearch.conditions_operators.keys()

    @ss_wrap
    def show_condition_operators(self, condition):
        """Show available operators for a given saved search condition"""
        # dict keys of allowed operators for the current condition
        permitted_operators = self.savedsearch.conditions_operators.get(condition)
        # transform these into values
        permitted_operators_list = set(
            [self.savedsearch.operators.get(op) for op in permitted_operators]
        )
        return permitted_operators_list

    @ss_wrap
    def saved_search(self, name, conditions):
        """Create a saved search. conditions is a list of dicts
        containing search conditions and must contain the following str keys:
        condition, operator, value
        """
        self.savedsearch._validate(conditions)
        payload = [{"name": name, "conditions": conditions}]
        headers = {"Zotero-Write-Token": token()}
        self._check_backoff()
        req = self.client.post(
            url=build_url(
                self.endpoint,
                "/{t}/{u}/searches".format(t=self.library_type, u=self.library_id),
            ),
            headers=headers,
            content=json.dumps(payload),
        )
        self.request = req
        try:
            req.raise_for_status()
        except httpx.HTTPError as exc:
            error_handler(self, req, exc)
        backoff = self.request.headers.get("backoff") or self.request.headers.get(
            "retry-after"
        )
        if backoff:
            self._set_backoff(backoff)
        return req.json()

    @ss_wrap
    def delete_saved_search(self, keys):
        """Delete one or more saved searches by passing a list of one or more
        unique search keys
        """
        headers = {"Zotero-Write-Token": token()}
        self._check_backoff()
        req = self.client.delete(
            url=build_url(
                self.endpoint,
                "/{t}/{u}/searches".format(t=self.library_type, u=self.library_id),
            ),
            headers=headers,
            params={"searchKey": ",".join(keys)},
        )
        self.request = req
        try:
            req.raise_for_status()
        except httpx.HTTPError as exc:
            error_handler(self, req, exc)
        backoff = self.request.headers.get("backoff") or self.request.headers.get(
            "retry-after"
        )
        if backoff:
            self._set_backoff(backoff)
        return req.status_code

    def upload_attachments(self, attachments, parentid=None, basedir=None):
        """Upload files to the already created (but never uploaded) attachments"""
        return Zupload(self, attachments, parentid, basedir=basedir).upload()

    def add_tags(self, item, *tags):
        """
        Add one or more tags to a retrieved item,
        then update it on the server
        Accepts a dict, and one or more tags to add to it
        Returns the updated item from the server
        """
        # Make sure there's a tags field, or add one
        try:
            assert item["data"]["tags"]
        except AssertionError:
            item["data"]["tags"] = list()
        for tag in tags:
            item["data"]["tags"].append({"tag": f"{tag}"})
        # make sure everything's OK
        assert self.check_items([item])
        return self.update_item(item)

    def check_items(self, items):
        """
        Check that items to be created contain no invalid dict keys
        Accepts a single argument: a list of one or more dicts
        The retrieved fields are cached and re-used until a 304 call fails
        """
        params = {"locale": self.locale, "timeout": timeout}
        query_string = "/itemFields"
        r = Request(
            "GET",
            build_url(self.endpoint, query_string),
            params=params,
        )
        with httpx.Client() as client:
            response = client.send(r)
        # now split up the URL
        result = urlparse(str(response.url))
        # construct cache key
        cachekey = result.path + "_" + result.query
        if self.templates.get(cachekey) and not self._updated(
            query_string, self.templates[cachekey], cachekey
        ):
            template = set(t["field"] for t in self.templates[cachekey]["tmplt"])
        else:
            template = set(t["field"] for t in self.item_fields())
        # add fields we know to be OK
        template = template | set(
            [
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
            ]
        )
        template = template | set(self.temp_keys)
        for pos, item in enumerate(items):
            if set(item) == set(["links", "library", "version", "meta", "key", "data"]):
                # we have an item that was retrieved from the API
                item = item["data"]
            to_check = set(i for i in list(item.keys()))
            difference = to_check.difference(template)
            if difference:
                raise ze.InvalidItemFields(
                    f"Invalid keys present in item {pos + 1}: {' '.join(i for i in difference)}"
                )
        return items

    @tcache
    def item_types(self):
        """Get all available item types"""
        # Check for a valid cached version
        params = {"locale": self.locale}
        query_string = "/itemTypes"
        return query_string, params

    @tcache
    def creator_fields(self):
        """Get localised creator fields"""
        # Check for a valid cached version
        params = {"locale": self.locale}
        query_string = "/creatorFields"
        return query_string, params

    @tcache
    def item_type_fields(self, itemtype):
        """Get all valid fields for an item"""
        params = {"itemType": itemtype, "locale": self.locale}
        query_string = "/itemTypeFields"
        return query_string, params

    @tcache
    def item_creator_types(self, itemtype):
        """Get all available creator types for an item"""
        params = {"itemType": itemtype, "locale": self.locale}
        query_string = "/itemTypeCreatorTypes"
        return query_string, params

    @tcache
    def item_fields(self):
        """Get all available item fields"""
        # Check for a valid cached version
        params = {"locale": self.locale}
        query_string = "/itemFields"
        return query_string, params

    def item_attachment_link_modes(self):
        """Get all available link mode types.
        Note: No viable REST API route was found for this, so I tested and built a list from documentation found
        here - https://www.zotero.org/support/dev/web_api/json
        """
        return ["imported_file", "imported_url", "linked_file", "linked_url"]

    def create_items(self, payload, parentid=None, last_modified=None):
        """
        Create new Zotero items
        Accepts two arguments:
            a list containing one or more item dicts
            an optional parent item ID.
        Note that this can also be used to update existing items
        """
        if len(payload) > 50:
            raise ze.TooManyItems("You may only create up to 50 items per call")
        # TODO: strip extra data if it's an existing item
        headers = {"Zotero-Write-Token": token(), "Content-Type": "application/json"}
        if last_modified is not None:
            headers["If-Unmodified-Since-Version"] = str(last_modified)
        to_send = json.dumps([i for i in self._cleanup(*payload, allow=("key"))])
        self._check_backoff()
        req = self.client.post(
            url=build_url(
                self.endpoint,
                "/{t}/{u}/items".format(t=self.library_type, u=self.library_id),
            ),
            content=to_send,
            headers=dict(headers),
        )
        self.request = req
        try:
            req.raise_for_status()
        except httpx.HTTPError as exc:
            error_handler(self, req, exc)
        resp = req.json()
        backoff = self.request.headers.get("backoff") or self.request.headers.get(
            "retry-after"
        )
        if backoff:
            self._set_backoff(backoff)
        if parentid:
            # we need to create child items using PATCH
            # TODO: handle possibility of item creation + failed parent
            # attachment
            uheaders = {
                "If-Unmodified-Since-Version": req.headers["last-modified-version"]
            }
            for value in resp["success"].values():
                payload = json.dumps({"parentItem": parentid})
                self._check_backoff()
                presp = self.client.patch(
                    url=build_url(
                        self.endpoint,
                        "/{t}/{u}/items/{v}".format(
                            t=self.library_type, u=self.library_id, v=value
                        ),
                    ),
                    content=payload,
                    headers=dict(uheaders),
                )
                self.request = presp
                try:
                    presp.raise_for_status()
                except httpx.HTTPError as exc:
                    error_handler(self, presp, exc)
                backoff = presp.headers.get("backoff") or presp.headers.get(
                    "retry-after"
                )
                if backoff:
                    self._set_backoff(backoff)
        return resp

    def create_collection(self, payload, last_modified=None):
        """Alias for create_collections to preserve backward compatibility"""
        return self.create_collections(payload, last_modified)

    def create_collections(self, payload, last_modified=None):
        """
        Create new Zotero collections
        Accepts one argument, a list of dicts containing the following keys:

        'name': the name of the collection
        'parentCollection': OPTIONAL, the parent collection to which you wish to add this
        """
        # no point in proceeding if there's no 'name' key
        for item in payload:
            if "name" not in item:
                raise ze.ParamNotPassed("The dict you pass must include a 'name' key")
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
                "/{t}/{u}/collections".format(t=self.library_type, u=self.library_id),
            ),
            headers=headers,
            content=json.dumps(payload),
        )
        self.request = req
        try:
            req.raise_for_status()
        except httpx.HTTPError as exc:
            error_handler(self, req, exc)
        backoff = req.headers.get("backoff") or req.headers.get("retry-after")
        if backoff:
            self._set_backoff(backoff)
        return req.json()

    @backoff_check
    def update_collection(self, payload, last_modified=None):
        """
        Update a Zotero collection property such as 'name'
        Accepts one argument, a dict containing collection data retrieved
        using e.g. 'collections()'
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
                "/{t}/{u}/collections/{c}".format(
                    t=self.library_type, u=self.library_id, c=key
                ),
            ),
            headers=headers,
            content=json.dumps(payload),
        )

    def attachment_simple(self, files, parentid=None):
        """
        Add attachments using filenames as title
        Arguments:
        One or more file paths to add as attachments:
        An optional Item ID, which will create child attachments
        """
        orig = self._attachment_template("imported_file")
        to_add = [orig.copy() for fls in files]
        for idx, tmplt in enumerate(to_add):
            tmplt["title"] = os.path.basename(files[idx])
            tmplt["filename"] = files[idx]
        if parentid:
            return self._attachment(to_add, parentid)
        else:
            return self._attachment(to_add)

    def attachment_both(self, files, parentid=None):
        """
        Add child attachments using title, filename
        Arguments:
        One or more lists or tuples containing title, file path
        An optional Item ID, which will create child attachments
        """
        orig = self._attachment_template("imported_file")
        to_add = [orig.copy() for f in files]
        for idx, tmplt in enumerate(to_add):
            tmplt["title"] = files[idx][0]
            tmplt["filename"] = files[idx][1]
        if parentid:
            return self._attachment(to_add, parentid)
        else:
            return self._attachment(to_add)

    @backoff_check
    def update_item(self, payload, last_modified=None):
        """
        Update an existing item
        Accepts one argument, a dict containing Item data
        """
        to_send = self.check_items([payload])[0]
        if last_modified is None:
            modified = payload["version"]
        else:
            modified = last_modified
        ident = payload["key"]
        headers = {"If-Unmodified-Since-Version": str(modified)}
        return self.client.patch(
            url=build_url(
                self.endpoint,
                "/{t}/{u}/items/{id}".format(
                    t=self.library_type, u=self.library_id, id=ident
                ),
            ),
            headers=headers,
            content=json.dumps(to_send),
        )

    def update_items(self, payload):
        """
        Update existing items
        Accepts one argument, a list of dicts containing Item data
        """
        to_send = [self.check_items([p])[0] for p in payload]
        # the API only accepts 50 items at a time, so we have to split
        # anything longer
        for chunk in chunks(to_send, 50):
            self._check_backoff()
            req = self.client.post(
                url=build_url(
                    self.endpoint,
                    "/{t}/{u}/items/".format(t=self.library_type, u=self.library_id),
                ),
                content=json.dumps(chunk),
            )
            self.request = req
            try:
                req.raise_for_status()
            except httpx.HTTPError as exc:
                error_handler(self, req, exc)
            backoff = req.headers.get("backoff") or req.headers.get("retry-after")
            if backoff:
                self._set_backoff(backoff)
        return True

    def update_collections(self, payload):
        """
        Update existing collections
        Accepts one argument, a list of dicts containing Collection data
        """
        to_send = [self.check_items([p])[0] for p in payload]
        # the API only accepts 50 items at a time, so we have to split
        # anything longer
        for chunk in chunks(to_send, 50):
            self._check_backoff()
            req = self.client.post(
                url=build_url(
                    self.endpoint,
                    "/{t}/{u}/collections/".format(
                        t=self.library_type, u=self.library_id
                    ),
                ),
                content=json.dumps(chunk),
            )
            self.request = req
            try:
                req.raise_for_status()
            except httpx.HTTPError as exc:
                error_handler(self, req, exc)
            backoff = req.headers.get("backoff") or req.headers.get("retry-after")
            if backoff:
                self._set_backoff(backoff)
        return True

    @backoff_check
    def addto_collection(self, collection, payload):
        """
        Add one or more items to a collection
        Accepts two arguments:
        The collection ID, and an item dict
        """
        ident = payload["key"]
        modified = payload["version"]
        # add the collection data from the item
        modified_collections = payload["data"]["collections"] + [collection]
        headers = {"If-Unmodified-Since-Version": str(modified)}
        return self.client.patch(
            url=build_url(
                self.endpoint,
                "/{t}/{u}/items/{i}".format(
                    t=self.library_type, u=self.library_id, i=ident
                ),
            ),
            content=json.dumps({"collections": modified_collections}),
            headers=headers,
        )

    @backoff_check
    def deletefrom_collection(self, collection, payload):
        """
        Delete an item from a collection
        Accepts two arguments:
        The collection ID, and and an item dict
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
                "/{t}/{u}/items/{i}".format(
                    t=self.library_type, u=self.library_id, i=ident
                ),
            ),
            content=json.dumps({"collections": modified_collections}),
            headers=headers,
        )

    @backoff_check
    def delete_tags(self, *payload):
        """
        Delete a group of tags
        pass in up to 50 tags, or use *[tags]

        """
        if len(payload) > 50:
            raise ze.TooManyItems("Only 50 tags or fewer may be deleted")
        modified_tags = " || ".join([tag for tag in payload])
        # first, get version data by getting one tag
        self.tags(limit=1)
        headers = {
            "If-Unmodified-Since-Version": self.request.headers["last-modified-version"]
        }
        return self.client.delete(
            url=build_url(
                self.endpoint,
                "/{t}/{u}/tags".format(t=self.library_type, u=self.library_id),
            ),
            params={"tag": modified_tags},
            headers=headers,
        )

    @backoff_check
    def delete_item(self, payload, last_modified=None):
        """
        Delete Items from a Zotero library
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
                "/{t}/{u}/items".format(t=self.library_type, u=self.library_id),
            )
        else:
            ident = payload["key"]
            if last_modified is not None:
                modified = last_modified
            else:
                modified = payload["version"]
            url = build_url(
                self.endpoint,
                "/{t}/{u}/items/{c}".format(
                    t=self.library_type, u=self.library_id, c=ident
                ),
            )
        headers = {"If-Unmodified-Since-Version": str(modified)}
        return self.client.delete(url=url, params=params, headers=headers)

    @backoff_check
    def delete_collection(self, payload, last_modified=None):
        """
        Delete a Collection from a Zotero library
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
                "/{t}/{u}/collections".format(t=self.library_type, u=self.library_id),
            )
        else:
            ident = payload["key"]
            if last_modified is not None:
                modified = last_modified
            else:
                modified = payload["version"]
            url = build_url(
                self.endpoint,
                "/{t}/{u}/collections/{c}".format(
                    t=self.library_type, u=self.library_id, c=ident
                ),
            )
        headers = {"If-Unmodified-Since-Version": str(modified)}
        return self.client.delete(url=url, params=params, headers=headers)


def error_handler(zot, req, exc=None):
    """Error handler for HTTP requests"""
    error_codes = {
        400: ze.UnsupportedParams,
        401: ze.UserNotAuthorised,
        403: ze.UserNotAuthorised,
        404: ze.ResourceNotFound,
        409: ze.Conflict,
        412: ze.PreConditionFailed,
        413: ze.RequestEntityTooLarge,
        428: ze.PreConditionRequired,
        429: ze.TooManyRequests,
    }

    def err_msg(req):
        """Return a nicely-formatted error message"""
        return f"\nCode: {req.status_code}\nURL: {str(req.url)}\nMethod: {req.request.method}\nResponse: {req.text}"

    if error_codes.get(req.status_code):
        # check to see whether its 429
        if req.status_code == 429:
            # try to get backoff or delay duration
            delay = req.headers.get("backoff") or req.headers.get("retry-after")
            if not delay:
                raise ze.TooManyRetries(
                    "You are being rate-limited and no backoff or retry duration has been received from the server. Try again later"
                )
            else:
                zot._set_backoff(delay)
        else:
            if not exc:
                raise error_codes.get(req.status_code)(err_msg(req))
            else:
                raise error_codes.get(req.status_code)(err_msg(req)) from exc
    else:
        if not exc:
            raise ze.HTTPError(err_msg(req))
        else:
            raise ze.HTTPError(err_msg(req)) from exc


class SavedSearch:
    """Saved search functionality
    See https://github.com/zotero/zotero/blob/master/chrome/content/zotero/xpcom/data/searchConditions.js
    """

    def __init__(self, zinstance):
        super(SavedSearch, self).__init__()
        self.zinstance = zinstance
        self.searchkeys = ("condition", "operator", "value")
        # always exclude these fields from zotero.item_keys()
        self.excluded_items = (
            "accessDate",
            "date",
            "pages",
            "section",
            "seriesNumber",
            "issue",
        )
        self.operators = {
            # this is a bit hacky, but I can't be bothered with Python's enums
            "is": "is",
            "isNot": "isNot",
            "beginsWith": "beginsWith",
            "contains": "contains",
            "doesNotContain": "doesNotContain",
            "isLessThan": "isLessThan",
            "isGreaterThan": "isGreaterThan",
            "isBefore": "isBefore",
            "isAfter": "isAfter",
            "isInTheLast": "isInTheLast",
            "any": "any",
            "all": "all",
            "true": "true",
            "false": "false",
        }
        # common groupings of operators
        self.groups = {
            "A": (self.operators["true"], self.operators["false"]),
            "B": (self.operators["any"], self.operators["all"]),
            "C": (
                self.operators["is"],
                self.operators["isNot"],
                self.operators["contains"],
                self.operators["doesNotContain"],
            ),
            "D": (self.operators["is"], self.operators["isNot"]),
            "E": (
                self.operators["is"],
                self.operators["isNot"],
                self.operators["isBefore"],
                self.operators["isInTheLast"],
            ),
            "F": (self.operators["contains"], self.operators["doesNotContain"]),
            "G": (
                self.operators["is"],
                self.operators["isNot"],
                self.operators["contains"],
                self.operators["doesNotContain"],
                self.operators["isLessThan"],
                self.operators["isGreaterThan"],
            ),
            "H": (
                self.operators["is"],
                self.operators["isNot"],
                self.operators["beginsWith"],
            ),
            "I": (self.operators["is"]),
        }
        self.conditions_operators = {
            "deleted": self.groups["A"],
            "noChildren": self.groups["A"],
            "unfiled": self.groups["A"],
            "publications": self.groups["A"],
            "retracted": self.groups["A"],
            "includeParentsAndChildren": self.groups["A"],
            "includeParents": self.groups["A"],
            "includeChildren": self.groups["A"],
            "recursive": self.groups["A"],
            "joinMode": self.groups["B"],
            "quicksearch-titleCreatorYear": self.groups["C"],
            "quicksearch-titleCreatorYearNote": self.groups["C"],
            "quicksearch-fields": self.groups["C"],
            "quicksearch-everything": self.groups["C"],
            "collectionID": self.groups["D"],
            "savedSearchID": self.groups["D"],
            "collection": self.groups["D"],
            "savedSearch": self.groups["D"],
            "dateAdded": self.groups["E"],
            "dateModified": self.groups["E"],
            "itemType": self.groups["D"],
            "fileTypeID": self.groups["D"],
            "tagID": self.groups["D"],
            "tag": self.groups["C"],
            "note": self.groups["F"],
            "childNote": self.groups["F"],
            "creator": self.groups["C"],
            "lastName": self.groups["C"],
            "field": self.groups["C"],
            "datefield": self.groups["E"],
            "year": self.groups["C"],
            "numberfield": self.groups["G"],
            "libraryID": self.groups["D"],
            "key": self.groups["H"],
            "itemID": self.groups["D"],
            "annotationText": self.groups["F"],
            "annotationComment": self.groups["F"],
            "fulltextWord": self.groups["F"],
            "fulltextContent": self.groups["F"],
            "tempTable": self.groups["I"],
        }
        ###########
        # ALIASES #
        ###########
        # aliases for numberfield
        pagefields = (
            "pages",
            "numPages",
            "numberOfVolumes",
            "section",
            "seriesNumber",
            "issue",
        )
        for pf in pagefields:
            self.conditions_operators[pf] = self.conditions_operators.get("numberfield")
        # aliases for datefield
        datefields = ("accessDate", "date", "dateDue", "accepted")
        for df in datefields:
            self.conditions_operators[df] = self.conditions_operators.get("datefield")
        # aliases for field - this makes a blocking API call unless item types have been cached
        item_fields = [
            itm["field"]
            for itm in self.zinstance.item_fields()
            if itm["field"] not in set(self.excluded_items)
        ]
        for itf in item_fields:
            self.conditions_operators[itf] = self.conditions_operators.get("field")

    def _validate(self, conditions):
        """Validate saved search conditions, raising an error if any contain invalid operators"""
        allowed_keys = set(self.searchkeys)
        operators_set = set(self.operators.keys())
        for condition in conditions:
            if set(condition.keys()) != allowed_keys:
                raise ze.ParamNotPassed(
                    f"Keys must be all of: {', '.join(self.searchkeys)}"
                )
            if condition.get("operator") not in operators_set:
                raise ze.ParamNotPassed(
                    f"You have specified an unknown operator: {condition.get('operator')}"
                )
            # dict keys of allowed operators for the current condition
            permitted_operators = self.conditions_operators.get(
                condition.get("condition")
            )
            # transform these into values
            permitted_operators_list = set(
                [self.operators.get(op) for op in permitted_operators]
            )
            if condition.get("operator") not in permitted_operators_list:
                raise ze.ParamNotPassed(
                    f"You may not use the '{condition.get('operator')}' operator when selecting the '{condition.get('condition')}' condition. \nAllowed operators: {', '.join(list(permitted_operators_list))}"
                )


class Zupload:
    """
    Zotero file attachment helper
    Receives a Zotero instance, file(s) to upload, and optional parent ID

    """

    def __init__(self, zinstance, payload, parentid=None, basedir=None):
        super(Zupload, self).__init__()
        self.zinstance = zinstance
        self.payload = payload
        self.parentid = parentid
        if basedir is None:
            self.basedir = Path("")
        elif isinstance(basedir, Path):
            self.basedir = basedir
        else:
            self.basedir = Path(basedir)

    def _verify(self, payload):
        """
        ensure that all files to be attached exist
        open()'s better than exists(), cos it avoids a race condition
        """
        if not payload:  # Check payload has nonzero length
            raise ze.ParamNotPassed
        for templt in payload:
            if os.path.isfile(str(self.basedir.joinpath(templt["filename"]))):
                try:
                    # if it is a file, try to open it, and catch the error
                    with open(str(self.basedir.joinpath(templt["filename"]))):
                        pass
                except IOError:
                    raise ze.FileDoesNotExist(
                        f"The file at {str(self.basedir.joinpath(templt['filename']))} couldn't be opened or found."
                    )
            # no point in continuing if the file isn't a file
            else:
                raise ze.FileDoesNotExist(
                    f"The file at {str(self.basedir.joinpath(templt['filename']))} couldn't be opened or found."
                )

    def _create_prelim(self):
        """
        Step 0: Register intent to upload files
        """
        self._verify(self.payload)
        if "key" in self.payload[0] and self.payload[0]["key"]:
            if next((i for i in self.payload if "key" not in i), False):
                raise ze.UnsupportedParams(
                    "Can't pass payload entries with and without keys to Zupload"
                )
            return None  # Don't do anything if payload comes with keys
        liblevel = "/{t}/{u}/items"
        # Create one or more new attachments
        headers = {"Zotero-Write-Token": token(), "Content-Type": "application/json"}
        # If we have a Parent ID, add it as a parentItem
        if self.parentid:
            for child in self.payload:
                child["parentItem"] = self.parentid
        to_send = json.dumps(self.payload)
        self.zinstance._check_backoff()
        req = self.client.post(
            url=build_url(
                self.zinstance.endpoint,
                liblevel.format(
                    t=self.zinstance.library_type, u=self.zinstance.library_id
                ),
            ),
            content=to_send,
            headers=headers,
        )
        try:
            req.raise_for_status()
        except httpx.HTTPError as exc:
            error_handler(self.zinstance, req, exc)
        backoff = req.headers.get("backoff") or req.headers.get("retry-after")
        if backoff:
            self.zinstance._set_backoff(backoff)
        data = req.json()
        for k in data["success"]:
            self.payload[int(k)]["key"] = data["success"][k]
        return data

    def _get_auth(self, attachment, reg_key, md5=None):
        """
        Step 1: get upload authorisation for a file
        """
        mtypes = mimetypes.guess_type(attachment)
        digest = hashlib.md5()
        with open(attachment, "rb") as att:
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
            "filename": os.path.basename(attachment),
            "filesize": os.path.getsize(attachment),
            "mtime": str(int(os.path.getmtime(attachment) * 1000)),
            "contentType": mtypes[0] or "application/octet-stream",
            "charset": mtypes[1],
            "params": 1,
        }
        self.zinstance._check_backoff()
        auth_req = self.zinstance.client.post(
            url=build_url(
                self.zinstance.endpoint,
                "/{t}/{u}/items/{i}/file".format(
                    t=self.zinstance.library_type,
                    u=self.zinstance.library_id,
                    i=reg_key,
                ),
            ),
            content=data,
            headers=auth_headers,
        )
        try:
            auth_req.raise_for_status()
        except httpx.HTTPError as exc:
            error_handler(self.zinstance, auth_req, exc)
        backoff = auth_req.headers.get("backoff") or auth_req.headers.get("retry-after")
        if backoff:
            self.zinstance._set_backoff(backoff)
        return auth_req.json()

    def _upload_file(self, authdata, attachment, reg_key):
        """
        Step 2: auth successful, and file not on server
        zotero.org/support/dev/server_api/file_upload#a_full_upload

        reg_key isn't used, but we need to pass it through to Step 3
        """
        upload_dict = authdata["params"]
        # pass tuple of tuples (not dict!), to ensure key comes first
        upload_list = [("key", upload_dict.pop("key"))]
        for key, value in upload_dict.items():
            upload_list.append((key, value))
        upload_list.append(("file", open(attachment, "rb").read()))
        upload_pairs = tuple(upload_list)
        try:
            self.zinstance._check_backoff()
            upload = self.client.post(
                url=authdata["url"],
                files=upload_pairs,
                headers={"User-Agent": f"Pyzotero/{pz.__version__}"},
            )
        except httpx.ConnectionError:
            raise ze.UploadError("ConnectionError")
        try:
            upload.raise_for_status()
        except httpx.HTTPError as exc:
            error_handler(self.zinstance, upload, exc)
        backoff = upload.headers.get("backoff") or upload.headers.get("retry-after")
        if backoff:
            self.zinstance._set_backoff(backoff)
        # now check the responses
        return self._register_upload(authdata, reg_key)

    def _register_upload(self, authdata, reg_key):
        """
        Step 3: upload successful, so register it
        """
        reg_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "If-None-Match": "*",
        }
        reg_data = {"upload": authdata.get("uploadKey")}
        self.zinstance._check_backoff()
        upload_reg = self.zinstane.client.post(
            url=build_url(
                self.zinstance.endpoint,
                "/{t}/{u}/items/{i}/file".format(
                    t=self.zinstance.library_type,
                    u=self.zinstance.library_id,
                    i=reg_key,
                ),
            ),
            content=reg_data,
            headers=dict(reg_headers),
        )
        try:
            upload_reg.raise_for_status()
        except httpx.HTTPError as exc:
            error_handler(self.zinstance, upload_reg, exc)
        backoff = upload_reg.headers.get("backoff") or upload_reg.headers.get(
            "retry-after"
        )
        if backoff:
            self._set_backoff(backoff)

    def upload(self):
        """
        File upload functionality

        Goes through upload steps 0 - 3 (private class methods), and returns
        a dict noting success, failure, or unchanged
        (returning the payload entries with that property as a list for each status)
        """
        result = {"success": [], "failure": [], "unchanged": []}
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
