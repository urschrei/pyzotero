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



class Zotero(object):
    """ Zotero API methods
        A full list of methods can be found here:
        http://www.zotero.org/support/dev/server_api
        Most of the methods return Atom feed documents, which can be parsed
        using feedparser (http://www.feedparser.org/docs/)

        Valid optional URL parameters for all calls: ('key' added by default)
        format: "atom" or "bib", default: "atom"
        version: integer, default: null

        Valid optional URL parameters for format=atom:
        content: "none", "html", "bib", default: "html"
        order: string, name of field to be used, default: "dateAdded"
        sort: "asc", "desc", default varies by "order"
        limit: integer 1 - 99, default 50
        start: integer, default: 0
        pprint: boolean, default: false
    """
    user_id = None
    user_key = None
    
    def __init__(self, user_id = None, user_key = None):
        """ Store Zotero credentials
        """
        self.endpoint = 'https://api.zotero.org'
        if user_id and user_key:
            self.user_id = user_id
            self.user_key = user_key
        # API methods
        self.api_methods = zotero_api.api_calls()
    def retrieve_data(self, request, url_params = None, request_params = None):
        """ Method for retrieving Zotero items via the API
            returns a dict containing feed items and lists of entries
        """
        # Add request parameter(s) if required
        if request not in self.api_methods:
            raise ze.CallDoesNotExist, \
            'The API call \'%s\' could not be found' % request
        if request_params:
            try:
                request_params['u'] = self.user_id
                request = urllib.quote(
                self.api_methods[request].format(**request_params))
            except KeyError, err:
                raise ze.ParamNotPassed, \
                'There\'s a request parameter missing: %s' % err
        # Otherwise, just add the user ID
        else:
            try:
                request = self.api_methods[request].format(u = self.user_id)
            except KeyError, err:
                raise ze.ParamNotPassed, \
                'There\'s a request parameter missing: %s' % err
        # Add URL parameters if they're passed
        if url_params:
            url_params['key'] = self.user_key
            data = urllib.urlencode(url_params)
        # Otherwise, just add the user key
        else:
            url_params = {'key': self.user_key}
            data = urllib.urlencode(url_params)
        request = '%s%s%s' % (request, '?', data)
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
        return feedparser.parse(data)

    def retrieve(func):
        """ Decorator for Zotero methods; calls retrieve_data() and passes
            the result to the decorated method
        """
        def wrap(self, *args, **kwargs):
            """ Returns result of retrieve_data() to the decorated method
            """
            retr = self.retrieve_data(*args, **kwargs)
            return func(self, retr)
        return wrap

    def total_items(self):
        """ Return the total number of items in the library
        """
        get_count = self.retrieve_data('top_level_items', {'limit': 1})
        return get_count.feed['zapi_totalresults'].decode('utf-8')

    @retrieve
    def items_data(self, retrieved):
        """ Takes the feed-parsed result of an API call, and returns a list
            containing one or more dicts containing item data
        """
        # Shunt each 'content' block into a list
        item_parsed = [a['content'][0]['value'] for a in retrieved.entries]
        # Shunt each 'title' and item ID value into a list
        item_title = [t['title'] for t in retrieved.entries]
        item_id = [i['zapi_key'] for i in retrieved.entries]
        items = []
        for index, content in enumerate(item_parsed):
            elem = xml.fromstring(content.encode('utf-8'))
            keys = [e.text for e in elem.iter('th')]
            values = [v.text for v in elem.iter('td')]
            zipped = dict(zip(keys, values))
            # add the utf-8 encoded 'title' and ID data to the dict:
            zipped['Title'] = item_title[index].encode('utf-8')
            zipped['ID'] = item_id[index].encode('utf-8')
            items.append(zipped)
        return items

    @retrieve
    def bib_items(self, request, params = None, request_params = None):
        """ Returns a list of strings formatted as HTML bibliography entries
            you may specify a 'style' key (e.g. 'mla' in your {params}; any
            default style in the Zotero Style Repository is valid
        """
        if params and 'content' not in params:
            params['content'] = 'bib'
        else:
            params = {'content': 'bib'}
        fp_object = self.retrieve_data(request, params, request_params)
        items = []
        for bib in fp_object.entries:
            items.append(bib['content'][0]['value'].encode('utf-8'))
        return items

    @retrieve
    def gen_items_data(self, retrieved):
        """ Returns a generator object containing one or more dicts
            of item data
        """
        # Shunt each 'content' block into a list
        item_parsed = [a['content'][0]['value'] for a in retrieved.entries]
        # Shunt each 'title' and item ID value into a list
        item_title = [t['title'] for t in retrieved.entries]
        item_id = [i['zapi_key'] for i in retrieved.entries]
        items = []
        for index, content in enumerate(item_parsed):
            elem = xml.fromstring(content.encode('utf-8'))
            keys = [e.text for e in elem.iter('th')]
            values = [v.text for v in elem.iter('td')]
            zipped = dict(zip(keys, values))
            # add the utf-8 encoded 'title' and ID data to the dict:
            zipped['Title'] = item_title[index].encode('utf-8')
            zipped['ID'] = item_id[index].encode('utf-8')
            items.append(zipped)
        return (i for i in items)

    @retrieve
    def collections_data(self, retrieved):
        """ Takes the feed-parsed result of an API call, and returns a list
            containing one or more dicts containing collection titles, IDs,
            and the number of subcollections it contains (if any)
        """
        collections = []
        collection_key = [k['zapi_key'] for k in retrieved.entries]
        collection_title = [t['title'] for t in retrieved.entries]
        collection_sub = [s['zapi_numcollections'] for s in retrieved.entries]
        for index, content in enumerate(collection_key):
            collection_data = {}
            collection_data['ID'] = collection_key[index].encode('utf-8')
            collection_data['title'] = collection_title[index].encode('utf-8')
            if int(collection_sub[index]) > 0:
                collection_data['subcollections'] = int(collection_sub[index])
            collections.append(collection_data)
        return collections

    @retrieve
    def groups_data(self, retrieved):
        """ Takes the feed-parsed result of an API call, and returns a list
            containing one or more dicts containing group titles, IDs,
            and the total number of items they contain
        """
        groups = []
        group_id = [t['title'] for t in retrieved.entries]
        group_items = [i['zapi_numitems'] for i in retrieved.entries]
        group_author = [a['author'] for a in retrieved.entries]
        for index, content in enumerate(group_id):
            group_data = {}
            group_data['ID'] = group_id[index].encode('utf-8')
            group_data['total_items'] = group_items[index].encode('utf-8')
            group_data['owner'] = group_author[index].encode('utf-8')
            groups.append(group_data)
        return groups

    @retrieve
    def tags_data(self, retrieved):
        """ Takes the feed-parsed result of an API call, and returns a list
            containing one or more tags
        """
        tags = [t['title'].encode('utf-8') for t in retrieved.entries]
        return tags


def main():
    """ main function
    """
    # Read a file from your cwd. Expects user id on line 1, key on line 2, LF
    auth_values = open_file(os.path.join(os.path.expanduser('~'),
    'zotero_keys.txt'))
    zot_id = auth_values[0]
    zot_key = auth_values[1]
    zot = Zotero(zot_id, zot_key)
    # Pass optional URL and request parameters in a dict
    par = {'limit': 2}
    req = {'tag': 'Criticism, Textual'}
    # print zot.items_data('top_level_items', par)
    print zot.items_data('items_for_tag', par, req)
    # par2 = {'limit': 2, 'style': 'mla'}
    # print zot.groups_data('user_groups')
    # print zot.collections_data('user_collections', par)
    # print zot.items_data('top_level_items', par)
    # print zot.bib_items('top_level_items', par2)


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