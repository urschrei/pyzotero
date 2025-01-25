"""
zotero_errors.py

Created by Stephan Hügel on 2011-03-04

This file is part of Pyzotero.
"""


# Define some exceptions
class PyZoteroError(Exception):
    """Generic parent exception"""

    pass


class ParamNotPassedError(PyZoteroError):
    """Raised if a parameter which is required isn't passed"""

    pass


class CallDoesNotExistError(PyZoteroError):
    """Raised if the specified API call doesn't exist"""

    pass


class UnsupportedParamsError(PyZoteroError):
    """Raised when unsupported parameters are passed"""

    pass


class UserNotAuthorisedError(PyZoteroError):
    """Raised when the user is not allowed to retrieve the resource"""

    pass


class TooManyItemsError(PyZoteroError):
    """Raised when too many items are passed to a Write API method"""

    pass


class MissingCredentialsError(PyZoteroError):
    """
    Raised when an attempt is made to create a Zotero instance
    without providing both the user ID and the user key
    """

    pass


class InvalidItemFieldsError(PyZoteroError):
    """Raised when an attempt is made to create/update items w/invalid fields"""

    pass


class ResourceNotFoundError(PyZoteroError):
    """Raised when a resource (item, collection etc.) could not be found"""

    pass


class HTTPError(PyZoteroError):
    """Raised for miscellaneous URLLib errors"""

    pass


class CouldNotReachURLError(PyZoteroError):
    """Raised when we can't reach a URL"""

    pass


class ConflictError(PyZoteroError):
    """409 - Raised when the target library is locked"""

    pass


class PreConditionFailedError(PyZoteroError):
    """
    412 - Raised when the provided X-Zotero-Write-Token has already been
    submitted
    """

    pass


class RequestEntityTooLargeError(PyZoteroError):
    """
    413 - The upload would exceed the storage quota of the library owner.
    """

    pass


class PreConditionRequiredError(PyZoteroError):
    """
    428 - Raised when If-Match or If-None-Match was not provided.
    """

    pass


class TooManyRequestsError(PyZoteroError):
    """
    429 - Raised when there are too many unfinished uploads.
    Try again after the number of seconds specified in the Retry-After header.
    """

    pass


class FileDoesNotExistError(PyZoteroError):
    """
    Raised when a file path to be attached can't be opened (or doesn't exist)
    """

    pass


class TooManyRetriesError(PyZoteroError):
    """
    Raise after the backoff period for new requests exceeds 32s
    """

    pass


class UploadError(PyZoteroError):
    """
    Raise if the connection drops during upload or some other non-HTTP error code is returned
    """

    pass
