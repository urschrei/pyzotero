"""Backwards-compatible re-exports for pyzotero.zotero_errors module.

This module maintains backwards compatibility for code that imports from
pyzotero.zotero_errors. New code should import from pyzotero.errors.

Example:
    # Old style (still works)
    from pyzotero import zotero_errors as ze

    # New style (preferred)
    from pyzotero import errors as ze

"""

# Re-export all exceptions for backwards compatibility
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
    "TooManyItemsError",
    "TooManyRequestsError",
    "TooManyRetriesError",
    "UnsupportedParamsError",
    "UploadError",
    "UserNotAuthorisedError",
]
