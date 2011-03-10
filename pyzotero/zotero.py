#!/usr/bin/env python
# encoding: utf-8
"""
zotero.py

Created by Stephan Hügel on 2011-02-28
Copyright Stephan Hügel, 2011

License: http://www.gnu.org/licenses/gpl-3.0.txt
"""

__version__ = '0.5'

import sys
import os
import urllib
import urllib2
import feedparser
import xml.etree.ElementTree as xml
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

    def retrieve(output_func):
        """ Decorator for Zotero methods; calls retrieve_data() and passes
            the result to the function specified by output_func
        """
        def wrap(func):
            """ Wrapper for original function
            """
            def wrapped_f(self, *args, **kwargs):
                """ Returns result of retrieve_data(), then output_func
                """
                orig_func = func(self, *args, **kwargs)
                retr = self.retrieve_data(orig_func)
                return eval(output_func)(retr)
            return wrapped_f
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

    def build_query(self, query_string, params = None):
        """ Set request parameters. Will always add the user ID if it hasn't
            been specifically set by an API call
        """
        params = {'u': self.user_id}
        try:
            query = query_string.format(**params)
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
        return self.build_query(query_string)

    @retrieve('self.items_data')
    def top(self):
        """ Get user top-level items
        """
        query_string = '/users/{u}/items/top'
        return self.build_query(query_string)

    @retrieve('self.items_data')
    def item(self, item):
        """ Get a specific item
        """
        query_string = '/users/{u}/items/{i}'.format(
        u = self.user_id, i = item)
        return self.build_query(query_string)

    @retrieve('self.items_data')
    def children(self, item):
        """ Get a specific item
        """
        query_string = '/users/{u}/items/{i}/children'.format(
        u = self.user_id,
        i = item)
        return self.build_query(query_string)

    @retrieve('self.items_data')
    def tag_items(self, tag):
        """ Get items for a specific tag
        """
        query_string = '/users/{u}/tags/{t}/items'.format(
        u = self.user_id,
        t = tag)
        return self.build_query(query_string)

    @retrieve('self.items_data')
    def collection_items(self, collection):
        """ Get a specific collection's items
        """
        query_string = '/users/{u}/collections/{c}/items'.format(
        u = self.user_id,
        c = collection)
        return self.build_query(query_string)

    @retrieve('self.items_data')
    def group_items(self, group):
        """ Get a specific group's items
        """
        query_string = '/groups/{g}/items'.format(
        g = group)
        return self.build_query(query_string)

    @retrieve('self.items_data')
    def group_top(self, group):
        """ Get a specific group's top-level items
        """
        query_string = '/groups/{g}/items/top'.format(
        g = group)
        return self.build_query(query_string)

    @retrieve('self.items_data')
    def group_item(self, group, item):
        """ Get a specific group item
        """
        query_string = '/groups/{g}/items/{i}'.format(
        g = group,
        i = item)
        return self.build_query(query_string)

    @retrieve('self.items_data')
    def group_item_children(self, group, item):
        """ Get a specific group item's child items
        """
        query_string = '/groups/{g}/items/{i}/children'.format(
        g = group,
        i = item)
        return self.build_query(query_string)

    @retrieve('self.items_data')
    def group_items_tag(self, group, tag):
        """ Get a specific group's items for a specific tag
        """
        query_string = '/groups/{g}/tags/{t}/items'.format(
        g = group,
        t = tag)
        return self.build_query(query_string)

    @retrieve('self.items_data')
    def group_collection_items(self, group, collection):
        """ Get a specific group's items for a specific collection
        """
        query_string = '/groups/{g}/collections/{c}/items'.format(
        g = group,
        c = collection)
        return self.build_query(query_string)

    @retrieve('self.items_data')
    def group_collection_top(self, group, collection):
        """ Get a specific group's top-level items for a specific collection
        """
        query_string = '/groups/{g}/collections/{c}/items/top'.format(
        g = group,
        c = collection)
        return self.build_query(query_string)

    @retrieve('self.items_data')
    def group_collection_item(self, group, collection, item):
        """ Get a specific collection's item from a specific group
        """
        query_string = '/groups/{g}/collections/{c}/items/{i}'.format(
        g = group,
        c = collection,
        i = item)
        return self.build_query(query_string)

    @retrieve('self.collections_data')
    def collections(self):
        """ Get user collections
        """
        query_string = '/users/{u}/collections'
        return self.build_query(query_string)

    @retrieve('self.collections_data')
    def collections_sub(self, collection):
        """ Get subcollections for a specific collection
        """
        query_string = '/users/{u}/collections/{c}/collections'.format(
        u = self.user_id,
        c = collection)
        return self.build_query(query_string)

    @retrieve('self.collections_data')
    def group_collections(self, group):
        """ Get collections for a specific group
        """
        query_string = '/groups/{group}/collections'.format(
        u = self.user_id,
        g = group)
        return self.build_query(query_string)

    @retrieve('self.collections_data')
    def group_collection(self, group, collection):
        """ Get collections for a specific group
        """
        query_string = '/groups/{g}/collections/{c}'.format(
        u = self.user_id,
        g = group,
        c = collection)
        return self.build_query(query_string)

    @retrieve('self.collections_data')
    def group_collection_sub(self, group, collection):
        """ Get collections for a specific group
        """
        query_string = '/groups/{g}/collections/{c}/collections'.format(
        u = self.user_id,
        g = group,
        c = collection)
        return self.build_query(query_string)

    @retrieve('self.groups_data')
    def groups(self):
        """ Get user groups
        """
        query_string = '/users/{u}/groups'
        return self.build_query(query_string)

    @retrieve('self.tags_data')
    def tags(self):
        """ Get tags for a specific item
        """
        query_string = '/users/{u}/tags'
        return self.build_query(query_string)

    @retrieve('self.tags_data')
    def item_tags(self, item):
        """ Get tags for a specific item
        """
        query_string = '/users/{u}/items/{i}/tags'.format(
        u = self.user_id,
        i = item)
        return self.build_query(query_string)

    @retrieve('self.tags_data')
    def group_tags(self, group):
        """ Get tags for a specific group
        """
        query_string = '/groups/{g}/tags'.format(
        u = self.user_id,
        g = group)
        return self.build_query(query_string)

    @retrieve('self.tags_data')
    def group_item_tags(self, group, item):
        """ Get tags for a specific group
        """
        query_string = '/groups/{g}/items/{i}/tags'.format(
        u = self.user_id,
        g = group,
        i = item)
        return self.build_query(query_string)

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
            # define a utf-8 parser with which to parse the content HTML
            utf = xml.XMLParser(encoding = 'utf-8')
            elem = xml.XML(content, utf)
            keys = [e.text.lower().encode('utf-8') for e in elem.iter('th')]
            keys = dedup(keys)
            values = [v.text.encode('utf-8') for v in elem.iter('td')]
            zipped = dict(zip(keys, values))
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

    def tags_data(self, retrieved):
        """ Format and return data from API call which return Tags
        """
        tags = [t['title'].encode('utf-8') for t in retrieved.entries]
        return tags

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
    zot.add_parameters(limit=10, start=50)
    items = zot.top()
    for item in items:
        print item.title, item.id

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