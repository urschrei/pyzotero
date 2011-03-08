#!/usr/bin/env python
# encoding: utf-8
"""
zotero.py

Created by Stephan Hügel on 2011-02-28
Copyright Stephan Hügel, 2011

License: http://www.gnu.org/licenses/gpl-3.0.txt
"""

__version__ = '0.4'

import sys
import os
import urllib
import urllib2
import feedparser
import xml.etree.ElementTree as xml
import zotero_api
import zotero_errors as ze
import traceback

def open_file(to_read):
    """ Open a text file for reading, and strip the newlines
        returns a list, one list item per line
    """
    try:
        with open(to_read, 'r') as opened:
            return [got_lines.rstrip('\n') for got_lines in opened.readlines()]
    except IOError:
        print "Couldn't read values from %s\nCan't continue." % to_read
        raise


def dedup(suspects):
    """ Check for duplicate key entries (e.g. contributor) and append a number
    to these """
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
        Most of the methods return Atom feed documents, which can be parsed
        using feedparser (http://www.feedparser.org/docs/)

        See the readme for details of valid URL and request parameters
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
        # API methods
        self.api_methods = zotero_api.api_calls()
        self.url_params = None

    def retrieve_data(self, request = None):
        """ Method for retrieving Zotero items via the API
            Returns a dict containing feed items and lists of entries
        """
        full_url = '%s%s' % (self.endpoint, request)
        try:
            data = urllib2.urlopen(full_url).read()
        except urllib2.HTTPError, error:
            if error.code == 401 or error.code == 403:
                raise ze.UserNotAuthorised, \
"You are not authorised to retrieve this resource (%s)" % error.code
            if error.code == 400:
                raise ze.RateLimitExceeded, \
"Invalid request, probably due to unsupported parameters: %s" % \
                data
            else:
                raise ze.HTTPError, \
                "HTTP Error %s (%s)" % (error.msg, error.code)
        # parse the result into Python data structures
        self.url_params = None
        return feedparser.parse(data)

    def retrieve(func):
        """ Decorator for Zotero methods; calls retrieve_data() and passes
            the result to the decorated method
        """
        def wrap(self, *args, **kwargs):
            """ Returns result of retrieve_data() to the decorated method
            """
            # build the query string from the request parameters
            # add request params to
            retr = self.retrieve_data(*args, **kwargs)
            return func(self, retr)
        return wrap

    def add_parameters(self, **params):
        """ Set URL parameters. Will always add the user key
        """
        if params:
            params['key'] = self.user_key
        else: 
            params = {'key': self.user_key}
        params = urllib.urlencode(params)
        self.url_params = params

    def build_query(self, query_string, params):
        """ Set request parameters. Will always add the user ID
        """
        if params:
            params['u'] = self.user_id
        else:
            params = {'u': self.user_id}
        try:
            query = query_string.format(params)
        except KeyError, err:
            raise ze.ParamNotPassed, \
            'There\'s a request parameter missing: %s' % err
        # Add the URL parameters and the user key, if necessary
        if not self.url_params:
            self.add_parameters()
        query = '%s?%s' % (query, self.url_params)
        return query

    def items(self, params = None):
        """ Get user items 
        """
        query_string = '/users/{u}/items'
        query = self.build_query(query_string, params)
        return self.items_data(self.retrieve_data(query))

    def collections(self, params = None):
        """ Get user collections
        """
        query_string = '/users/{u}/collections'
        query = self.build_query(query_string, params)
        return self.collections_data(self.retrieve_data(query))

    def groups(self, params = None):
        """ Get user groups
        """
        query_string = '/users/{u}/groups'
        query = self.build_query(query_string, params)
        return self.groups_data(self.retrieve_data(query))
        
    def collection_items(self, params = None):
        """ Get a collection's items 
        """
        query_string = '/users/{u}/collections/{collection}/items'
        query = self.build_query(query_string, params)
        return self.items_data(self.retrieve_data(query))

    def items_data(self, retrieved):
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
            keys = [e.text.lower() for e in elem.iter('th')]
            keys = dedup(keys)
            values = [v.text.encode('utf-8') for v in elem.iter('td')]
            zipped = dict(zip(keys, values))
            # add the utf-8 encoded 'title' and ID data to the dict:
            zipped['title'] = item_title[index].encode('utf-8')
            zipped['id'] = item_id[index].encode('utf-8')
            items.append(Item(zipped))
        return items

    def collections_data(self, retrieved):
        """ Format and return data from API calls which return collections
        """
        collections = []
        collection_key = [k['zapi_key'] for k in retrieved.entries]
        collection_title = [t['title'] for t in retrieved.entries]
        collection_sub = [s['zapi_numcollections'] for s in retrieved.entries]
        for index in range(len(collection_key)):
            collection_data = {}
            collection_data['id'] = collection_key[index].encode('utf-8')
            collection_data['title'] = collection_title[index].encode('utf-8')
            if int(collection_sub[index]) > 0:
                collection_data['subcollections'] = int(collection_sub[index])
            collections.append(collection_data)
        return collections

    def groups_data(self, retrieved):
        """ Format and return data from API calls which return Groups
        """
        groups = []
        group_id = [t['title'] for t in retrieved.entries]
        group_items = [i['zapi_numitems'] for i in retrieved.entries]
        group_author = [a['author'] for a in retrieved.entries]
        for index in range(len(group_id)):
            group_data = {}
            group_data['id'] = group_id[index].encode('utf-8')
            group_data['total_items'] = group_items[index].encode('utf-8')
            group_data['owner'] = group_author[index].encode('utf-8')
            groups.append(group_data)
        return groups



class Item(object):
    """ Adds all retrieved values as instance properties by key, value.
        Currently, this class is little more than a container for what would
        otherwise be dicts (and I'm not convinced they aren't the way to go)
    """
    def __init__(self, values):
        super(Item, self).__init__()
        # Hackish and bad; creates instance attributes on the fly
        self.__dict__ = dict(values)

    def __getattr__(self, name):
        """ Only called if __getattribute__ fails, so we can return
            None without too much hand-wringing
        """
        return None



def main():
    """ main function
    """
    # Read a file from your cwd. Expects user id on line 1, key on line 2, LF
    auth_values = open_file(os.path.join(os.path.expanduser('~'),
    'zotero_keys.txt'))
    zot_id = auth_values[0]
    zot_key = auth_values[1]
    zot = Zotero(zot_id, zot_key)
    zot.add_parameters(limit=5)
    # returns list of Items
    items = zot.items()
    for item in items:
        # this will explode unless your system encoding is set to UTF-8
        print 'Author: %s | Title: %s' % (item.author, item.title)
    # returns list of collection dicts
    zot.add_parameters(limit=5)
    collections = zot.collections()
    for item in collections:
        print 'Collection Title: %s | ID: %s' % (item['title'], item['id'])
    # returns list of of group dicts
    groups = zot.groups()
    for group in groups:
        print group['id']
    # returns a collection's items:
    collection_items = zot.collection_items('PRMD6BGB')
    for item in collection_item:
        print 'Author: %s | Title: %s' % (item.author, item.title)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        # actually raise these, for a clean exit
        raise
    except Exception, errm:
        # all other exceptions: display the error
        print errm
        print "Stack trace:\n", traceback.print_exc(file = sys.stdout)
    else:
        pass
    finally:
        # exit cleanly once we've done everything else
        sys.exit(0)