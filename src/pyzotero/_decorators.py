"""Decorator functions for Pyzotero.

These decorators handle caching, backoff, and response processing for API calls.
They are tightly coupled with the Zotero class and are internal implementation details.
"""

from __future__ import annotations

import io
import zipfile
from functools import wraps
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import bibtexparser
import feedparser
import httpx
from httpx import Request

from ._utils import DEFAULT_TIMEOUT, build_url, get_backoff_duration
from .errors import error_handler

if TYPE_CHECKING:
    from collections.abc import Callable


def cleanwrap(func: Callable) -> Callable:
    """Wrap for Zotero._cleanup to process multiple items."""

    @wraps(func)
    def enc(self, *args, **kwargs):
        """Send each item to _cleanup()."""
        return (func(self, item, **kwargs) for item in args)

    return enc


def tcache(func: Callable) -> Callable:
    """Handle URL building and caching for template functions."""

    @wraps(func)
    def wrapped_f(self, *args, **kwargs):
        """Call the decorated function to get query string and params,
        builds URL, retrieves template, caches result, and returns template.
        """
        query_string, params = func(self, *args, **kwargs)
        params["timeout"] = DEFAULT_TIMEOUT
        r = Request(
            "GET",
            build_url(self.endpoint, query_string),
            params=params,
        )
        response = self.client.send(r)

        # now split up the URL
        result = urlparse(str(response.url))
        # construct cache key
        cachekey = f"{result.path}_{result.query}"
        if self.templates.get(cachekey) and not self._updated(
            query_string,
            self.templates[cachekey],
            cachekey,
        ):
            return self.templates[cachekey]["tmplt"]
        # otherwise perform a normal request and cache the response
        retrieved = self._retrieve_data(query_string, params=params)
        return self._cache(retrieved, cachekey)

    return wrapped_f


def backoff_check(func: Callable) -> Callable:
    """Perform backoff processing for write operations.

    func must return a Requests GET / POST / PUT / PATCH / DELETE etc.
    This is intercepted: we first check for an active backoff
    and wait if need be.
    After the response is received, we do normal error checking
    and set a new backoff if necessary, before returning.

    Use with functions that are intended to return True.
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
        backoff = get_backoff_duration(resp.headers)
        if backoff:
            self._set_backoff(backoff)

        return True

    return wrapped_f


def retrieve(func: Callable) -> Callable:
    """Call _retrieve_data() and pass the result to the correct processor."""

    @wraps(func)
    def wrapped_f(self, *args, **kwargs) -> Any:
        """Return result of _retrieve_data().

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
        ) or "bib"
        # select format, or assume JSON
        content_type_header = self.request.headers["Content-Type"].lower() + ";"
        fmt = self.formats.get(
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
                common_strings=True,
                ignore_nonstandard_types=False,
            )
            return parser.parse(retrieved.text)
        # it's binary, so return raw content
        if fmt != "json":
            return retrieved.content
        # no need to do anything special, return JSON
        return retrieved.json()

    return wrapped_f


def ss_wrap(func: Callable) -> Callable:
    """Ensure that a SavedSearch object exists before method execution."""

    def wrapper(self, *args, **kwargs):
        if not self.savedsearch:
            # Import here to avoid circular imports
            from ._search import SavedSearch  # noqa: PLC0415

            self.savedsearch = SavedSearch(self)
        return func(self, *args, **kwargs)

    return wrapper


__all__ = [
    "backoff_check",
    "cleanwrap",
    "retrieve",
    "ss_wrap",
    "tcache",
]
