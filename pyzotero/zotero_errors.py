#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
zotero_errors.py

Created by Stephan Hügel on 2011-03-04

This file is part of Pyzotero.

The MIT License (MIT)

Copyright (c) 2015 Stephan Hügel

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""


# Define some exceptions
class PyZoteroError(Exception):
    """ Generic parent exception
    """
    pass


class ParamNotPassed(PyZoteroError):
    """ Raised if a parameter which is required isn't passed
    """
    pass


class CallDoesNotExist(PyZoteroError):
    """ Raised if the specified API call doesn't exist
    """
    pass


class UnsupportedParams(PyZoteroError):
    """ Raised when unsupported parameters are passed
    """
    pass


class UserNotAuthorised(PyZoteroError):
    """ Raised when the user is not allowed to retrieve the resource
    """
    pass


class TooManyItems(PyZoteroError):
    """ Raised when too many items are passed to a Write API method
    """
    pass


class MissingCredentials(PyZoteroError):
    """
    Raised when an attempt is made to create a Zotero instance
    without providing both the user ID and the user key
    """
    pass


class InvalidItemFields(PyZoteroError):
    """ Raised when an attempt is made to create/update items w/invalid fields
    """
    pass


class ResourceNotFound(PyZoteroError):
    """ Raised when a resource (item, collection etc.) could not be found
    """
    pass


class HTTPError(PyZoteroError):
    """ Raised for miscellaneous URLLib errors
    """
    pass


class CouldNotReachURL(PyZoteroError):
    """ Raised when we can't reach a URL
    """
    pass


class Conflict(PyZoteroError):
    """ 409 - Raised when the target library is locked
    """
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
    429 - Raised when Too many unfinished uploads.
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
