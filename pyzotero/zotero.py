#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
zotero.py

Created by Stephan Hügel on 2011-02-28
Copyright Stephan Hügel, 2011

This file is part of Pyzotero.

Pyzotero is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Pyzotero is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Pyzotero. If not, see <http://www.gnu.org/licenses/>.
"""

__author__ = 'urschrei@gmail.com'
__version__ = '0.8.3'


import urllib
import urllib2
import socket
import feedparser
import json
import uuid
import time
from urlparse import urlparse
from xml.dom import minidom

import zotero_errors as ze


# Avoid hanging the application if there's no server response
timeout = 30
socket.setdefaulttimeout(timeout)



def ib64_patched(self, attrsD, contentparams):
    """
    Patch isBase64 to prevent Base64 encoding of JSON content
    """
    if attrsD.get('mode', '') == 'base64':
        return 1
    if self.contentparams['type'].startswith('text/'):
        return 0
    if self.contentparams['type'].endswith('+xml'):
        return 0
    if self.contentparams['type'].endswith('/xml'):
        return 0
    if self.contentparams['type'].endswith('/json'):
        return 0
    return 1


# Override feedparser's buggy isBase64 method until they fix it
feedparser._FeedParserMixin._isBase64 = ib64_patched


class Zotero(object):
    """
    Zotero API methods
    A full list of methods can be found here:
    http://www.zotero.org/support/dev/server_api
    """

    def __init__(self, user_id = None, user_key = None):
        """ Store Zotero credentials
        """
        self.endpoint = 'https://api.zotero.org'
        if user_id and user_key:
            self.user_id = user_id
            self.user_key = user_key
        else:
            raise ze.MissingCredentials, \
            'Please provide both the user ID and the user key'
        self.url_params = None
        self.etags = None
        self.temp_keys = ['key', 'etag', 'group_id', 'updated']

    def _etags(self, incoming):
        """
        Return a list of etags parsed out of the XML response
        """
        # Parse Atom as straight XML in order to get the etags FFS
        xmldoc = minidom.parseString(incoming)
        return [c.attributes['zapi:etag'].value for
            c in xmldoc.getElementsByTagName('content')]

    def _retrieve_data(self, request = None):
        """
        Retrieve Zotero items via the API
        Combine endpoint and request to access the specific resource
        Returns an Atom document
        """
        full_url = '%s%s' % (self.endpoint, request)
        req = urllib2.Request(full_url)
        req.add_header('User-Agent', 'Pyzotero/%s' % __version__)
        try:
            response = urllib2.urlopen(req)
            data = response.read()
        except (urllib2.HTTPError, urllib2.URLError), error:
            self._error_handler(req, error)
        # parse the result into Python data structures
        return data

    def retrieve(func):
        """
        Decorator for Zotero methods; calls _retrieve_data() and passes
        the result to the JSON processor
        """
        def wrapped_f(self, *args, **kwargs):
            """
            Returns result of _retrieve_data()

            orig_func's return value is part of a URI, and it's this
            which is intercepted and passed to _retrieve_data:
            '/users/123/items?key=abc123'
            the atom doc returned by _retrieve_data is then
            passed to _etags in order to extract the etag attributes
            from each entry, then to feedparser, then to _process_content
            """
            orig_func = func(self, *args, **kwargs)
            retrieved = self._retrieve_data(orig_func)
            # get etags from the response
            self.etags = self._etags(retrieved)
            # return the parsed Atom doc
            return self._process_content(feedparser.parse(retrieved))
        return wrapped_f

    def add_parameters(self, **params):
        """ Add URL parameters. Will always add the user key
        """
        self.url_params = None
        if params:
            params['key'] = self.user_key
        else:
            params = {'key': self.user_key}
        # always return json, unless different format is specified
        if 'content' not in params:
            params['content'] = 'json'
        params = urllib.urlencode(params)
        self.url_params = params

    def _build_query(self, query_string):
        """
        Set request parameters. Will always add the user ID if it hasn't
        been specifically set by an API method
        """
        try:
            query = urllib.quote(query_string.format(u = self.user_id))
        except KeyError, err:
            raise ze.ParamNotPassed, \
            'There\'s a request parameter missing: %s' % err
        # Add the URL parameters and the user key, if necessary
        if not self.url_params:
            self.add_parameters()
        query = '%s?%s' % (query, self.url_params)
        return query

    # The following methods are Zotero Read API calls
    @retrieve
    def items(self):
        """ Get user items
        """
        query_string = '/users/{u}/items'
        return self._build_query(query_string)

    @retrieve
    def top(self):
        """ Get user top-level items
        """
        query_string = '/users/{u}/items/top'
        return self._build_query(query_string)

    @retrieve
    def item(self, item):
        """ Get a specific item
        """
        query_string = '/users/{u}/items/{i}'.format(
        i = item)
        return self._build_query(query_string)

    @retrieve
    def children(self, item):
        """ Get a specific item's child items
        """
        query_string = '/users/{u}/items/{i}/children'.format(
        i = item)
        return self._build_query(query_string)

    @retrieve
    def tag_items(self, tag):
        """ Get items for a specific tag
        """
        query_string = '/users/{u}/tags/{t}/items'.format(
        t = tag)
        return self._build_query(query_string)

    @retrieve
    def collection_items(self, collection):
        """ Get a specific collection's items
        """
        query_string = '/users/{u}/collections/{c}/items'.format(
        c = collection)
        return self._build_query(query_string)

    @retrieve
    def group_items(self, group):
        """ Get a specific group's items
        """
        query_string = '/groups/{g}/items'.format(
        g = group)
        return self._build_query(query_string)

    @retrieve
    def group_top(self, group):
        """ Get a specific group's top-level items
        """
        query_string = '/groups/{g}/items/top'.format(
        g = group)
        return self._build_query(query_string)

    @retrieve
    def group_item(self, group, item):
        """ Get a specific group item
        """
        query_string = '/groups/{g}/items/{i}'.format(
        g = group,
        i = item)
        return self._build_query(query_string)

    @retrieve
    def group_item_children(self, group, item):
        """ Get a specific group item's child items
        """
        query_string = '/groups/{g}/items/{i}/children'.format(
        g = group,
        i = item)
        return self._build_query(query_string)

    @retrieve
    def group_items_tag(self, group, tag):
        """ Get a specific group's items for a specific tag
        """
        query_string = '/groups/{g}/tags/{t}/items'.format(
        g = group,
        t = tag)
        return self._build_query(query_string)

    @retrieve
    def group_collection_items(self, group, collection):
        """ Get a specific group's items from a specific collection
        """
        query_string = '/groups/{g}/collections/{c}/items'.format(
        g = group,
        c = collection)
        return self._build_query(query_string)

    @retrieve
    def group_collection_top(self, group, collection):
        """ Get a specific group's top-level items from a specific collection
        """
        query_string = '/groups/{g}/collections/{c}/items/top'.format(
        g = group,
        c = collection)
        return self._build_query(query_string)

    @retrieve
    def group_collection_item(self, group, collection, item):
        """ Get a specific collection's item from a specific group
        """
        query_string = '/groups/{g}/collections/{c}/items/{i}'.format(
        g = group,
        c = collection,
        i = item)
        return self._build_query(query_string)

    @retrieve
    def collections(self):
        """ Get user collections
        """
        query_string = '/users/{u}/collections'
        return self._build_query(query_string)

    @retrieve
    def collections_sub(self, collection):
        """ Get subcollections for a specific collection
        """
        query_string = '/users/{u}/collections/{c}/collections'.format(
        u = self.user_id,
        c = collection)
        return self._build_query(query_string)

    @retrieve
    def group_collections(self, group):
        """ Get collections for a specific group
        """
        query_string = '/groups/{group}/collections'.format(
        u = self.user_id,
        g = group)
        return self._build_query(query_string)

    @retrieve
    def group_collection(self, group, collection):
        """ Get a specific collection for a specific group
        """
        query_string = '/groups/{g}/collections/{c}'.format(
        g = group,
        c = collection)
        return self._build_query(query_string)

    @retrieve
    def group_collection_sub(self, group, collection):
        """ Get collections for a specific group
        """
        query_string = '/groups/{g}/collections/{c}/collections'.format(
        g = group,
        c = collection)
        return self._build_query(query_string)

    @retrieve
    def groups(self):
        """ Get user groups
        """
        query_string = '/users/{u}/groups'
        return self._build_query(query_string)

    @retrieve
    def tags(self):
        """ Get tags for a specific item
        """
        query_string = '/users/{u}/tags'
        return self._build_query(query_string)

    @retrieve
    def item_tags(self, item):
        """ Get tags for a specific item
        """
        query_string = '/users/{u}/items/{i}/tags'.format(
        i = item)
        return self._build_query(query_string)

    @retrieve
    def group_tags(self, group):
        """ Get tags for a specific group
        """
        query_string = '/groups/{g}/tags'.format(
        g = group)
        return self._build_query(query_string)

    @retrieve
    def group_item_tags(self, group, item):
        """ Get tags for a specific item in a specific group
        """
        query_string = '/groups/{g}/items/{i}/tags'.format(
        g = group,
        i = item)
        return self._build_query(query_string)

    def check_updated(self, payload):
        """
        Check if an item's been updated
        Accepts a dict containing item data
        Returns True or False
        """
        opener = urllib2.build_opener(NotModifiedHandler())
        query = self.endpoint + self._build_query(
            '/users/{u}/items/{i}'.format(
                u = self.user_id,
                i = payload['key']))
        req = urllib2.Request(query)
        req.add_header('If-Modified-Since', payload['updated'])
        try:
            url_handle = opener.open(req)
            _ = url_handle.info()
        except (urllib2.HTTPError, urllib2.URLError), error:
            self._error_handler(req, error)
        if hasattr(url_handle, 'code') and url_handle.code == 304:
            return False
        else:
            return True

    def all_top(self):
        """ Retrieve all top-level items
        """
        # get a single top-level item
        query = self._build_query('/users/{u}/items/top')
        self.add_parameters(limit=1)
        data = self._retrieve_data(query)
        self.url_params = None
        parsed = feedparser.parse(data)
        # extract the 'total results' figure
        total = int(parsed['feed']['zapi_totalresults'].encode('utf8'))
        all_results = []
        # Retrieve all top-level items, 99 at a time
        for i in xrange(1, total + 1, 99):
            self.add_parameters(start = i, limit = 99)
            all_results.extend(self.top())
        return all_results

    def get_subset(self, subset):
        """
        Retrieve a subset of items
        Accepts a single argument: a list of item IDs
        """
        if len(subset) > 50:
            raise ze.TooManyItems, \
                    "You may only retrieve 50 items per call"
        retr = []
        for itm in subset:
            retr.extend(self.item(itm))
        return retr

    # The following methods process data returned by Read API calls
    def _process_content(self, retrieved):
        """ Call either _standard_items or _bib_items, based on the URL param
        """
        # Content request in 'bib' format, so call _bib_items
        if self.url_params.find('=bib') != -1:
            return self._bib_items(retrieved)
        else:
            return self._standard_items(retrieved)

    def _standard_items(self, retrieved):
        """ Format and return data from API calls which return Items
        """
        # send entries to _tags_data if there's no JSON
        try:
            items = [json.loads(e['content'][0]['value'])
                for e in retrieved.entries]
        except ValueError:
            return self._tags_data(retrieved)

        # try to add various namespaced values to the items
        zapi_keys = ['key']
        for zapi in zapi_keys:
            try:
                for key, _ in enumerate(items):
                    items[key][unicode(zapi)] = \
                            retrieved.entries[key][unicode('zapi_%s' % zapi)]
            except KeyError:
                pass
        # try to add the updated time in the same format the server expects it
        for key, _ in enumerate(items):
            try:
                items[key][u'updated'] = \
                        time.strftime(
                                "%a, %d %b %Y %H:%M:%S %Z",
                                retrieved.entries[key]['updated_parsed'])
            except KeyError:
                pass
        # add the etags
        for k, _ in enumerate(items):
            items[k][u'etag'] = self.etags[k]

        # Try to get a group ID, and add it to the dict
        try:
            group_id = [urlparse(g['links'][0]['href']).path.split('/')[2]
                    for g in retrieved.entries]
            for k, val in enumerate(items):
                val[u'group_id'] = group_id[k]
        except KeyError:
            pass
        self.url_params = None
        return items

    def _bib_items(self, retrieved):
        """ Return a list of strings formatted as HTML bibliography entries
        """
        items = []
        for bib in retrieved.entries:
            items.append(bib['content'][0]['value'])
        self.url_params = None
        return items

    def _tags_data(self, retrieved):
        """ Format and return data from API calls which return Tags
        """
        tags = [t['title'] for t in retrieved.entries]
        self.url_params = None
        return tags

    # The following methods are Write API calls
    def item_template(self, itemtype):
        """ Get a template for a new item
        """
        query_string = '/items/new?itemType={i}'.format(
        i = itemtype)
        retrieved = self._retrieve_data(query_string)
        return json.loads(retrieved)

    def item_types(self):
        """ Get all available item types
        """
        query_string = '/itemTypes'
        retrieved = self._retrieve_data(query_string)
        return json.loads(retrieved)

    def item_fields(self):
        """ Get all available item fields
        """
        query_string = '/itemFields'
        retrieved = self._retrieve_data(query_string)
        return json.loads(retrieved)

    def item_creator_types(self, itemtype):
        """ Get all available creator types for an item
        """
        query_string = '/itemTypeCreatorTypes?itemType={i}'.format(
        i = itemtype)
        retrieved = self._retrieve_data(query_string)
        return json.loads(retrieved)

    def create_items(self, payload):
        """
        Create new Zotero items
        Accepts one argument, a list containing one or more item dicts
        """
        if len(payload) > 50:
            raise ze.TooManyItems, \
                    "You may only create up to 50 items per call"
        # we don't want to overwrite our items, so make a copy
        to_create = list(payload)
        # remove keys we may have added
        for tempkey in self.temp_keys:
            _ = [tc.pop(tempkey) for tc in to_create if tempkey in tc]
        to_send = json.dumps({'items': to_create})
        token = str(uuid.uuid4()).replace('-','')
        req = urllib2.Request(
        self.endpoint + '/users/{u}/items'.format(u = self.user_id) +
            '?' + urllib.urlencode({'key': self.user_key}))
        req.add_data(to_send)
        req.add_header('X-Zotero-Write-Token', token)
        req.add_header('Content-Type', 'application/json' )
        req.add_header('User-Agent', 'Pyzotero/%s' % __version__)
        try:
            resp = urllib2.urlopen(req)
            data = resp.read()
            self.etags = self._etags(data)
        except (urllib2.HTTPError, urllib2.URLError), error:
            self._error_handler(req, error)
        return self._standard_items(feedparser.parse(data))

    def create_collection(self, payload):
        """
        Create a new Zotero collection
        Accepts one argument, a dict containing the following keys:

        'name': the name of the collection
        'parent': OPTIONAL, the parent collection to which you wish to add this
        """
        # no point in proceeding if there's no 'name' key
        if 'name' not in payload:
            raise ze.ParamNotPassed, \
                    "The dict you pass must include a 'name' key"
        # add a blank 'parent' key if it hasn't been passed
        if not 'parent' in payload:
            payload['parent'] = ''
        to_send = json.dumps(payload)
        token = str(uuid.uuid4()).replace('-','')
        req = urllib2.Request(
        self.endpoint + '/users/{u}/collections'.format(u = self.user_id) +
            '?' + urllib.urlencode({'key': self.user_key}))
        req.add_data(to_send)
        req.add_header('X-Zotero-Write-Token', token)
        req.add_header('User-Agent', 'Pyzotero/%s' % __version__)
        try:
            urllib2.urlopen(req)
        except (urllib2.HTTPError, urllib2.URLError), error:
            self._error_handler(req, error)
        return True

    def update_collection(self, payload):
        """
        Update a Zotero collection
        Accepts one argument, a dict containing collection data retrieved
        using e.g. 'collections()'

        """
        # we don't want to overwrite the dict we passed in, so make a copy
        to_update = dict(payload)
        token = to_update['etag']
        key = to_update['key']
        # remove any keys we've added
        for tempkey in self.temp_keys:
            to_update.pop(tempkey, None)
        to_send = json.dumps(to_update)
        # Override urllib2 to give it a PUT verb
        opener = urllib2.build_opener(urllib2.HTTPHandler)
        req = urllib2.Request(
        self.endpoint + '/users/{u}/collections/{c}'.format(
            u = self.user_id, c = key) +
            '?' + urllib.urlencode({'key': self.user_key}))
        req.add_data(to_send)
        req.get_method = lambda: 'PUT'
        req.add_header('If-Match', token)
        req.add_header('User-Agent', 'Pyzotero/%s' % __version__)
        try:
            opener.open(req)
        except (urllib2.HTTPError, urllib2.URLError), error:
            self._error_handler(req, error)
        return True

    def update_item(self, payload):
        """
        Update an existing item
        Accepts one argument, a dict containing Item data
        """
        # we don't want to modify the dict we passed in, so create a copy
        to_update = dict(payload)
        etag = to_update['etag']
        ident = to_update['key']
        # remove any keys we've added
        for tempkey in self.temp_keys:
            to_update.pop(tempkey, None)
        to_send = json.dumps(to_update)
        # Override urllib2 to give it a PUT verb
        opener = urllib2.build_opener(urllib2.HTTPHandler)
        req = urllib2.Request(self.endpoint + '/users/{u}/items/'.format(
            u = self.user_id) + ident +
            '?' + urllib.urlencode({'key': self.user_key}))
        req.get_method = lambda: 'PUT'
        req.add_data(to_send)
        req.add_header('If-Match', etag)
        req.add_header('User-Agent', 'Pyzotero/%s' % __version__)
        try:
            resp = opener.open(req)
            data = resp.read()
            self.etags = self._etags(data)
        except (urllib2.HTTPError, urllib2.URLError), error:
            self._error_handler(req, error)
        return self._standard_items(feedparser.parse(data))

    def addto_collection(self, collection, payload):
        """
        Add one or more items to a collection
        Accepts two arguments:
        The collection ID, and a list containing one or more item dicts
        """
        # create a string containing item IDs
        to_send = ' '.join([p['key'].encode('utf8') for p in payload])

        req = urllib2.Request(
        self.endpoint + '/users/{u}/collections/{c}/items'.format(
            u = self.user_id, c = collection) +
            '?' + urllib.urlencode({'key': self.user_key}))
        req.add_data(to_send)
        req.add_header('User-Agent', 'Pyzotero/%s' % __version__)
        try:
            urllib2.urlopen(req)
        except (urllib2.HTTPError, urllib2.URLError), error:
            self._error_handler(req, error)
        return True

    def deletefrom_collection(self, collection, payload):
        """
        Delete an item from a collection
        Accepts two arguments:
        The collection ID, and a dict containing one or more item dicts
        """
        ident = payload['key']
        # Override urllib2 to give it a DELETE verb
        opener = urllib2.build_opener(urllib2.HTTPHandler)
        req = urllib2.Request(
        self.endpoint + '/users/{u}/collections/{c}/items/'.format(
            u = self.user_id, c = collection) + ident +
            '?' + urllib.urlencode({'key': self.user_key}))
        req.get_method = lambda: 'DELETE'
        req.add_header('User-Agent', 'Pyzotero/%s' % __version__)
        try:
            opener.open(req)
        except (urllib2.HTTPError, urllib2.URLError), error:
            self._error_handler(req, error)
        return True

    def delete_item(self, payload):
        """
        Delete an Item from a Zotero library
        Accepts a single argument: a dict containing item data
        """
        etag = payload['etag']
        ident = payload['key']
        # Override urllib2 to give it a DELETE verb
        opener = urllib2.build_opener(urllib2.HTTPHandler)
        req = urllib2.Request(self.endpoint + '/users/{u}/items/'.format(
            u = self.user_id) + ident +
            '?' + urllib.urlencode({'key': self.user_key}))
        req.get_method = lambda: 'DELETE'
        req.add_header('If-Match', etag)
        req.add_header('User-Agent', 'Pyzotero/%s' % __version__)
        try:
            opener.open(req)
        except (urllib2.HTTPError, urllib2.URLError), error:
            self._error_handler(req, error)
        return True

    def delete_collection(self, payload):
        """
        Delete a Collection from a Zotero library
        Accepts a single argument: a dict containing item data
        """
        etag = payload['etag']
        ident = payload['key']
        # Override urllib2 to give it a DELETE verb
        opener = urllib2.build_opener(urllib2.HTTPHandler)
        req = urllib2.Request(self.endpoint + '/users/{u}/collections/{c}'
            .format(u = self.user_id, c = ident) +
            '?' + urllib.urlencode({'key': self.user_key}))
        req.get_method = lambda: 'DELETE'
        req.add_header('If-Match', etag)
        req.add_header('User-Agent', 'Pyzotero/%s' % __version__)
        try:
            opener.open(req)
        except (urllib2.HTTPError, urllib2.URLError), error:
            self._error_handler(req, error)
        return True

    def _error_handler(self, req, error):
        """
        Error handler for HTTP requests
        """
        # Distinguish between URL errors and HTTP status codes of 400+
        if hasattr(error, 'reason'):
            raise ze.CouldNotReachURL, \
"Could not reach server. Reason: %s\nURL: %s" % (error, req.get_full_url())
        elif hasattr(error, 'code'):
            if error.code == 401 or error.code == 403:
                raise ze.UserNotAuthorised, \
"Not authorised: (%s)\nURL: %s\nType: %s\nData: %s" % (
        error.code, req.get_full_url(), req.get_method(), req.get_data())
            elif error.code == 400:
                raise ze.UnsupportedParams, \
"Invalid request, probably due to unsupported parameters: %s\n%s\n%s" % \
                (req.get_full_url(), req.get_method(), req.get_data())
            elif error.code == 404:
                raise ze.ResourceNotFound, \
"No results for the following query:\n%s" % req.get_full_url()
            elif error.code == 409:
                raise ze.Conflict, \
"The target library is locked"
            elif error.code == 412:
                raise ze.PreConditionFailed, \
"The item was already submitted, or has changed since you retrieved it"
            else:
                raise ze.HTTPError, \
"HTTP Error %s (%s)\nURL: %s\nData: %s" % (
                error.msg, error.code, req.get_full_url(), req.get_data())



class NotModifiedHandler(urllib2.BaseHandler):
    """
    304 Not Modified handler for urllib2
    use like so:
    - opener = urllib2.build_opener(NotModifiedHandler())
    - add the If-Modified-Since header to the request
    - req.get_method = lambda: 'PUT'/'DELETE'
    - url_handle = opener.open(req)
    - headers = url_handle.info()
    - if hasattr(url_handle, 'code') and url_handle.code == 304:
    -   return False
    http://goo.gl/2fhI3
    """
    def __init__(self):
        pass
    def http_error_304(self, req, f_p, code, message, headers):
        """ The actual handler """
        addinfourl = urllib2.addinfourl(f_p, headers, req.get_full_url())
        addinfourl.code = code
        return addinfourl

