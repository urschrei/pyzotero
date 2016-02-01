#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the Pyzotero module

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

import os
import json
import unittest
import httpretty
from httpretty import HTTPretty
from pyzotero.pyzotero import zotero as z
from dateutil import parser

# Python 3 compatibility faffing
try:
    from urllib import urlencode
    from urllib import quote
    from urlparse import urlparse
    from urlparse import parse_qs
except ImportError:
    from urllib.parse import urlencode
    from urllib.parse import urlparse
    from urllib.parse import parse_qs
    from urllib.parse import quote


class ZoteroTests(unittest.TestCase):
    """ Tests for pyzotero
    """
    cwd = os.path.dirname(os.path.realpath(__file__))

    def get_doc(self, doc_name, cwd=cwd):
        """ return the requested test document """
        with open(os.path.join(cwd, 'api_responses', '%s' % doc_name), 'r') as f:
            return f.read()

    def setUp(self):
        """ Set stuff up
        """
        self.item_doc = self.get_doc('item_doc.json')
        self.items_doc = self.get_doc('items_doc.json')
        self.collections_doc = self.get_doc('collections_doc.json')
        self.collection_doc = self.get_doc('collection_doc.json')
        self.citation_doc = self.get_doc('citation_doc.xml')
        # self.biblio_doc = self.get_doc('bib_doc.xml')
        self.attachments_doc = self.get_doc('attachments_doc.json')
        self.tags_doc = self.get_doc('tags_doc.json')
        self.groups_doc = self.get_doc('groups_doc.json')
        self.item_templt = self.get_doc('item_template.json')
        self.item_types = self.get_doc('item_types.json')
        self.keys_response = self.get_doc('keys_doc.txt')
        self.creation_doc = self.get_doc('creation_doc.json')
        self.item_file = self.get_doc('item_file.pdf')
        # Add the item file to the mock response by default
        HTTPretty.enable()
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items',
            content_type='application/json',
            body=self.items_doc)

    @httpretty.activate
    def testFailWithoutCredentials(self):
        """ Instance creation should fail, because we're leaving out a
            credential
        """
        with self.assertRaises(z.ze.MissingCredentials):
            z.Zotero('myuserID')

    @httpretty.activate
    def testRequestBuilder(self):
        """ Should url-encode all added parameters
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        zot.add_parameters(limit=0, start=7)
        self.assertEqual(
            parse_qs('start=7&limit=100&format=json'),
            parse_qs(zot.url_params))

    # @httpretty.activate
    # def testBuildQuery(self):
    #     """ Check that spaces etc. are being correctly URL-encoded and added
    #         to the URL parameters
    #     """
    #     orig = 'https://api.zotero.org/users/myuserID/tags/hi%20there/items?start=10&format=json'
    #     zot = z.Zotero('myuserID', 'user', 'myuserkey')
    #     zot.add_parameters(start=10)
    #     query_string = '/users/{u}/tags/hi there/items'
    #     query = zot._build_query(query_string)
    #     self.assertEqual(
    #         sorted(parse_qs(orig).items()),
    #         sorted(parse_qs(query).items()))

    @httpretty.activate
    def testParseItemJSONDoc(self):
        """ Should successfully return a list of item dicts, key should match
            input doc's zapi:key value, and author should have been correctly
            parsed out of the XHTML payload
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items',
            content_type='application/json',
            body=self.item_doc)
        items_data = zot.items()
        self.assertEqual(u'X42A7DEE', items_data['data']['key'])
        self.assertEqual(u'Institute of Physics (Great Britain)', items_data['data']['creators'][0]['name'])
        self.assertEqual(u'book', items_data['data']['itemType'])
        test_dt = parser.parse("2011-01-13T03:37:29Z")
        incoming_dt = parser.parse(items_data['data']['dateModified'])
        self.assertEqual(test_dt, incoming_dt)

    @httpretty.activate
    def testGetItemFile(self):
        """
        Should successfully return a binary string with a PDF content
        """
        zot = z.Zotero('myuserid', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserid/items/MYITEMID/file',
            content_type='application/pdf',
            body=self.item_file)
        items_data = zot.file('myitemid')
        self.assertEqual(b'One very strange PDF\n', items_data)

    @httpretty.activate
    def testParseAttachmentsJSONDoc(self):
        """ Ensure that attachments are being correctly parsed """
        zot = z.Zotero('myuserid', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserid/items',
            content_type='application/json',
            body=self.attachments_doc)
        attachments_data = zot.items()
        self.assertEqual(u'1641 Depositions', attachments_data['data']['title'])

    @httpretty.activate
    def testParseKeysResponse(self):
        """ Check that parsing plain keys returned by format = keys works """
        zot = z.Zotero('myuserid', 'user', 'myuserkey')
        zot.url_params = 'format=keys'
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserid/items?format=keys',
            content_type='text/plain',
            body=self.keys_response)
        response = zot.items()
        self.assertEqual('JIFWQ4AN', response[:8].decode("utf-8"))

    @httpretty.activate
    def testParseChildItems(self):
        """ Try and parse child items """
        zot = z.Zotero('myuserid', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserid/items/ABC123/children',
            content_type='application/json',
            body=self.items_doc)
        items_data = zot.children('ABC123')
        self.assertEqual(u'NM66T6EF', items_data[0]['key'])

    @httpretty.activate
    def testCitUTF8(self):
        """ Ensure that unicode citations are correctly processed by Pyzotero
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        url = 'https://api.zotero.org/users/myuserID/items/GW8V2CK7'
        HTTPretty.register_uri(
            HTTPretty.GET,
            url,
            content_type='application/atom+xml',
            body=self.citation_doc)
        cit = zot.item('GW8V2CK7', content='citation', style='chicago-author-date')
        self.assertEqual(
            cit[0],
            u'<span>(Ans\\xe6lm and Tka\\u010dik 2014)</span>')
    # @httpretty.activate
    # def testParseItemAtomBibDoc(self):
    #     """ Should match a DIV with class = csl-entry
    #     """
    #     zot = z.Zotero('myuserID', 'user', 'myuserkey')
    #     zot.url_params = 'content=bib'
    #     HTTPretty.register_uri(
    #         HTTPretty.GET,
    #         'https://api.zotero.org/users/myuserID/items?content=bib&format=atom',
    #         content_type='application/atom+xml',
    #         body=self.biblio_doc)
    #     items_data = zot.items()
    #     self.assertEqual(
    #         items_data[0],
    #         u'<div class="csl-entry">Robert A. Caro. \u201cThe Power Broker\u202f: Robert Moses and the Fall of New York,\u201d 1974.</div>'
    #         )

    @httpretty.activate
    def testParseCollectionJSONDoc(self):
        """ Should successfully return a single collection dict,
            'name' key value should match input doc's name value
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/collections/KIMI8BSG',
            content_type='application/json',
            body=self.collection_doc)
        collections_data = zot.collection('KIMI8BSG')
        self.assertEqual(
            "LoC",
            collections_data['data']['name'])

    @httpretty.activate
    def testParseCollectionsJSONDoc(self):
        """ Should successfully return a list of collection dicts, key should
            match input doc's zapi:key value, and 'title' value should match
            input doc's title value
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/collections',
            content_type='application/json',
            body=self.collections_doc)
        collections_data = zot.collections()
        self.assertEqual(
            "LoC",
            collections_data[0]['data']['name'])

    @httpretty.activate
    def testParseTagsJSON(self):
        """ Should successfully return a list of tags
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/tags?limit=1',
            content_type='application/json',
            body=self.tags_doc)
        tags_data = zot.tags()
        self.assertEqual(u'Community / Economic Development', tags_data[0])

    @httpretty.activate
    def testParseGroupsJSONDoc(self):
        """ Should successfully return a list of group dicts, ID should match
            input doc's zapi:key value, and 'total_items' value should match
            input doc's zapi:numItems value
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/groups',
            content_type='application/json',
            body=self.groups_doc)
        groups_data = zot.groups()
        self.assertEqual('smart_cities', groups_data[0]['data']['name'])

    def testParamsReset(self):
        """ Should successfully reset URL parameters after a query string
            is built
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        zot.add_parameters(start=5, limit=10)
        zot._build_query('/whatever')
        zot.add_parameters(start=2)
        self.assertEqual(
            parse_qs('start=2&format=json&limit=100'),
            parse_qs(zot.url_params))

    @httpretty.activate
    def testParamsBlankAfterCall(self):
        """ self.url_params should be blank after an API call
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items',
            content_type='application/json',
            body=self.items_doc)
        zot.items()
        self.assertEqual(None, zot.url_params)

    @httpretty.activate
    def testResponseForbidden(self):
        """ Ensure that an error is properly raised for 403
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items',
            content_type='application/json',
            body=self.items_doc,
            status=403)
        with self.assertRaises(z.ze.UserNotAuthorised):
            zot.items()

    @httpretty.activate
    def testResponseUnsupported(self):
        """ Ensure that an error is properly raised for 400
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items',
            content_type='application/json',
            body=self.items_doc,
            status=400)
        with self.assertRaises(z.ze.UnsupportedParams):
            zot.items()

    @httpretty.activate
    def testResponseNotFound(self):
        """ Ensure that an error is properly raised for 404
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items',
            body=self.items_doc,
            content_type='application/json',
            status=404)
        with self.assertRaises(z.ze.ResourceNotFound):
            zot.items()

    @httpretty.activate
    def testResponseMiscError(self):
        """ Ensure that an error is properly raised for unspecified errors
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items',
            content_type='application/json',
            body=self.items_doc,
            status=500)
        with self.assertRaises(z.ze.HTTPError):
            zot.items()

    @httpretty.activate
    def testGetItems(self):
        """ Ensure that we can retrieve a list of all items """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/itemTypes',
            content_type='application/json',
            body=self.item_types)
        resp = zot.item_types()
        self.assertEqual(resp[0]['itemType'], 'artwork')

    @httpretty.activate
    def testGetTemplate(self):
        """ Ensure that item templates are retrieved and converted into dicts
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/items/new?itemType=book',
            content_type='application/json',
            body=self.item_templt)
        t = zot.item_template('book')
        self.assertEqual('book', t['itemType'])

    def testCreateCollectionError(self):
        """ Ensure that collection creation fails with the wrong dict
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        t = [{'foo': 'bar'}]
        with self.assertRaises(z.ze.ParamNotPassed):
            t = zot.create_collection(t)

    @httpretty.activate
    def testNoApiKey(self):
        """ Ensure that pyzotero works when api_key is not set
        """
        zot = z.Zotero('myuserID', 'user')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items',
            content_type='application/json',
            body=self.item_doc)
        items = zot.items()
        self.assertEqual(len(items), 6) # this isn't a very good assertion

    # @httpretty.activate
    # def testUpdateItem(self):
    #     """ Test that we can update an item
    #         This test is a kludge; it only tests that the mechanism for
    #         internal key removal is OK, and that we haven't made any silly
    #         list/dict comprehension or genexpr errors
    #     """
    #     import json
    #     # first, retrieve an item
    #     zot = z.Zotero('myuserID', 'user', 'myuserkey')
    #     HTTPretty.register_uri(
    #         HTTPretty.GET,
    #         'https://api.zotero.org/users/myuserID/items',
    #         body=self.items_doc)
    #     items_data = zot.items()
    #     items_data['title'] = 'flibble'
    #     json.dumps(*zot._cleanup(items_data))

    @httpretty.activate
    def testItemCreation(self):
        """ Tests creation of a new item using a template
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/items/new?itemType=book',
            body=self.item_templt,
            content_type='application/json')
        template = zot.item_template('book')
        httpretty.reset()
        HTTPretty.register_uri(
            HTTPretty.POST,
            'https://api.zotero.org/users/myuserID/items',
            body=self.creation_doc,
            content_type='application/json',
            status=200)
        # now let's test something
        resp = zot.create_items([template])
        self.assertEqual('ABC123', resp['success']['0'])

    def testTooManyItems(self):
        """ Should fail because we're passing too many items
        """
        itms = [i for i in range(51)]
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        with self.assertRaises(z.ze.TooManyItems):
            zot.create_items(itms)

    # @httprettified
    # def testRateLimit(self):
    #     """ Test 429 response handling (e.g. wait, wait a bit longer etc.)
    #     """
    #     zot = z.Zotero('myuserID', 'user', 'myuserkey')
    #     HTTPretty.register_uri(
    #         HTTPretty.GET,
    #         'https://api.zotero.org/users/myuserID/items',
    #         responses=[
    #             HTTPretty.Response(body=self.items_doc, status=429),
    #             HTTPretty.Response(body=self.items_doc, status=429),
    #             HTTPretty.Response(body=self.items_doc, status=200)])
    #     zot.items()
    #     with self.assertEqual(z.backoff.delay, 8):
    #         zot.items()

    def tearDown(self):
        """ Tear stuff down
        """
        HTTPretty.disable()


if __name__ == "__main__":
    unittest.main()
