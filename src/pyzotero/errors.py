"""Exception classes and error handling for Pyzotero.

This module defines all custom exceptions used by the library
and the error_handler function for processing HTTP errors.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx2

from ._utils import get_backoff_duration

if TYPE_CHECKING:
    from ._types import ZoteroClientProtocol


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


class LocalAPIKeyRequiredError(UserNotAuthorisedError):
    """401 - Raised when a local API write has no valid local API key.

    Local API keys have no relation to zotero.org API keys. A key that the
    user grants with "Allow", not "Always Allow", is valid for one write only:
    the first successful write uses it. Call ``Zotero.authorize_local()`` to
    get a new key.
    """


class LocalAPIDeniedError(UserNotAuthorisedError):
    """403 - Raised when the user denies a local API authorisation request."""


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


class ServerIDMismatchError(PreConditionFailedError):
    """412 - Raised when Zotero-Server-ID does not match the local server.

    The request went to a different Zotero instance, or to the same instance
    with a restored or replaced database. Object data and versions from the
    local API apply only to one server ID. Do not use them with a different
    server ID.
    """


class ServerIDRequiredError(PreConditionRequiredError):
    """428 - Raised when a local API write had no Zotero-Server-ID header.

    Pyzotero gets and sends the header automatically. Thus this error shows
    that a request did not go through ``Zotero._write``.
    """


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


# The local API uses the status codes 401, 412 and 428 for more than one
# condition each. To identify the condition, examine the plain-text response
# body. Each entry is a sequence of (body fragment, exception class) pairs.
# The fragments are compared with the response text in the given order.
_LOCAL_API_ERRORS: dict[int, tuple[tuple[str, type[PyZoteroError]], ...]] = {
    401: (
        ("API key required", LocalAPIKeyRequiredError),
        ("Invalid or expired API key", LocalAPIKeyRequiredError),
    ),
    412: (("Zotero-Server-ID does not match", ServerIDMismatchError),),
    428: (("Zotero-Server-ID not provided", ServerIDRequiredError),),
}

# The message for these errors gets a hint, because the server's own response
# text does not show the corrective action.
_ERROR_HINTS: dict[type[PyZoteroError], str] = {
    LocalAPIKeyRequiredError: (
        "Hint: call Zotero.authorize_local() to obtain a local API key. A key "
        "granted with 'Allow' rather than 'Always Allow' is single-use, and is "
        "consumed by the first successful write."
    ),
    ServerIDMismatchError: (
        "Hint: the server_id in use belongs to a different Zotero instance or "
        "database. Local API data and versions must be partitioned by server "
        "ID; discard anything cached against the old one before replacing it."
    ),
}


def _error_class(req: httpx2.Response) -> type[PyZoteroError]:
    """Return the most specific exception class for a response.

    If the body does not identify one of the local API's special conditions,
    fall back to a lookup by status code.
    """
    for fragment, error_cls in _LOCAL_API_ERRORS.get(req.status_code, ()):
        if fragment in req.text:
            return error_cls
    return ERROR_CODES.get(req.status_code, HTTPError)


def _err_msg(req: httpx2.Response, hint: str = "") -> str:
    """Return a nicely-formatted error message for an HTTP response."""
    return (
        f"\nCode: {req.status_code}\n"
        f"URL: {req.url!s}\n"
        f"Method: {req.request.method}\n"
        f"Response: {req.text}" + (f"\n{hint}" if hint else "")
    )


def error_handler(
    zot: ZoteroClientProtocol, req: httpx2.Response, exc: BaseException | None = None
) -> None:
    """Error handler for HTTP requests.

    Raises an appropriate PyZoteroError subclass for the response status code.

    HTTP 429 responses are a special case: instead of raising, the
    server-supplied backoff duration is recorded on ``zot`` via
    ``_set_backoff`` and the function returns normally, leaving the caller
    to retry. If no backoff duration is present, TooManyRetriesError is raised.

    Args:
        zot: A Zotero instance (or any object with _set_backoff method).
        req: The HTTP response object.
        exc: Optional exception that triggered this handler.

    """
    if req.status_code == httpx2.codes.TOO_MANY_REQUESTS:
        delay = get_backoff_duration(req.headers)
        if not delay:
            msg = (
                "You are being rate-limited and no backoff or retry duration "
                "has been received from the server. Try again later"
            )
            raise TooManyRetriesError(msg)
        zot._set_backoff(delay)
        return

    error_cls = _error_class(req)
    msg = _err_msg(req, _ERROR_HINTS.get(error_cls, ""))
    if exc is None:
        raise error_cls(msg)
    raise error_cls(msg) from exc


__all__ = [
    "ERROR_CODES",
    "CallDoesNotExistError",
    "ConflictError",
    "CouldNotReachURLError",
    "FileDoesNotExistError",
    "HTTPError",
    "InvalidItemFieldsError",
    "LocalAPIDeniedError",
    "LocalAPIKeyRequiredError",
    "MissingCredentialsError",
    "ParamNotPassedError",
    "PreConditionFailedError",
    "PreConditionRequiredError",
    "PyZoteroError",
    "RequestEntityTooLargeError",
    "ResourceNotFoundError",
    "ServerIDMismatchError",
    "ServerIDRequiredError",
    "TooManyItemsError",
    "TooManyRequestsError",
    "TooManyRetriesError",
    "UnsupportedParamsError",
    "UploadError",
    "UserNotAuthorisedError",
    "error_handler",
]
