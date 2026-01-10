"""Exception classes and error handling for Pyzotero.

This module defines all custom exceptions used by the library
and the error_handler function for processing HTTP errors.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from ._utils import get_backoff_duration

if TYPE_CHECKING:
    from typing import Any


class PyZoteroError(Exception):
    """Generic parent exception for all Pyzotero errors."""


class ParamNotPassedError(PyZoteroError):
    """Raised if a parameter which is required isn't passed."""


class CallDoesNotExistError(PyZoteroError):
    """Raised if the specified API call doesn't exist."""


class UnsupportedParamsError(PyZoteroError):
    """Raised when unsupported parameters are passed."""


class UserNotAuthorisedError(PyZoteroError):
    """Raised when the user is not allowed to retrieve the resource."""


class TooManyItemsError(PyZoteroError):
    """Raised when too many items are passed to a Write API method."""


class MissingCredentialsError(PyZoteroError):
    """Raised when an attempt is made to create a Zotero instance
    without providing both the user ID and the user key.
    """


class InvalidItemFieldsError(PyZoteroError):
    """Raised when an attempt is made to create/update items w/invalid fields."""


class ResourceNotFoundError(PyZoteroError):
    """Raised when a resource (item, collection etc.) could not be found."""


class HTTPError(PyZoteroError):
    """Raised for miscellaneous HTTP errors."""


class CouldNotReachURLError(PyZoteroError):
    """Raised when we can't reach a URL."""


class ConflictError(PyZoteroError):
    """409 - Raised when the target library is locked."""


class PreConditionFailedError(PyZoteroError):
    """412 - Raised when the provided X-Zotero-Write-Token has already been
    submitted.
    """


class RequestEntityTooLargeError(PyZoteroError):
    """413 - The upload would exceed the storage quota of the library owner."""


class PreConditionRequiredError(PyZoteroError):
    """428 - Raised when If-Match or If-None-Match was not provided."""


class TooManyRequestsError(PyZoteroError):
    """429 - Raised when there are too many unfinished uploads.
    Try again after the number of seconds specified in the Retry-After header.
    """


class FileDoesNotExistError(PyZoteroError):
    """Raised when a file path to be attached can't be opened (or doesn't exist)."""


class TooManyRetriesError(PyZoteroError):
    """Raise after the backoff period for new requests exceeds 32s."""


class UploadError(PyZoteroError):
    """Raise if the connection drops during upload or some other non-HTTP error
    code is returned.
    """


# Mapping of HTTP status codes to exception classes
ERROR_CODES: dict[int, type[PyZoteroError]] = {
    400: UnsupportedParamsError,
    401: UserNotAuthorisedError,
    403: UserNotAuthorisedError,
    404: ResourceNotFoundError,
    409: ConflictError,
    412: PreConditionFailedError,
    413: RequestEntityTooLargeError,
    428: PreConditionRequiredError,
    429: TooManyRequestsError,
}


def error_handler(
    zot: Any, req: httpx.Response, exc: BaseException | None = None
) -> None:
    """Error handler for HTTP requests.

    Raises appropriate exceptions based on HTTP status codes and handles
    rate limiting with backoff.

    Args:
        zot: A Zotero instance (or any object with _set_backoff method)
        req: The HTTP response object
        exc: Optional exception that triggered this handler

    """

    def err_msg(req: httpx.Response) -> str:
        """Return a nicely-formatted error message."""
        return (
            f"\nCode: {req.status_code}\n"
            f"URL: {req.url!s}\n"
            f"Method: {req.request.method}\n"
            f"Response: {req.text}"
        )

    if ERROR_CODES.get(req.status_code):
        # check to see whether its 429
        if req.status_code == httpx.codes.TOO_MANY_REQUESTS:
            # try to get backoff or delay duration
            delay = get_backoff_duration(req.headers)
            if not delay:
                msg = (
                    "You are being rate-limited and no backoff or retry duration "
                    "has been received from the server. Try again later"
                )
                raise TooManyRetriesError(msg)
            zot._set_backoff(delay)
        elif not exc:
            raise ERROR_CODES[req.status_code](err_msg(req))
        else:
            raise ERROR_CODES[req.status_code](err_msg(req)) from exc
    elif not exc:
        raise HTTPError(err_msg(req))
    else:
        raise HTTPError(err_msg(req)) from exc


__all__ = [
    "ERROR_CODES",
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
    "error_handler",
]
