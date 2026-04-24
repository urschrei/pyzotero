"""Decorator functions for Pyzotero.

These decorators handle caching, backoff, and response processing for API calls.
They are tightly coupled with the Zotero class and are internal implementation details.
"""

from __future__ import annotations

import copy
import io
import zipfile
from collections.abc import Callable, Generator
from functools import wraps
from typing import Any, TypeVar
from urllib.parse import urlencode

import bibtexparser
import feedparser
import httpx

from ._utils import DEFAULT_TIMEOUT, get_backoff_duration
from .errors import error_handler

T = TypeVar("T")


def cleanwrap(func: Callable[..., T]) -> Callable[..., Generator[T, None, None]]:
    """Wrap for Zotero._cleanup to process multiple items."""

    @wraps(func)
    def enc(self: Any, *args: Any, **kwargs: Any) -> Generator[T, None, None]:
        """Send each item to _cleanup()."""
        return (func(self, item, **kwargs) for item in args)

    return enc


def tcache(
    func: Callable[..., tuple[str, dict[str, Any]]],
) -> Callable[..., dict[str, Any]]:
    """Handle URL building and caching for template functions."""

    @wraps(func)
    def wrapped_f(self: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Call the decorated function to get query string and params,
        check the local template cache, and retrieve + cache on miss.
        """
        query_string, params = func(self, *args, **kwargs)
        params["timeout"] = DEFAULT_TIMEOUT
        # Build a stable cache key locally, without a network round-trip.
        cachekey = f"{query_string}?{urlencode(sorted(params.items()))}"
        if self.templates.get(cachekey) and not self._updated(
            query_string,
            self.templates[cachekey],
            cachekey,
        ):
            # Deep-copy so callers may mutate the result without corrupting
            # the cached entry (matches the contract of Zotero._cache).
            return copy.deepcopy(self.templates[cachekey]["tmplt"])
        retrieved = self._retrieve_data(query_string, params=params)
        return self._cache(retrieved, cachekey)

    return wrapped_f


def backoff_check(
    func: Callable[..., httpx.Response],
) -> Callable[..., bool]:
    """Perform backoff processing for write operations.

    func must return a Requests GET / POST / PUT / PATCH / DELETE etc.
    This is intercepted: we first check for an active backoff
    and wait if need be.
    After the response is received, we do normal error checking
    and set a new backoff if necessary, before returning.

    Use with functions that are intended to return True.
    """

    @wraps(func)
    def wrapped_f(self: Any, *args: Any, **kwargs: Any) -> bool:
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


def _extract_zip_attachment(retrieved: httpx.Response) -> bytes:
    """Extract the single file from a Zotero-compressed attachment response.

    The Zotero API zips plain-text attachments when the redirect carries the
    ``Zotero-File-Compressed: Yes`` header. When present, return the inner
    file's bytes; otherwise return the response body as-is.
    """
    if (
        retrieved.history
        and retrieved.history[0].headers.get("Zotero-File-Compressed") == "Yes"
    ):
        z = zipfile.ZipFile(io.BytesIO(retrieved.content))
        return z.read(z.namelist()[0])
    return retrieved.content


def _parse_bibtex(text: str) -> Any:
    """Parse a BibTeX response body into a BibDatabase."""
    parser = bibtexparser.bparser.BibTexParser(
        common_strings=True,
        ignore_nonstandard_types=False,
    )
    return parser.parse(text)


def retrieve(func: Callable[..., str]) -> Callable[..., Any]:
    """Call _retrieve_data() and pass the result to the correct processor."""

    @wraps(func)
    def wrapped_f(self: Any, *args: Any, **kwargs: Any) -> Any:
        """Return result of _retrieve_data().

        func's return value is part of a URI, and it's this
        which is intercepted and passed to _retrieve_data:
        '/users/123/items?key=abc123'
        """
        if kwargs:
            self.add_parameters(**kwargs)
        retrieved = self._retrieve_data(func(self, *args))
        self.links = self._extract_links()
        self.url_params = None

        # Tag responses short-circuit format dispatch.
        if "tags" in str(self.request.url):
            return self._tags_data(retrieved.json())

        content_type = self.request.headers["Content-Type"].lower().split(";", 1)[0]
        fmt = self.formats.get(content_type, "json")

        if fmt == "zip":
            return _extract_zip_attachment(self.request)
        if fmt == "atom":
            content_match = self.content.search(str(self.request.url))
            content = content_match.group(0) if content_match else "bib"
            processor = self.processors.get(content)
            return processor(feedparser.parse(retrieved.text))
        if fmt == "bibtex":
            return _parse_bibtex(retrieved.text)
        if fmt == "json":
            return retrieved.json()
        if fmt == "snapshot":
            # dump() uses this flag to append .zip to the output filename.
            self.snapshot = True
        # Anything else (snapshot, PDFs, Office formats, media, binary) → raw bytes.
        return retrieved.content

    return wrapped_f


def ss_wrap(func: Callable[..., T]) -> Callable[..., T]:
    """Ensure that a SavedSearch object exists before method execution."""

    def wrapper(self: Any, *args: Any, **kwargs: Any) -> T:
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
