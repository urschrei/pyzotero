"""Pyzotero - Python wrapper for the Zotero API.

Maintainer note: this module defines the public API surface. When adding
a new public symbol, add it to both the imports below and to ``__all__``,
and update ``doc/index.rst`` if it is user-facing.
"""

import importlib.metadata

try:
    # __package__ allows for the case where __name__ is "__main__"
    __version__ = importlib.metadata.version(__package__ or __name__)
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"

# Public API exports
from pyzotero._client import Zotero
from pyzotero._search import SavedSearch
from pyzotero._upload import Zupload
from pyzotero._utils import chunks
from pyzotero.errors import (
    CallDoesNotExistError,
    ConflictError,
    CouldNotReachURLError,
    FileDoesNotExistError,
    HTTPError,
    InvalidItemFieldsError,
    MissingCredentialsError,
    ParamNotPassedError,
    PreConditionFailedError,
    PreConditionRequiredError,
    PyZoteroError,
    RequestEntityTooLargeError,
    ResourceNotFoundError,
    TooManyItemsError,
    TooManyRequestsError,
    TooManyRetriesError,
    UnsupportedParamsError,
    UploadError,
    UserNotAuthorisedError,
)

__all__ = [
    # Exceptions
    "CallDoesNotExistError",
    "ConflictError",
    "CouldNotReachURLError",
    "FileDoesNotExistError",
    "HTTPError",
    "InvalidItemFieldsError",
    "MissingCredentialsError",
    "ParamNotPassedError",
    "PreConditionFailedError",
    "PreConditionRequiredError",
    "PyZoteroError",
    "RequestEntityTooLargeError",
    "ResourceNotFoundError",
    "SavedSearch",
    "TooManyItemsError",
    "TooManyRequestsError",
    "TooManyRetriesError",
    "UnsupportedParamsError",
    "UploadError",
    "UserNotAuthorisedError",
    # Main classes
    "Zotero",
    "Zupload",
    # Version
    "__version__",
    # Utilities
    "chunks",
]
