#! /usr/bin/env python
# coding=utf-8
"""
Tests for the Pyzotero module
"""

import unittest
import sys

from pyzotero import zotero as z
from pyzotero import zotero_errors as ze
import feedparser

class ZoteroTests(unittest.TestCase):

    def setUp(self):
        """ Set stuff up
        """
        self.zot = z.Zotero('myuserID', 'myuserkey')
        self.zot.add_parameters(start = 10)
        self.item_doc = """<?xml version="1.0"?>
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
        self.feed = feedparser.parse(self.item_doc)

    def testFailWithoutCredentials(self):
        """ This should fail, because we're failing to pass a credential
        """
        with self.assertRaises(ze.MissingCredentials):
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
        # /users/000/tags/hi%20there/items?start=10&key=myuserkey
        self.assertEqual(
        '/users/000/tags/hi%20there/items?start=10&key=myuserkey',
        query)

    def testParseItemAtomDoc(self):
        """ Should successfully return a list of item dicts, ID should match
            input doc's zapi:key value, and author should have been correctly
            parsed out of the XHTML payload
        """
        items_data = self.zot.items_data(self.feed)
        self.assertEqual('T4AH4RZA', items_data[0]['id'], 'message')
        self.assertEqual('T. J. McIntyre', items_data[0]['author'], 'message')

    def tearDown(self):
        """ Tear stuff down
        """



if __name__ == "__main__":
    unittest.main()
