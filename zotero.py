#!/usr/bin/env python
# encoding: utf-8
"""
zotero.py

Created by Stephan Hügel on 2011-02-28
"""

import sys
import os
import urllib
import urllib2
import httplib
import feedparser

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

        Valid optional URL parameters in all modes:
        format: "atom" or "bib", default: "atom"
        key: string, default:  null
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
        # TODO: throw an error if we're missing either of the above
        # Some API methods, not exhaustive
        self.api_methods = {
        'all_items':'/users/{u}/items',                  # user_id
        'top_level':'/users/{u}/items/top',              # user_id
        'specific_item':'/users/{u}/items/%s',           # user_id, item_id
        'child_items':'/users/{u}/items/%s/children',    # user_id, item_id
        'item_tags':'/users/{u}/items/%s/tags',          # user_id, item_id
        'user_tags':'/users/{u}/tags',                   # user_id
        'items_for_tag':'/users/{u}/tags/%s/items',      # user_id, tag_id
        'collections':'/users/{u}/collections',          # user_id
        'collection_items':'/users/{u}/collections/%s',  # user_id, collect_id
        'group_items':'/groups/%s/items'                 # group_id
        }

    def retrieve_titles(self, request, url_params = None, request_params = None):
        """ General method for retrieving Zotero API resources
        """
        # This should still work even if there's no {u} field in the dict value
        request = self.api_methods[request].format(u = self.user_id)
        if url_params:
            data = urllib.urlencode(url_params)
            request = '%s%s%s' % (request, '?', data)
        full_url = '%s%s' % (self.endpoint, request)
        data = urllib2.urlopen(full_url).read()
        # print data
        feed_data = feedparser.parse(data)
        return [t['title'] for t in feed_data.entries]

def main():
    """ main function
    """
    # Read a file from your cwd. Expects user id on line 1, key on line 2, LF
    auth_values = open_file(os.path.join(os.path.expanduser('~'),
    'zotero_keys.txt'))
    zot_id = auth_values[0]
    zot_key = auth_values[1]
    zot = Zotero(zot_id, zot_key)
    # pass optional request parameters in a dict
    par = {'limit': '10', 'start': 50}
    titles = zot.retrieve_titles('all_items', par)
    print '\n'.join([t for t in titles])

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        # actually raise these, for a clean exit
        raise
    except Exception, error:
        # all other exceptions: display the error
        print error
    else:
        pass
    finally:
        # exit cleanly once we've done everything else
        sys.exit(0)