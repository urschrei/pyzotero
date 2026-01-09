"""Backwards-compatible re-exports for pyzotero.zotero module.

This module maintains backwards compatibility for code that imports from
pyzotero.zotero. New code should import directly from pyzotero.

Example:
    # Old style (still works)
    from pyzotero.zotero import Zotero

    # New style (preferred)
    from pyzotero import Zotero

"""

# Re-export everything for backwards compatibility
# Also import the errors module for backwards compat
from pyzotero import zotero_errors as ze
from pyzotero._client import Zotero
from pyzotero._decorators import backoff_check, cleanwrap, retrieve, ss_wrap, tcache
from pyzotero._search import SavedSearch
from pyzotero._upload import Zupload
from pyzotero._utils import (
    DEFAULT_ITEM_LIMIT,
    DEFAULT_NUM_ITEMS,
    DEFAULT_TIMEOUT,
    ONE_HOUR,
    build_url,
    chunks,
    merge_params,
    token,
)
from pyzotero.errors import error_handler

# Preserve original module-level attributes
__author__ = "Stephan Hügel"
__api_version__ = "3"

# Backwards compatibility: the old 'timeout' variable name
timeout = DEFAULT_TIMEOUT

__all__ = [
    # Constants
    "DEFAULT_ITEM_LIMIT",
    "DEFAULT_NUM_ITEMS",
    "DEFAULT_TIMEOUT",
    "ONE_HOUR",
    "SavedSearch",
    # Classes
    "Zotero",
    "Zupload",
    # Module attributes
    "__api_version__",
    "__author__",
    # Decorators
    "backoff_check",
    # Utility functions
    "build_url",
    "chunks",
    "cleanwrap",
    "error_handler",
    "merge_params",
    "retrieve",
    "ss_wrap",
    "tcache",
    "timeout",
    "token",
    # Backwards compat
    "ze",
]
