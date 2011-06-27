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
__version__ = '0.6.9'


import urllib
import urllib2
import socket
import feedparser
import json
import uuid
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
    """ Zotero API methods
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

    def _etags(self, incoming):
        """
        Return a list of etags parsed out of the XML response
        """
        # Parse Atom as straight XML in order to get the etags FFS
        xmldoc = minidom.parseString(incoming)
        return [c.attributes['zapi:etag'].value for
            c in xmldoc.getElementsByTagName('content')]

    def retrieve_data(self, request = None):
        """ Retrieve Zotero items via the API
            Combine endpoint and request to access the specific resource
            Returns a dict containing feed items and lists of entries
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
        """ Decorator for Zotero methods; calls retrieve_data() and passes
            the result to the JSON processor
        """
        def wrapped_f(self, *args, **kwargs):
            """ Returns result of retrieve_data()

                orig_func's return value is part of a URI, and it's this
                which is intercepted and passed to retrieve_data:
                '/users/123/items?key=abc123'
                the feed-parsed atom doc returned by retrieve_data is then
                passed to process_content
            """
            orig_func = func(self, *args, **kwargs)
            retrieved = self.retrieve_data(orig_func)
            # get etags from the response
            self.etags = self._etags(retrieved)
            # return the parsed Atom doc
            return self.process_content(feedparser.parse(retrieved))
        return wrapped_f

    def add_parameters(self, **params):
        """ Set URL parameters. Will always add the user key
        """
        self.url_params = None
        if params:
            params['key'] = self.user_key
        else:
            params = {'key': self.user_key}
        # always return json
        if not params.get('content', None) == 'bib' or None:
            params['content'] = 'json'
        params = urllib.urlencode(params)
        self.url_params = params

    def _build_query(self, query_string):
        """ Set request parameters. Will always add the user ID if it hasn't
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

    # The following methods are all Zotero Read API calls
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
        u = self.user_id, i = item)
        return self._build_query(query_string)

    @retrieve
    def children(self, item):
        """ Get a specific item's child items
        """
        query_string = '/users/{u}/items/{i}/children'.format(
        u = self.user_id,
        i = item)
        return self._build_query(query_string)

    @retrieve
    def tag_items(self, tag):
        """ Get items for a specific tag
        """
        query_string = '/users/{u}/tags/{t}/items'.format(
        u = self.user_id,
        t = tag)
        return self._build_query(query_string)

    @retrieve
    def collection_items(self, collection):
        """ Get a specific collection's items
        """
        query_string = '/users/{u}/collections/{c}/items'.format(
        u = self.user_id,
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
        u = self.user_id,
        g = group,
        c = collection)
        return self._build_query(query_string)

    @retrieve
    def group_collection_sub(self, group, collection):
        """ Get collections for a specific group
        """
        query_string = '/groups/{g}/collections/{c}/collections'.format(
        u = self.user_id,
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
        u = self.user_id,
        i = item)
        return self._build_query(query_string)

    @retrieve
    def group_tags(self, group):
        """ Get tags for a specific group
        """
        query_string = '/groups/{g}/tags'.format(
        u = self.user_id,
        g = group)
        return self._build_query(query_string)

    @retrieve
    def group_item_tags(self, group, item):
        """ Get tags for a specific item in a specific group
        """
        query_string = '/groups/{g}/items/{i}/tags'.format(
        u = self.user_id,
        g = group,
        i = item)
        return self._build_query(query_string)

    def item_types(self):
        """ Get all available item types
        """
        query_string = '/itemTypes'
        retrieved = self.retrieve_data(query_string)
        return json.loads(retrieved)

    def item_fields(self):
        """ Get all available item fields
        """
        query_string = '/itemFields'
        retrieved = self.retrieve_data(query_string)
        return json.loads(retrieved)

    def item_creator_types(self, itemtype):
        """ Get all available creator types for an item
        """
        query_string = '/itemTypeCreatorTypes?itemType={i}'.format(
        i = itemtype)
        retrieved = self.retrieve_data(query_string)
        return json.loads(retrieved)

    def item_template(self, itemtype):
        """ Get a template for a new item
        """
        query_string = '/items/new?itemType={i}'.format(
        i = itemtype)
        retrieved = self.retrieve_data(query_string)
        return json.loads(retrieved)

    # These methods process returned data from Read API calls, returning lists
    def process_content(self, retrieved):
        """ Call either standard_items or bib_items, depending on the URL param
        """
        # Content request in 'bib' format, so call bib_items
        if self.url_params.find('=bib') != -1:
            return self.bib_items(retrieved)
        else:
            return self.standard_items(retrieved)

    def standard_items(self, retrieved):
        """ Format and return data from API calls which return Items
        """
        # send entries to tags_data if there's no JSON
        try:
            items = [json.loads(e['content'][0]['value'])
                for e in retrieved.entries]
        except ValueError:
            return self.tags_data(retrieved)

        # try to add various namespaced values to the items
        zapi_keys = ['key']
        for zapi in zapi_keys:
            try:
                for key, _ in enumerate(items):
                    items[key][unicode(zapi)] = \
                            retrieved.entries[key][unicode('zapi_%s' % zapi)]
            except KeyError:
                pass
        # add the etags
        for k, _ in enumerate(items):
            items[k][u'etag'] = self.etags[k]

        # Try to get a group ID, and add it to the dict
        try:
            group_id = [g['links'][0]['href'].split('/')[-1].split('?')[0]
                    for g in retrieved.entries]
            for k, val in enumerate(items):
                val[u'group_id'] = group_id[k]
        except KeyError:
            pass
        self.url_params = None
        return items

    def bib_items(self, retrieved):
        """ Return a list of strings formatted as HTML bibliography entries
        """
        items = []
        for bib in retrieved.entries:
            items.append(bib['content'][0]['value'])
        self.url_params = None
        return items

    def tags_data(self, retrieved):
        """ Format and return data from API calls which return Tags
        """
        tags = [t['title'] for t in retrieved.entries]
        self.url_params = None
        return tags

    # The following are Write API calls

    def create_items(self, payload):
        """
        Create new Zotero items
        Accepts one argument, a list containing one or more item dicts
        """
        # remove keys we may have added
        for p in payload:
            try:
                del p['etag'], p['key'], p['group_id']
            except KeyError:
                pass
        to_send = json.dumps({'items': payload})
        token = str(uuid.uuid4()).replace('-','')
        req = urllib2.Request(
        self.endpoint + '/users/{u}/items'.format(u = self.user_id) +
        '?' + urllib.urlencode({'key': self.user_key}))
        req.add_data(to_send)
        req.add_header('X-Zotero-Write-Token', token)
        req.add_header('User-Agent', 'Pyzotero/%s' % __version__)
        try:
            resp = urllib2.urlopen(req)
            data = resp.read()
            self.etags = self._etags(data)
        except (urllib2.HTTPError, urllib2.URLError), error:
            self._error_handler(req, error)
        return self.standard_items(feedparser.parse(data))

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
"Invalid request, probably due to unsupported parameters: %s" % \
                req.get_full_url()
            elif error.code == 404:
                raise ze.ResourceNotFound, \
"No results for the following query:\n%s" % req.get_full_url()
            elif error.code == 409:
                raise ze.Conflict, \
"The target library is locked"
            else:
                raise ze.HTTPError, \
"HTTP Error %s (%s)\nURL: %s\nData: %s" % (
                error.msg, error.code, req.get_full_url(), req.get_data())

