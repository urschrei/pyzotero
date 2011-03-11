#!/usr/bin/env python
# encoding: utf-8
"""
zotero_errors.py

Created by Stephan Hügel on 2011-03-04
Copyright Stephan Hügel, 2011

License: http://www.gnu.org/licenses/gpl-3.0.txt
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



class RateLimitExceeded(PyZoteroError):
    """ Raised when the API rate limit is exceeded
    """
    pass



class UserNotAuthorised(PyZoteroError):
    """ Raised when the user is not allowed to retrieve the resource
    """
    pass



class MissingCredentials(PyZoteroError):
    """ Raised when an attempt is made to create a Zotero instance
        without providing both the user ID and the user key
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
