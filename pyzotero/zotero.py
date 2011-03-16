#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
zotero.py

Created by Stephan Hügel on 2011-02-28
Copyright Stephan Hügel, 2011

License: http://www.gnu.org/licenses/gpl-3.0.txt
"""

__version__ = '0.6.7'


import urllib
import urllib2
import socket
import feedparser
import xml.etree.ElementTree as xml

import zotero_errors as ze


# Avoid hanging the application if there's no server response
timeout = 30
socket.setdefaulttimeout(timeout)

def dedup(suspects):
    """ Check for duplicate key entries (e.g. contributor) and append a number
        to these. This is a horrible hack, but the Zotero API returns items
        with non-unique key values (arbitrary no. of contributors/authors/eds)
    """
    seen = []
    counter = 2
    for candidate in suspects:
        if candidate in seen:
            candidate = '%s_%s' % (candidate, counter)
            counter += 1
            seen.append(candidate)
        else:
            seen.append(candidate)
    return seen



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
            # Distinguish between URL errors and HTTP status codes of 400+
            if hasattr(error, 'reason'):
                raise ze.CouldNotReachURL, \
    "Could not reach server. Reason: %s\nURL: %s" % (error, full_url)
            elif hasattr(error, 'code'):
                if error.code == 401 or error.code == 403:
                    raise ze.UserNotAuthorised, \
    "You are not authorised to retrieve this resource (%s)" % error.code
                elif error.code == 400:
                    raise ze.UnsupportedParams, \
    "Invalid request, probably due to unsupported parameters: %s" % \
                    full_url
                elif error.code == 404:
                    raise ze.ResourceNotFound, \
    "No results for the following query:\n%s" % full_url
                else:
                    raise ze.HTTPError, \
    "HTTP Error %s (%s)\nURL: %s" % (
                    error.msg, error.code, full_url)
        # parse the result into Python data structures
        return feedparser.parse(data)

    def retrieve(output_func):
        """ Decorator for Zotero methods; calls _retrieve_data() and passes
            the result to the function specified by output_func
        """
        def wrap(func):
            """ Wrapper for original function
            """
            def wrapped_f(self, *args, **kwargs):
                """ Returns result of retrieve_data(), then output_func

                    orig_func's return value is part of a URI, and it's this
                    which is intercepted and passed to retrieve_data:
                    '/users/123/items?key=abc123'
                    the feed-parsed atom doc returned by retrieve_data is then
                    passed to output_func (items, groups, tags, collections)
                """
                orig_func = func(self, *args, **kwargs)
                retr = self.retrieve_data(orig_func)
                return eval(output_func)(retr)
            return wrapped_f
        return wrap

    def add_parameters(self, **params):
        """ Set URL parameters. Will always add the user key
        """
        self.url_params = None
        if params:
            params['key'] = self.user_key
        else: 
            params = {'key': self.user_key}
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

    @retrieve('self.items_data')
    def items(self):
        """ Get user items 
        """
        query_string = '/users/{u}/items'
        return self._build_query(query_string)

    @retrieve('self.items_data')
    def top(self):
        """ Get user top-level items
        """
        query_string = '/users/{u}/items/top'
        return self._build_query(query_string)

    @retrieve('self.items_data')
    def item(self, item):
        """ Get a specific item
        """
        query_string = '/users/{u}/items/{i}'.format(
        u = self.user_id, i = item)
        return self._build_query(query_string)

    @retrieve('self.items_data')
    def children(self, item):
        """ Get a specific item's child items
        """
        query_string = '/users/{u}/items/{i}/children'.format(
        u = self.user_id,
        i = item)
        return self._build_query(query_string)

    @retrieve('self.items_data')
    def tag_items(self, tag):
        """ Get items for a specific tag
        """
        query_string = '/users/{u}/tags/{t}/items'.format(
        u = self.user_id,
        t = tag)
        return self._build_query(query_string)

    @retrieve('self.items_data')
    def collection_items(self, collection):
        """ Get a specific collection's items
        """
        query_string = '/users/{u}/collections/{c}/items'.format(
        u = self.user_id,
        c = collection)
        return self._build_query(query_string)

    @retrieve('self.items_data')
    def group_items(self, group):
        """ Get a specific group's items
        """
        query_string = '/groups/{g}/items'.format(
        g = group)
        return self._build_query(query_string)

    @retrieve('self.items_data')
    def group_top(self, group):
        """ Get a specific group's top-level items
        """
        query_string = '/groups/{g}/items/top'.format(
        g = group)
        return self._build_query(query_string)

    @retrieve('self.items_data')
    def group_item(self, group, item):
        """ Get a specific group item
        """
        query_string = '/groups/{g}/items/{i}'.format(
        g = group,
        i = item)
        return self._build_query(query_string)

    @retrieve('self.items_data')
    def group_item_children(self, group, item):
        """ Get a specific group item's child items
        """
        query_string = '/groups/{g}/items/{i}/children'.format(
        g = group,
        i = item)
        return self._build_query(query_string)

    @retrieve('self.items_data')
    def group_items_tag(self, group, tag):
        """ Get a specific group's items for a specific tag
        """
        query_string = '/groups/{g}/tags/{t}/items'.format(
        g = group,
        t = tag)
        return self._build_query(query_string)

    @retrieve('self.items_data')
    def group_collection_items(self, group, collection):
        """ Get a specific group's items from a specific collection
        """
        query_string = '/groups/{g}/collections/{c}/items'.format(
        g = group,
        c = collection)
        return self._build_query(query_string)

    @retrieve('self.items_data')
    def group_collection_top(self, group, collection):
        """ Get a specific group's top-level items from a specific collection
        """
        query_string = '/groups/{g}/collections/{c}/items/top'.format(
        g = group,
        c = collection)
        return self._build_query(query_string)

    @retrieve('self.items_data')
    def group_collection_item(self, group, collection, item):
        """ Get a specific collection's item from a specific group
        """
        query_string = '/groups/{g}/collections/{c}/items/{i}'.format(
        g = group,
        c = collection,
        i = item)
        return self._build_query(query_string)

    @retrieve('self.collections_data')
    def collections(self):
        """ Get user collections
        """
        query_string = '/users/{u}/collections'
        return self._build_query(query_string)

    @retrieve('self.collections_data')
    def collections_sub(self, collection):
        """ Get subcollections for a specific collection
        """
        query_string = '/users/{u}/collections/{c}/collections'.format(
        u = self.user_id,
        c = collection)
        return self._build_query(query_string)

    @retrieve('self.collections_data')
    def group_collections(self, group):
        """ Get collections for a specific group
        """
        query_string = '/groups/{group}/collections'.format(
        u = self.user_id,
        g = group)
        return self._build_query(query_string)

    @retrieve('self.collections_data')
    def group_collection(self, group, collection):
        """ Get a specific collection for a specific group
        """
        query_string = '/groups/{g}/collections/{c}'.format(
        u = self.user_id,
        g = group,
        c = collection)
        return self._build_query(query_string)

    @retrieve('self.collections_data')
    def group_collection_sub(self, group, collection):
        """ Get collections for a specific group
        """
        query_string = '/groups/{g}/collections/{c}/collections'.format(
        u = self.user_id,
        g = group,
        c = collection)
        return self._build_query(query_string)

    @retrieve('self.groups_data')
    def groups(self):
        """ Get user groups
        """
        query_string = '/users/{u}/groups'
        return self._build_query(query_string)

    @retrieve('self.tags_data')
    def tags(self):
        """ Get tags for a specific item
        """
        query_string = '/users/{u}/tags'
        return self._build_query(query_string)

    @retrieve('self.tags_data')
    def item_tags(self, item):
        """ Get tags for a specific item
        """
        query_string = '/users/{u}/items/{i}/tags'.format(
        u = self.user_id,
        i = item)
        return self._build_query(query_string)

    @retrieve('self.tags_data')
    def group_tags(self, group):
        """ Get tags for a specific group
        """
        query_string = '/groups/{g}/tags'.format(
        u = self.user_id,
        g = group)
        return self._build_query(query_string)

    @retrieve('self.tags_data')
    def group_item_tags(self, group, item):
        """ Get tags for a specific item in a specific group
        """
        query_string = '/groups/{g}/items/{i}/tags'.format(
        u = self.user_id,
        g = group,
        i = item)
        return self._build_query(query_string)

    def items_data(self, retrieved):
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
        # Shunt each 'content' block into a list
        item_parsed = [a['content'][0]['value'] for a in retrieved.entries]
        # Shunt each 'title' and item ID value into a list
        item_title = [t['title'] for t in retrieved.entries]
        item_id = [i['zapi_key'] for i in retrieved.entries]
        items = []
        for index, content in enumerate(item_parsed):
            elem = xml.fromstring(content.encode('utf-8'))
            keys = dedup(
            [e.text.lower() for e in elem.iter('th')])
            values = [v.text for v in elem.iter('td')]
            zipped = dict(zip(keys, values))
            zipped['title'] = item_title[index]
            zipped['id'] = item_id[index]
            items.append(zipped)
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

    def collections_data(self, retrieved):
        """ Format and return data from API calls which return Collections
        """
        collections = []
        collection_key = [k['zapi_key'] for k in retrieved.entries]
        collection_title = [t['title'] for t in retrieved.entries]
        collection_sub = [s['zapi_numcollections'] for s in retrieved.entries]
        for index in range(len(collection_key)):
            collection_data = {}
            collection_data['id'] = collection_key[index]
            collection_data['title'] = collection_title[index]
            if int(collection_sub[index]) > 0:
                collection_data['subcollections'] = int(collection_sub[index])
            collections.append(collection_data)
            self.url_params = None
        return collections

    def groups_data(self, retrieved):
        """ Format and return data from API calls which return Groups
        """
        groups = []
        group_uid = [i['id'] for i in retrieved.entries]
        group_title = [t['title'] for t in retrieved.entries]
        group_items = [i['zapi_numitems'] for i in retrieved.entries]
        group_author = [a['author'] for a in retrieved.entries]
        group_id = [u['links'][0]['href'] for u in retrieved.entries]
        for index in range(len(group_uid)):
            group_data = {}
            group_data['uid'] = group_uid[index]
            group_data['title'] = group_title[index]
            group_data['total_items'] = group_items[index]
            group_data['owner'] = group_author[index]
            # Ugh. Fix your fucking API. See also: dedup()
            group_data['id'] = group_id[index].split('/')[-1]
            groups.append(group_data)
            self.url_params = None
        return groups

    def tags_data(self, retrieved):
        """ Format and return data from API calls which return Tags
        """
        tags = [t['title'] for t in retrieved.entries]
        self.url_params = None
        return tags
