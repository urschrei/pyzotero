#!/usr/bin/env python
# encoding: utf-8
"""
zotero_api.py

Created by Stephan Hügel on 2011-03-04
Copyright Stephan Hügel, 2011

License: http://www.gnu.org/licenses/gpl-3.0.txt
"""


def api_calls():
    """ Return a list of valid Zotero API calls
    """
    api_calls = {
    'all_items':'/users/{u}/items',
    'top_level_items':'/users/{u}/items/top',
    'specific_item':'/users/{u}/items/{item}',
    'child_items':'/users/{u}/items/{item}/children',
    'item_tags':'/users/{u}/items/{item}/tags',
    'user_tags':'/users/{u}/tags',
    'items_for_tag':'/users/{u}/tags/{tag}/items',
    'user_collections':'/users/{u}/collections',
    'collection_items':'/users/{u}/collections/{collection}/items',
    'sub_collections': '/users/{u}/collections/{collection}/collections',
    'user_groups': '/users/{u}/groups',
    'group_items':'/groups/{group}/items',
    'top_group_items': '/groups/{group}/items/top',
    'group_item': '/groups/{group}/items/{item}',
    'group_item_children': '/groups/{group}/items/{item}/children',
    'group_item_tags': '/groups/{group}/items/{item}/tags',
    'group_tags': '/groups/{group}/tags',
    'group_user_items_tag': '/groups/{group}/tags/{tag}/items',
    'group_collections': '/groups/{group}/collections',
    'group_collection': '/groups/{group}/collections/{collection}',
    'group_collection_sub':\
     '/groups/{group}/collections/{collection}/collections',
    'group_collection_items':\
     '/groups/{group}/collections/{collection}/items',
    'group_collection_item':\
    '/groups/{group}/collections/{collection}/items/{item}'
    }
    return api_calls
    