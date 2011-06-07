#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the Pyzotero module
"""

import unittest
import sys
import os
import zotero as z
import feedparser

import urllib2
from StringIO import StringIO



def mock_response(req, resp_obj, resp_code):
    """ Mock response for MyHTTPSHandler
    """
    resp = urllib2.addinfourl(StringIO(resp_obj),
    'This is a mocked URI!',
    req.get_full_url())
    resp.code = resp_code
    resp.msg = "OK"
    return resp


class MyHTTPSHandler(urllib2.HTTPSHandler):
    """ Mock response for urllib2
        takes 2 arguments: a string or a reference to a file, and response code
        this is what's returned by .read()
    """
    def __init__(self, resp_obj, resp_code = None):
        self.resp_obj = resp_obj
        if not resp_code:
            self.resp_code = 200
        else: self.resp_code = resp_code
    # Change HTTPSHandler and https_open to http for non-https calls
    def https_open(self, req):
        return mock_response(req, self.resp_obj, self.resp_code)



class ZoteroTests(unittest.TestCase):
    """ Tests for pyzotero
    """
    def setUp(self):
        """ Set stuff up
        """
        self.items_doc = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom" xmlns:zapi="http://zotero.org/ns/api">
          <title>Zotero / urschrei / Top-Level Items</title>
          <id>http://zotero.org/users/436/items/top?limit=1</id>
          <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/items/top?limit=1"/>
          <link rel="first" type="application/atom+xml" href="https://api.zotero.org/users/436/items/top?limit=1"/>
          <link rel="next" type="application/atom+xml" href="https://api.zotero.org/users/436/items/top?limit=1&amp;start=1"/>
          <link rel="last" type="application/atom+xml" href="https://api.zotero.org/users/436/items/top?limit=1&amp;start=949"/>
          <link rel="alternate" type="text/html" href="http://zotero.org/users/436/items/top?limit=1"/>
          <zapi:totalResults>950</zapi:totalResults>
          <zapi:apiVersion>1</zapi:apiVersion>
          <updated>2011-02-14T00:27:03Z</updated>
          <entry>
            <title>“We Need a Popular Discipline”</title>
            <author>
              <name>urschrei</name>
              <uri>http://zotero.org/urschrei</uri>
            </author>
            <id>http://zotero.org/urschrei/items/T4AH4RZA</id>
            <published>2011-02-14T00:27:03Z</published>
            <updated>2011-02-14T00:27:03Z</updated>
            <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/items/T4AH4RZA"/>
            <link rel="alternate" type="text/html" href="http://zotero.org/urschrei/items/T4AH4RZA"/>
            <zapi:key>T4AH4RZA</zapi:key>
            <zapi:itemType>journalArticle</zapi:itemType>
            <zapi:creatorSummary>McIntyre</zapi:creatorSummary>
            <zapi:numChildren>1</zapi:numChildren>
            <zapi:numTags>0</zapi:numTags>
            <content type="xhtml">
              <div xmlns="http://www.w3.org/1999/xhtml">
                <table>
                  <tr class="itemType">
                    <th style="text-align: right">Type</th>
                    <td>Joürnal Article</td>
                  </tr>
                  <tr class="creator">
                    <th style="text-align: right">Author</th>
                    <td>T. J. McIntyre</td>
                  </tr>
                  <tr class="publicationTitle">
                    <th style="text-align: right">Publication</th>
                    <td>Journal of Intellectual Property Law &amp; Practice</td>
                  </tr>
                  <tr class="ISSN">
                    <th style="text-align: right">ISSN</th>
                    <td>1747-1532</td>
                  </tr>
                  <tr class="date">
                    <th style="text-align: right">Date</th>
                    <td>2007</td>
                  </tr>
                  <tr class="libraryCatalog">
                    <th style="text-align: right">Library Catalog</th>
                    <td>Google Scholar</td>
                  </tr>
                  <tr class="shortTitle">
                    <th style="text-align: right">Short Title</th>
                    <td>Copyright in custom code</td>
                  </tr>
                </table>
              </div>
            </content>
          </entry>
        </feed>"""
        self.collections_doc = u"""<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom" xmlns:zapi="http://zotero.org/ns/api">
          <title>Zotero / urschrei / Collections</title>
          <id>http://zotero.org/users/436/collections?limit=1</id>
          <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/collections?limit=1"/>
          <link rel="first" type="application/atom+xml" href="https://api.zotero.org/users/436/collections?limit=1"/>
          <link rel="next" type="application/atom+xml" href="https://api.zotero.org/users/436/collections?limit=1&amp;start=1"/>
          <link rel="last" type="application/atom+xml" href="https://api.zotero.org/users/436/collections?limit=1&amp;start=36"/>
          <link rel="alternate" type="text/html" href="http://zotero.org/users/436/collections?limit=1"/>
          <zapi:totalResults>37</zapi:totalResults>
          <zapi:apiVersion>1</zapi:apiVersion>
          <updated>2010-04-26T14:23:45Z</updated>
          <entry>
            <title>A Midsummer Night's Dream</title>
            <author>
              <name>urschrei</name>
              <uri>http://zotero.org/urschrei</uri>
            </author>
            <id>http://zotero.org/urschrei/collections/PRMD6BGB</id>
            <published>2010-04-19T13:06:58Z</published>
            <updated>2010-04-26T14:23:45Z</updated>
            <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/collections/PRMD6BGB"/>
            <link rel="alternate" type="text/html" href="http://zotero.org/urschrei/collections/PRMD6BGB"/>
            <zapi:key>PRMD6BGB</zapi:key>
            <zapi:numCollections>0</zapi:numCollections>
            <zapi:numItems>5</zapi:numItems>
            <content type="html">
              <div xmlns="http://www.w3.org/1999/xhtml"/>
            </content>
          </entry>
        </feed>"""
        self.tags_doc = u"""<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom" xmlns:zapi="http://zotero.org/ns/api">
          <title>Zotero / urschrei / Tags</title>
          <id>http://zotero.org/users/436/tags?limit=1</id>
          <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/tags?limit=1"/>
          <link rel="first" type="application/atom+xml" href="https://api.zotero.org/users/436/tags?limit=1"/>
          <link rel="next" type="application/atom+xml" href="https://api.zotero.org/users/436/tags?limit=1&amp;start=1"/>
          <link rel="last" type="application/atom+xml" href="https://api.zotero.org/users/436/tags?limit=1&amp;start=453"/>
          <link rel="alternate" type="text/html" href="http://zotero.org/users/436/tags?limit=1"/>
          <zapi:totalResults>454</zapi:totalResults>
          <zapi:apiVersion>1</zapi:apiVersion>
          <updated>2010-03-27T13:56:08Z</updated>
          <entry xmlns:zxfer="http://zotero.org/ns/transfer">
            <title>Authority in literature</title>
            <author>
              <name>urschrei</name>
              <uri>http://zotero.org/urschrei</uri>
            </author>
            <id>http://zotero.org/urschrei/tags/Authority+in+literature</id>
            <published>2010-03-26T18:23:14Z</published>
            <updated>2010-03-27T13:56:08Z</updated>
            <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/tags/Authority+in+literature"/>
            <link rel="alternate" type="text/html" href="http://zotero.org/urschrei/tags/Authority+in+literature"/>
            <zapi:numItems>2</zapi:numItems>
            <content type="xhtml">
              <div xmlns="http://www.w3.org/1999/xhtml"/>
            </content>
          </entry>
        </feed>"""
        self.groups_doc = u"""<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom" xmlns:zapi="http://zotero.org/ns/api">
          <title>urschrei&#x2019;s Groups</title>
          <id>http://zotero.org/users/436/groups</id>
          <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/groups"/>
          <link rel="first" type="application/atom+xml" href="https://api.zotero.org/users/436/groups"/>
          <link rel="last" type="application/atom+xml" href="https://api.zotero.org/users/436/groups"/>
          <link rel="alternate" type="text/html" href="http://zotero.org/users/436/groups"/>
          <zapi:totalResults>1</zapi:totalResults>
          <zapi:apiVersion>1</zapi:apiVersion>
          <updated>2010-07-04T21:56:22Z</updated>
          <entry xmlns:zxfer="http://zotero.org/ns/transfer">
            <title>DFW</title>
            <author>
              <name>urschrei</name>
              <uri>http://zotero.org/urschrei</uri>
            </author>
            <id>http://zotero.org/groups/dfw</id>
            <published>2010-01-20T12:31:26Z</published>
            <updated>2010-07-04T21:56:22Z</updated>
            <link rel="self" type="application/atom+xml" href="https://api.zotero.org/groups/10248"/>
            <link rel="alternate" type="text/html" href="http://zotero.org/groups/dfw"/>
            <zapi:numItems>346</zapi:numItems>
            <content type="html">
              <div xmlns="http://www.w3.org/1999/xhtml"/>
            </content>
          </entry>
         </feed>"""
        self.bib_doc = """<?xml version="1.0"?>
         <feed xmlns="http://www.w3.org/2005/Atom" xmlns:zapi="http://zotero.org/ns/api">
           <title>Zotero / urschrei / Top-Level Items</title>
           <id>http://zotero.org/users/436/items/top?limit=1&amp;content=bib</id>
           <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/items/top?limit=1&amp;content=bib"/>
           <link rel="first" type="application/atom+xml" href="https://api.zotero.org/users/436/items/top?limit=1&amp;content=bib"/>
           <link rel="next" type="application/atom+xml" href="https://api.zotero.org/users/436/items/top?limit=1&amp;content=bib&amp;start=1"/>
           <link rel="last" type="application/atom+xml" href="https://api.zotero.org/users/436/items/top?limit=1&amp;content=bib&amp;start=949"/>
           <link rel="alternate" type="text/html" href="http://zotero.org/users/436/items/top?limit=1"/>
           <zapi:totalResults>950</zapi:totalResults>
           <zapi:apiVersion>1</zapi:apiVersion>
           <updated>2011-02-14T00:27:03Z</updated>
           <entry>
             <title>Copyright in custom code: Who owns commissioned software?</title>
             <author>
               <name>urschrei</name>
               <uri>http://zotero.org/urschrei</uri>
             </author>
             <id>http://zotero.org/urschrei/items/T4AH4RZA</id>
             <published>2011-02-14T00:27:03Z</published>
             <updated>2011-02-14T00:27:03Z</updated>
             <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/items/T4AH4RZA?content=bib"/>
             <link rel="alternate" type="text/html" href="http://zotero.org/urschrei/items/T4AH4RZA"/>
             <zapi:key>T4AH4RZA</zapi:key>
             <zapi:itemType>journalArticle</zapi:itemType>
             <zapi:creatorSummary>McIntyre</zapi:creatorSummary>
             <zapi:numChildren>1</zapi:numChildren>
             <zapi:numTags>0</zapi:numTags>
             <content type="xhtml">
               <div xmlns="http://www.w3.org/1999/xhtml" class="csl-bib-body" style="line-height: 1.35; padding-left: 2em; text-indent:-2em;">
           <div class="csl-entry">McIntyre, T. J. &#x201C;Copyright in custom code: Who owns commissioned software?&#x201D; <i>Journal of Intellectual Property Law &amp; Practice</i> (2007).</div>
         </div>
             </content>
           </entry>
         </feed>"""
        # Add the item file to the mock response by default
        my_opener = urllib2.build_opener(MyHTTPSHandler(self.items_doc))
        z.urllib2.install_opener(my_opener)


    def testFailWithoutCredentials(self):
        """ Instance creation should fail, because we're leaving out a
            credential
        """
        with self.assertRaises(z.ze.MissingCredentials):
            zf = z.Zotero('myuserID')

    def testRequestBuilder(self):
        """ Should add the user key, then url-encode all other added parameters
        """
        zot = z.Zotero('myuserID', 'myuserkey')
        zot.add_parameters(limit = 0, start = 7)
        self.assertEqual('start=7&limit=0&key=myuserkey', zot.url_params)

    def testBuildQuery(self):
        """ Check that spaces etc. are being correctly URL-encoded and added
            to the URL parameters
        """
        zot = z.Zotero('myuserID', 'myuserkey')
        zot.add_parameters(start = 10)
        query_string = '/users/000/tags/hi there/items'
        query = zot._build_query(query_string)
        self.assertEqual(
        '/users/000/tags/hi%20there/items?start=10&key=myuserkey',
        query)

    def testParseItemAtomDoc(self):
        """ Should successfully return a list of item dicts, ID should match
            input doc's zapi:key value, and author should have been correctly
            parsed out of the XHTML payload
        """
        zot = z.Zotero('myuserID', 'myuserkey')
        items_data = zot.items()
        self.assertEqual('T4AH4RZA', items_data[0]['id'])
        self.assertEqual(u'T. J. McIntyre', items_data[0]['author'])
        self.assertEqual(u'Joürnal Article', items_data[0]['type'])

    def testEncodings(self):
        """ Should be able to print unicode strings to stdout, and convert
            them to UTF-8 before printing them
        """
        zot = z.Zotero('myuserID', 'myuserkey')
        items_data = zot.items()
        try:
            print items_data[0]['title']
        except UnicodeError:
            self.fail('Your Python install appears unable to print unicode')
        try:
            print items_data[0]['title'].encode('utf-8')
        except UnicodeError:
            self.fail(
'Your Python install appears to dislike encoding unicode strings as UTF-8')

    def testParseItemAtomBibDoc(self):
        """ Should match a DIV with class = csl-entry
        """
        my_opener = urllib2.build_opener(MyHTTPSHandler(self.bib_doc))
        z.urllib2.install_opener(my_opener)
        zot = z.Zotero('myuserID', 'myuserkey')
        zot.url_params = 'content=bib'
        items_data = zot.items()
        dec = items_data[0].encode('utf-8')
        self.assertTrue(dec.startswith("""<div class="csl-entry">"""))

    def testParseCollectionsAtomDoc(self):
        """ Should successfully return a list of collection dicts, ID should
            match input doc's zapi:key value, and 'title' value should match
            input doc's title value
        """
        my_opener = urllib2.build_opener(MyHTTPSHandler(self.collections_doc))
        z.urllib2.install_opener(my_opener)
        zot = z.Zotero('myuserID', 'myuserkey')
        collections_data = zot.collections()
        self.assertEqual('PRMD6BGB', collections_data[0]['id'])
        self.assertEqual('A Midsummer Night\'s Dream',
        collections_data[0]['title'])

    def testParseTagsAtomDoc(self):
        """ Should successfully return a list of tags
        """
        my_opener = urllib2.build_opener(MyHTTPSHandler(self.tags_doc))
        z.urllib2.install_opener(my_opener)
        zot = z.Zotero('myuserID', 'myuserkey')
        tags_data = zot.tags()
        self.assertEqual('Authority in literature', tags_data[0])

    def testParseGroupsAtomDoc(self):
        """ Should successfully return a list of group dicts, ID should match
            input doc's zapi:key value, and 'total_items' value should match
            input doc's zapi:numItems value
        """
        my_opener = urllib2.build_opener(MyHTTPSHandler(self.groups_doc))
        z.urllib2.install_opener(my_opener)
        zot = z.Zotero('myuserID', 'myuserkey')
        groups_data = zot.groups()
        self.assertEqual('DFW', groups_data[0]['title'])
        self.assertEqual('346', groups_data[0]['total_items'])

    def testParamsReset(self):
        """ Should successfully reset URL parameters after a query string
            is built
        """
        zot = z.Zotero('myuserID', 'myuserkey')
        zot.add_parameters(start = 5, limit = 10)
        zot._build_query('/whatever')
        zot.add_parameters(start = 2)
        self.assertEqual('start=2&key=myuserkey', zot.url_params)

    def testParamsBlankAfterCall(self):
        """ self.url_params should be blank after an API call
        """
        zot = z.Zotero('myuserID', 'myuserkey')
        items = zot.items()
        self.assertEqual(None, zot.url_params)

    def testItemNotSet(self):
        """ Calling an item's property should return 'Not Set' if it doesn't exist
        """
        zot = z.Zotero('myuserID', 'myuserkey')
        items = zot.items()
        self.assertEqual('Not Set', items[0]['foo'])

    def testCollectionNotSet(self):
        """ Calling an item's property should return 'Not Set' if it doesn't exist
        """
        my_opener = urllib2.build_opener(MyHTTPSHandler(self.collections_doc))
        z.urllib2.install_opener(my_opener)
        zot = z.Zotero('myuserID', 'myuserkey')
        coll = zot.collections()
        self.assertEqual('Not Set', coll[0]['bar'])

    def testGroupNotSet(self):
        """ Calling an item's property should return 'Not Set' if it doesn't exist
        """
        my_opener = urllib2.build_opener(MyHTTPSHandler(self.groups_doc))
        z.urllib2.install_opener(my_opener)
        zot = z.Zotero('myuserID', 'myuserkey')
        groups = zot.groups()
        self.assertEqual('Not Set', groups[0]['baz'])

    def testDedup(self):
        """ Ensure that de-duplication of a list containing some repeating
            strings works OK
        """
        test_strings = ['foo', 'foo', 'bar', 'baz']
        deduped = z.dedup(test_strings)
        self.assertEqual(['foo', 'foo_2', 'bar', 'baz'], deduped)

    def testResponseForbidden(self):
        """ Ensure that an error is properly raised for 403
        """
        my_opener = urllib2.build_opener(MyHTTPSHandler(self.groups_doc, 403))
        z.urllib2.install_opener(my_opener)
        zot = z.Zotero('myuserID', 'myuserkey')
        with self.assertRaises(z.ze.UserNotAuthorised):
            zot.items()

    def testResponseUnsupported(self):
        """ Ensure that an error is properly raised for 400
        """
        my_opener = urllib2.build_opener(MyHTTPSHandler(self.groups_doc, 400))
        z.urllib2.install_opener(my_opener)
        zot = z.Zotero('myuserID', 'myuserkey')
        with self.assertRaises(z.ze.UnsupportedParams):
            zot.items()

    def testResponseNotFound(self):
        """ Ensure that an error is properly raised for 404
        """
        my_opener = urllib2.build_opener(MyHTTPSHandler(self.groups_doc, 404))
        z.urllib2.install_opener(my_opener)
        zot = z.Zotero('myuserID', 'myuserkey')
        with self.assertRaises(z.ze.ResourceNotFound):
            zot.items()

    def testResponseMiscError(self):
        """ Ensure that an error is properly raised for unspecified errors
        """
        my_opener = urllib2.build_opener(MyHTTPSHandler(self.groups_doc, 500))
        z.urllib2.install_opener(my_opener)
        zot = z.Zotero('myuserID', 'myuserkey')
        with self.assertRaises(z.ze.HTTPError):
            zot.items()

    def tearDown(self):
        """ Tear stuff down
        """



if __name__ == "__main__":
    unittest.main()
