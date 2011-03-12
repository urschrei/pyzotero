#! /usr/bin/env python
# coding=utf-8
"""
Tests for the Pyzotero module
"""

import unittest

import zotero as z
import feedparser

class ZoteroTests(unittest.TestCase):
    """ Tests for pyzotero
    """
    def setUp(self):
        """ Set stuff up
        """
        self.zot = z.Zotero('myuserID', 'myuserkey')
        self.item_doc = u"""<?xml version="1.0"?>
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
        <title>Copyright in custom code: Who owns commissioned software?</title>
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
                <td>Journal Article</td>
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
        self.doc_parsed = feedparser.parse(self.item_doc)
        self.collections_parsed = feedparser.parse(self.collections_doc)
        self.tags_parsed = feedparser.parse(self.tags_doc)
        self.groups_parsed = feedparser.parse(self.groups_doc)
        self.zot.add_parameters(start = 10)

    def testFailWithoutCredentials(self):
        """ Instance creation should fail, because we're leaving out a
            credential
        """
        with self.assertRaises(z.ze.MissingCredentials):
            zf = z.Zotero('myuserID')

    def testRequestBuilder(self):
        """ Should add the user key, then url-encode all other added parameters
        """
        self.zot.add_parameters(limit = 0, start = 7)
        self.assertEqual('start=7&limit=0&key=myuserkey', self.zot.url_params)

    def testBuildQuery(self):
        """ Check that spaces etc. are being correctly URL-encoded and added
            to the URL parameters
        """
        query_string = '/users/000/tags/hi there/items'
        query = self.zot._build_query(query_string)
        self.assertEqual(
        '/users/000/tags/hi%20there/items?start=10&key=myuserkey',
        query)

    def testParseItemAtomDoc(self):
        """ Should successfully return a list of item dicts, ID should match
            input doc's zapi:key value, and author should have been correctly
            parsed out of the XHTML payload
        """
        items_data = self.zot.items_data(self.doc_parsed)
        self.assertEqual('T4AH4RZA', items_data[0]['id'], 'message')
        self.assertEqual('T. J. McIntyre', items_data[0]['author'], 'message')

    def testParseItemAtomBibDoc(self):
        """ Should fail, as setting the content = 'bib' param causes the
            return result to be passed to the bib_items
            parsing method
        """
        self.zot.url_params = 'content=bib'
        items_data = self.zot.items_data(self.doc_parsed)
        with self.assertRaises(TypeError):
            self.assertEqual('T4AH4RZA', items_data[0]['id'], 'message')

    def testParseCollectionsAtomDoc(self):
        """ Should successfully return a list of collection dicts, ID should
            match input doc's zapi:key value, and 'title' value should match
            input doc's title value
        """
        collections_data = self.zot.collections_data(self.collections_parsed)
        self.assertEqual('PRMD6BGB', collections_data[0]['id'])
        self.assertEqual('A Midsummer Night\'s Dream',
        collections_data[0]['title'])

    def testParseTagsAtomDoc(self):
        """ Should successfully return a list of tags
        """
        tags_data = self.zot.tags_data(self.tags_parsed)
        self.assertEqual('Authority in literature', tags_data[0])

    def testParseGroupsAtomDoc(self):
        """ Should successfully return a list of group dicts, ID should match
            input doc's zapi:key value, and 'total_items' value should match
            input doc's zapi:numItems value
        """
        groups_data = self.zot.groups_data(self.groups_parsed)
        self.assertEqual('DFW', groups_data[0]['id'])
        self.assertEqual('346', groups_data[0]['total_items'])

    def testParamsReset(self):
        """ Should successfully reset URL parameters after a query string
            is built
        """
        self.zot.add_parameters(start = 5, limit = 10)
        self.zot._build_query('/whatever')
        self.zot.add_parameters(start = 2)
        self.assertEqual('start=2&key=myuserkey', self.zot.url_params)

    def testDedup(self):
        """ Ensure that de-duplication of a list containing some repeating
            strings works OK
        """
        test_strings = ['foo', 'foo', 'bar', 'baz']
        deduped = z.dedup(test_strings)
        self.assertEqual(['foo', 'foo_2', 'bar', 'baz'], deduped)

    def tearDown(self):
        """ Tear stuff down
        """



if __name__ == "__main__":
    unittest.main()
