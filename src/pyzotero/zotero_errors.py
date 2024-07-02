"""
zotero_errors.py

Created by Stephan Hügel on 2011-03-04

This file is part of Pyzotero.
"""


# Define some exceptions
class PyZoteroError(Exception):
    """Generic parent exception"""

    pass


class ParamNotPassed(PyZoteroError):
    """Raised if a parameter which is required isn't passed"""

    pass


class CallDoesNotExist(PyZoteroError):
    """Raised if the specified API call doesn't exist"""

    pass


class UnsupportedParams(PyZoteroError):
    """Raised when unsupported parameters are passed"""

    pass


class UserNotAuthorised(PyZoteroError):
    """Raised when the user is not allowed to retrieve the resource"""

    pass


class TooManyItems(PyZoteroError):
    """Raised when too many items are passed to a Write API method"""

    pass


class MissingCredentials(PyZoteroError):
    """
    Raised when an attempt is made to create a Zotero instance
    without providing both the user ID and the user key
    """

    pass


class InvalidItemFields(PyZoteroError):
    """Raised when an attempt is made to create/update items w/invalid fields"""

    pass


class ResourceNotFound(PyZoteroError):
    """Raised when a resource (item, collection etc.) could not be found"""

    pass


class HTTPError(PyZoteroError):
    """Raised for miscellaneous URLLib errors"""

    pass


class CouldNotReachURL(PyZoteroError):
    """Raised when we can't reach a URL"""

    pass


class Conflict(PyZoteroError):
    """409 - Raised when the target library is locked"""

    pass


class PreConditionFailed(PyZoteroError):
    """
    412 - Raised when the provided X-Zotero-Write-Token has already been
    submitted
    """

    pass


class RequestEntityTooLarge(PyZoteroError):
    """
    413 – The upload would exceed the storage quota of the library owner.
    """

    pass


class PreConditionRequired(PyZoteroError):
    """
    428 - Raised when If-Match or If-None-Match was not provided.
    """

    pass


class TooManyRequests(PyZoteroError):
    """
    429 - Raised when there are too many unfinished uploads.
    Try again after the number of seconds specified in the Retry-After header.
    """

    pass


class FileDoesNotExist(PyZoteroError):
    """
    Raised when a file path to be attached can't be opened (or doesn't exist)
    """

    pass


class TooManyRetries(PyZoteroError):
    """
    Raise after the backoff period for new requests exceeds 32s
    """

    pass


class UploadError(PyZoteroError):
    """
    Raise if the connection drops during upload or some other non-HTTP error code is returned
    """

    pass
