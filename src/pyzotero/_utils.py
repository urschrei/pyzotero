"""Utility functions for Pyzotero.

This module contains helper functions used throughout the library.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import PurePosixPath
from typing import TypeVar
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

# Avoid hanging the application if there's no server response
DEFAULT_TIMEOUT = 30

ONE_HOUR = 3600
DEFAULT_NUM_ITEMS = 50
DEFAULT_ITEM_LIMIT = 100

T = TypeVar("T")


def build_url(base_url: str, path: str, args_dict: dict | None = None) -> str:
    """Build a valid URL from base, path, and optional query parameters.

    This avoids string concatenation errors and leading/trailing slash issues.
    """
    base_url = base_url.removesuffix("/")
    parsed = urlparse(base_url)
    new_path = str(PurePosixPath(parsed.path) / path.removeprefix("/"))
    if args_dict:
        return urlunparse(parsed._replace(path=new_path, query=urlencode(args_dict)))
    return urlunparse(parsed._replace(path=new_path))


def merge_params(url: str, params: dict) -> tuple[str, dict]:
    """Strip query parameters from URL and merge with provided params.

    Returns a tuple of (base_url, merged_params).
    """
    parsed = urlparse(url)
    # Extract query parameters from URL
    incoming = parse_qs(parsed.query)
    incoming = {k: v[0] for k, v in incoming.items()}

    # Create new params dict by merging
    merged = {**incoming, **params}

    # Get base URL by zeroing out the query component
    base_url = urlunparse(parsed._replace(query=""))

    return base_url, merged


def token() -> str:
    """Return a unique 32-char write-token."""
    return str(uuid.uuid4().hex)


def chunks(iterable: list[T], n: int) -> Iterator[list[T]]:
    """Yield successive n-sized chunks from an iterable."""
    for i in range(0, len(iterable), n):
        yield iterable[i : i + n]


def get_backoff_duration(headers) -> str | None:
    """Extract backoff duration from response headers.

    The Zotero API may return backoff instructions via either the
    'Backoff' or 'Retry-After' header.
    """
    return headers.get("backoff") or headers.get("retry-after")


__all__ = [
    "DEFAULT_ITEM_LIMIT",
    "DEFAULT_NUM_ITEMS",
    "DEFAULT_TIMEOUT",
    "ONE_HOUR",
    "build_url",
    "chunks",
    "get_backoff_duration",
    "merge_params",
    "token",
]
