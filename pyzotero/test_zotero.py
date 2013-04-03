#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the Pyzotero module

Copyright Stephan Hügel, 2011

This file is part of Pyzotero.

Pyzotero is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Pyzotero is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Pyzotero. If not, see <http://www.gnu.org/licenses/>.
"""

import unittest
from httpretty import HTTPretty, httprettified
import zotero as z


class ZoteroTests(unittest.TestCase):
    """ Tests for pyzotero
    """
    def setUp(self):
        """ Set stuff up
        """
        self.items_doc = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom" xmlns:zapi="http://zotero.org/ns/api">
          <title>Zotero / urschrei / Items</title>
          <id>http://zotero.org/users/436/items?limit=3&amp;content=json</id>
          <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/items?limit=1&amp;content=json"/>
          <link rel="first" type="application/atom+xml" href="https://api.zotero.org/users/436/items?limit=1&amp;content=json"/>
          <link rel="next" type="application/atom+xml" href="https://api.zotero.org/users/436/items?limit=1&amp;content=json&amp;start=3"/>
          <link rel="last" type="application/atom+xml" href="https://api.zotero.org/users/436/items?limit=1&amp;content=json&amp;start=1086"/>
          <link rel="alternate" type="text/html" href="http://zotero.org/users/436/items?limit=1"/>
          <zapi:totalResults>1087</zapi:totalResults>
          <zapi:apiVersion>1</zapi:apiVersion>
          <updated>2011-05-28T11:07:58Z</updated>
          <entry>
            <title>Copyright in custom code: Who owns commissioned software?</title>
            <author>
              <name>urschrei</name>
              <uri>http://zotero.org/urschrei</uri>
            </author>
            <id>http://zotero.org/urschrei/items/T4AH4RZA</id>
            <published>2011-02-14T00:27:03Z</published>
            <updated>2011-02-14T00:27:03Z</updated>
            <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/items/T4AH4RZA?content=json"/>
            <link rel="alternate" type="text/html" href="http://zotero.org/urschrei/items/T4AH4RZA"/>
            <zapi:key>T4AH4RZA</zapi:key>
            <zapi:itemType>journalArticle</zapi:itemType>
            <zapi:creatorSummary>McIntyre</zapi:creatorSummary>
            <zapi:numChildren>1</zapi:numChildren>
            <zapi:numTags>0</zapi:numTags>
            <content type="application/json" zapi:etag="7252daf2495feb8ec89c61f391bcba24">{"itemType":"journalArticle","title":"Copyright in custom code: Who owns commissioned software?","creators":[{"creatorType":"author","firstName":"T. J.","lastName":"McIntyre"}],"abstractNote":"","publicationTitle":"Journal of Intellectual Property Law \u0026 Practice","volume":"","issue":"","pages":"","date":"2007","series":"","seriesTitle":"","seriesText":"","journalAbbreviation":"","language":"","DOI":"","ISSN":"1747-1532","shortTitle":"Copyright in custom code","url":"","accessDate":"","archive":"","archiveLocation":"","libraryCatalog":"Google Scholar","callNumber":"","rights":"","extra":"","tags":[]}</content>
          </entry>
        </feed>"""
        self.attachments_doc = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom" xmlns:zapi="http://zotero.org/ns/api">
          <title>Zotero / urschrei / Items</title>
          <id>http://zotero.org/users/436/items?limit=1&amp;content=json</id>
          <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/items?limit=1&amp;content=json"/>
          <link rel="first" type="application/atom+xml" href="https://api.zotero.org/users/436/items?limit=1&amp;content=json"/>
          <link rel="next" type="application/atom+xml" href="https://api.zotero.org/users/436/items?limit=1&amp;content=json&amp;start=1"/>
          <link rel="last" type="application/atom+xml" href="https://api.zotero.org/users/436/items?limit=1&amp;content=json&amp;start=1128"/>
          <link rel="alternate" type="text/html" href="http://zotero.org/users/436/items?limit=1"/>
          <zapi:totalResults>1129</zapi:totalResults>
          <zapi:apiVersion>1</zapi:apiVersion>
          <updated>2012-01-11T19:54:47Z</updated>
          <entry>
            <title>1641 Depositions</title>
            <author>
              <name>urschrei</name>
              <uri>http://zotero.org/urschrei</uri>
            </author>
            <id>http://zotero.org/urschrei/items/TM8QRS36</id>
            <published>2012-01-11T19:54:47Z</published>
            <updated>2012-01-11T19:54:47Z</updated>
            <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/items/TM8QRS36?content=json"/>
            <link rel="up" type="application/atom+xml" href="https://api.zotero.org/users/436/items/47RUN6RI?content=json"/>
            <link rel="alternate" type="text/html" href="http://zotero.org/urschrei/items/TM8QRS36"/>
            <zapi:key>TM8QRS36</zapi:key>
            <zapi:itemType>attachment</zapi:itemType>
            <zapi:numTags>0</zapi:numTags>
            <content zapi:type="json" zapi:etag="1686f563f9b4cb1db3a745a920bf0afa">{"itemType":"attachment","title":"1641 Depositions","accessDate":"2012-01-11 19:54:47","url":"http://1641.tcd.ie/project-conservation.php","note":"","linkMode":1,"mimeType":"text/html","charset":"utf-8","tags":[]}</content>
          </entry>
        </feed>"""
        self.collections_doc = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom" xmlns:zapi="http://zotero.org/ns/api">
          <title>Zotero / urschrei / Collections</title>
          <id>http://zotero.org/users/436/collections?limit=1&amp;content=json</id>
          <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/collections?limit=1&amp;content=json"/>
          <link rel="first" type="application/atom+xml" href="https://api.zotero.org/users/436/collections?limit=1&amp;content=json"/>
          <link rel="next" type="application/atom+xml" href="https://api.zotero.org/users/436/collections?limit=1&amp;content=json&amp;start=1"/>
          <link rel="last" type="application/atom+xml" href="https://api.zotero.org/users/436/collections?limit=1&amp;content=json&amp;start=37"/>
          <link rel="alternate" type="text/html" href="http://zotero.org/users/436/collections?limit=1"/>
          <zapi:totalResults>38</zapi:totalResults>
          <zapi:apiVersion>1</zapi:apiVersion>
          <updated>2011-03-16T15:00:09Z</updated>
          <entry>
            <title>Badiou</title>
            <author>
              <name>urschrei</name>
              <uri>http://zotero.org/urschrei</uri>
            </author>
            <id>http://zotero.org/urschrei/collections/HTUHVPE5</id>
            <published>2011-03-16T14:48:18Z</published>
            <updated>2011-03-16T15:00:09Z</updated>
            <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/collections/HTUHVPE5"/>
            <link rel="alternate" type="text/html" href="http://zotero.org/urschrei/collections/HTUHVPE5"/>
            <zapi:key>HTUHVPE5</zapi:key>
            <zapi:numCollections>0</zapi:numCollections>
            <zapi:numItems>27</zapi:numItems>
            <content type="application/json" zapi:etag="7252daf2495feb8ec89c61f391bcba24">{"name":"A Midsummer Night's Dream","parent":false}</content>
          </entry>
        </feed>"""
        self.tags_doc = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom" xmlns:zapi="http://zotero.org/ns/api">
          <title>Zotero / urschrei / Tags</title>
          <id>http://zotero.org/users/436/tags?limit=1&amp;content=json</id>
          <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/tags?limit=1&amp;content=json"/>
          <link rel="first" type="application/atom+xml" href="https://api.zotero.org/users/436/tags?limit=1&amp;content=json"/>
          <link rel="next" type="application/atom+xml" href="https://api.zotero.org/users/436/tags?limit=1&amp;content=json&amp;start=1"/>
          <link rel="last" type="application/atom+xml" href="https://api.zotero.org/users/436/tags?limit=1&amp;content=json&amp;start=319"/>
          <link rel="alternate" type="text/html" href="http://zotero.org/users/436/tags?limit=1"/>
          <zapi:totalResults>320</zapi:totalResults>
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
            <zapi:numItems>1</zapi:numItems>
          </entry>
        </feed>"""
        self.groups_doc = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom" xmlns:zapi="http://zotero.org/ns/api">
          <title>urschrei&#x2019;s Groups</title>
          <id>http://zotero.org/users/436/groups?limit=1&amp;content=json</id>
          <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/groups?limit=1&amp;content=json"/>
          <link rel="first" type="application/atom+xml" href="https://api.zotero.org/users/436/groups?limit=1&amp;content=json"/>
          <link rel="next" type="application/atom+xml" href="https://api.zotero.org/users/436/groups?limit=1&amp;content=json&amp;start=1"/>
          <link rel="last" type="application/atom+xml" href="https://api.zotero.org/users/436/groups?limit=1&amp;content=json&amp;start=1"/>
          <link rel="alternate" type="text/html" href="http://zotero.org/users/436/groups?limit=1"/>
          <zapi:totalResults>2</zapi:totalResults>
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
            <link rel="self" type="application/atom+xml" href="https://api.zotero.org/groups/10248?content=json"/>
            <link rel="alternate" type="text/html" href="http://zotero.org/groups/dfw"/>
            <zapi:numItems>468</zapi:numItems>
            <content type="application/json">{"name":"DFW","owner":436,"type":"PublicOpen","description":"%3Cp%3EA+grouped+collection+of+the+David+Foster+Wallace+bibliography%2C+adapted%2Fedited%2Fupdated+from+what%27s+available+elsewhere.%3C%2Fp%3E","url":"","hasImage":1,"libraryEnabled":1,"libraryEditing":"admins","libraryReading":"all","fileEditing":"none","members":{"2":539271}}</content>
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
             <content type="xhtml" zapi:etag="7252daf2495feb8ec89c61f391bcba24">
               <div xmlns="http://www.w3.org/1999/xhtml" class="csl-bib-body" style="line-height: 1.35; padding-left: 2em; text-indent:-2em;">
           <div class="csl-entry">McIntyre, T. J. &#x201C;Copyright in custom code: Who owns commissioned software?&#x201D; <i>Journal of Intellectual Property Law &amp; Practice</i> (2007).</div>
         </div>
             </content>
           </entry>
         </feed>"""
        self.created_response = """<?xml version="1.0"?>
        <entry xmlns="http://www.w3.org/2005/Atom" xmlns:zapi="http://zotero.org/ns/api">
          <title>Hell, I don't Know</title>
          <author>
            <name>urschrei</name>
            <uri>http://zotero.org/urschrei</uri>
          </author>
          <id>http://zotero.org/urschrei/items/NVGIBE59</id>
          <published>2011-12-14T19:24:20Z</published>
          <updated>2011-12-17T19:19:37Z</updated>
          <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/items/NVGIBE59?content=json"/>
          <link rel="alternate" type="text/html" href="http://zotero.org/urschrei/items/NVGIBE59"/>
          <zapi:key>NVGIBE59</zapi:key>
          <zapi:itemType>journalArticle</zapi:itemType>
          <zapi:creatorSummary>Salo</zapi:creatorSummary>
          <zapi:year/>
          <zapi:numChildren>1</zapi:numChildren>
          <zapi:numTags>0</zapi:numTags>
          <content type="application/json" zapi:etag="1ed002db69174ae2ae0e3b90499df15e">{"itemType":"journalArticle","title":"Hell, I don't Know","creators":[{"creatorType":"author","firstName":"Dorotea","lastName":"Salo"}],"abstractNote":"","publicationTitle":"","volume":"","issue":"","pages":"","date":"","series":"","seriesTitle":"","seriesText":"","journalAbbreviation":"","language":"","DOI":"","ISSN":"","shortTitle":"","url":"","accessDate":"","archive":"","archiveLocation":"","libraryCatalog":"","callNumber":"","rights":"","extra":"","tags":[]}</content>
        </entry>"""
        self.item_templt = """{
          "itemType" : "book",
          "title" : "",
          "creators" : [
            {
              "creatorType" : "author",
              "firstName" : "",
              "lastName" : ""
            }
          ],
          "url" : "",
          "tags" : [],
          "notes" : [],
          "etag" : ""
        }"""
        self.item_types = """[
        {
            "itemType":"artwork",
            "localized":"Artwork"
        },
        {
            "itemType":"audioRecording",
            "localized":"Audio Recording"
        },
        {
            "itemType":"bill",
            "localized":"Bill"
        },
        {
            "itemType":"blogPost",
            "localized":"Blog Post"
        },
        {
            "itemType":"book",
            "localized":"Book"
        },
        {
            "itemType":"bookSection",
            "localized":"Book Section"
        },
        {
            "itemType":"case",
            "localized":"Case"
        },
        {
            "itemType":"computerProgram",
            "localized":"Computer Program"
        },
        {
            "itemType":"conferencePaper",
            "localized":"Conference Paper"
        },
        {
            "itemType":"dictionaryEntry",
            "localized":"Dictionary Entry"
        },
        {
            "itemType":"document",
            "localized":"Document"
        },
        {
            "itemType":"email",
            "localized":"E-mail"
        },
        {
            "itemType":"encyclopediaArticle",
            "localized":"Encyclopedia Article"
        },
        {
            "itemType":"film",
            "localized":"Film"
        },
        {
            "itemType":"forumPost",
            "localized":"Forum Post"
        },
        {
            "itemType":"hearing",
            "localized":"Hearing"
        },
        {
            "itemType":"instantMessage",
            "localized":"Instant Message"
        },
        {
            "itemType":"interview",
            "localized":"Interview"
        },
        {
            "itemType":"journalArticle",
            "localized":"Journal Article"
        },
        {
            "itemType":"letter",
            "localized":"Letter"
        },
        {
            "itemType":"magazineArticle",
            "localized":"Magazine Article"
        },
        {
            "itemType":"manuscript",
            "localized":"Manuscript"
        },
        {
            "itemType":"map",
            "localized":"Map"
        },
        {
            "itemType":"newspaperArticle",
            "localized":"Newspaper Article"
        },
        {
            "itemType":"note",
            "localized":"Note"
        },
        {
            "itemType":"patent",
            "localized":"Patent"
        },
        {
            "itemType":"podcast",
            "localized":"Podcast"
        },
        {
            "itemType":"presentation",
            "localized":"Presentation"
        },
        {
            "itemType":"radioBroadcast",
            "localized":"Radio Broadcast"
        },
        {
            "itemType":"report",
            "localized":"Report"
        },
        {
            "itemType":"statute",
            "localized":"Statute"
        },
        {
            "itemType":"tvBroadcast",
            "localized":"TV Broadcast"
        },
        {
            "itemType":"thesis",
            "localized":"Thesis"
        },
        {
            "itemType":"videoRecording",
            "localized":"Video Recording"
        },
        {
            "itemType":"webpage",
            "localized":"Web Page"
        }
        ]"""
        self.keys_response = """ABCDE\nFGHIJ\nKLMNO\n"""
        # Add the item file to the mock response by default
        HTTPretty.enable()
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items?content=json&key=myuserkey',
            body=self.items_doc)

    @httprettified
    def testFailWithoutCredentials(self):
        """ Instance creation should fail, because we're leaving out a
            credential
        """
        with self.assertRaises(z.ze.MissingCredentials):
            zf = z.Zotero('myuserID')

    @httprettified
    def testRequestBuilder(self):
        """ Should add the user key, then url-encode all other added parameters
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        zot.add_parameters(limit=0, start=7)
        self.assertEqual('content=json&start=7&limit=0&key=myuserkey', zot.url_params)

    @httprettified
    def testBuildQuery(self):
        """ Check that spaces etc. are being correctly URL-encoded and added
            to the URL parameters
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        zot.add_parameters(start=10)
        query_string = '/users/{u}/tags/hi there/items'
        query = zot._build_query(query_string)
        self.assertEqual(
            '/users/myuserID/tags/hi%20there/items?content=json&start=10&key=myuserkey',
            query)

    @httprettified
    def testParseItemAtomDoc(self):
        """ Should successfully return a list of item dicts, key should match
            input doc's zapi:key value, and author should have been correctly
            parsed out of the XHTML payload
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items?content=json&key=myuserkey',
            body=self.items_doc)
        items_data = zot.items()
        self.assertEqual(u'T4AH4RZA', items_data[0]['key'])
        self.assertEqual(u'7252daf2495feb8ec89c61f391bcba24', items_data[0]['etag'])
        self.assertEqual(u'McIntyre', items_data[0]['creators'][0]['lastName'])
        self.assertEqual(u'journalArticle', items_data[0]['itemType'])
        self.assertEqual(u'Mon, 14 Feb 2011 00:27:03 GMT', items_data[0]['updated'])

    @httprettified
    def testParseAttachmentsAtomDoc(self):
        """" Ensure that attachments are being correctly parsed """
        zot = z.Zotero('myuserid', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserid/items?content=json&key=myuserkey',
            body=self.attachments_doc)
        attachments_data = zot.items()
        self.assertEqual(u'1641 Depositions', attachments_data[0]['title'])

    @httprettified
    def testParseKeysResponse(self):
        """ Check that parsing plain keys returned by format = keys works """
        zot = z.Zotero('myuserid', 'user', 'myuserkey')
        zot.url_params = 'format=keys'
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserid/items?format=keys',
            body=self.keys_response)
        response = zot.items()
        self.assertEqual('ABCDE\nFGHIJ\nKLMNO\n', response)

    @httprettified
    def testParseChildItems(self):
        """ Try and parse child items """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items/ABC123/children?content=json&key=myuserkey',
            body=self.items_doc)
        items_data = zot.children('ABC123')
        self.assertEqual(u'T4AH4RZA', items_data[0]['key'])

    @httprettified
    def testEncodings(self):
        """ Should be able to print unicode strings to stdout, and convert
            them to UTF-8 before printing them
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items?content=json&key=myuserkey',
            body=self.items_doc)
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

    @httprettified
    def testParseItemAtomBibDoc(self):
        """ Should match a DIV with class = csl-entry
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        zot.url_params = 'content=bib'
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items?content=json&key=myuserkey',
            body=self.bib_doc)
        items_data = zot.items()
        dec = items_data[0]
        self.assertTrue(dec.startswith("""<div class="csl-entry">"""))

    @httprettified
    def testParseCollectionsAtomDoc(self):
        """ Should successfully return a list of collection dicts, key should
            match input doc's zapi:key value, and 'title' value should match
            input doc's title value
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/collections?content=json&key=myuserkey',
            body=self.collections_doc)
        collections_data = zot.collections()
        self.assertEqual(u'HTUHVPE5', collections_data[0]['key'])
        self.assertEqual(
            "A Midsummer Night's Dream",
            collections_data[0]['name'])

    @httprettified
    def testParseTagsAtomDoc(self):
        """ Should successfully return a list of tags
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/tags?content=json&key=myuserkey',
            body=self.tags_doc)
        # /users/myuserID/tags?content=json&key=myuserkey
        tags_data = zot.tags()
        self.assertEqual('Authority in literature', tags_data[0])

    @httprettified
    def testParseGroupsAtomDoc(self):
        """ Should successfully return a list of group dicts, ID should match
            input doc's zapi:key value, and 'total_items' value should match
            input doc's zapi:numItems value
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/groups?content=json&key=myuserkey',
            body=self.groups_doc)
        groups_data = zot.groups()
        self.assertEqual('DFW', groups_data[0]['name'])
        self.assertEqual('10248', groups_data[0]['group_id'])

    def testParamsReset(self):
        """ Should successfully reset URL parameters after a query string
            is built
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        zot.add_parameters(start=5, limit=10)
        zot._build_query('/whatever')
        zot.add_parameters(start=2)
        self.assertEqual('content=json&start=2&key=myuserkey', zot.url_params)

    @httprettified
    def testParamsBlankAfterCall(self):
        """ self.url_params should be blank after an API call
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items?content=json&key=myuserkey',
            body=self.items_doc)
        _ = zot.items()
        self.assertEqual(None, zot.url_params)

    @httprettified
    def testResponseForbidden(self):
        """ Ensure that an error is properly raised for 403
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items?content=json&key=myuserkey',
            body=self.items_doc,
            status=403)
        with self.assertRaises(z.ze.UserNotAuthorised):
            zot.items()

    @httprettified
    def testResponseUnsupported(self):
        """ Ensure that an error is properly raised for 400
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items?content=json&key=myuserkey',
            body=self.items_doc,
            status=400)
        with self.assertRaises(z.ze.UnsupportedParams):
            zot.items()

    @httprettified
    def testResponseNotFound(self):
        """ Ensure that an error is properly raised for 404
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items?content=json&key=myuserkey',
            body=self.items_doc,
            status=404)
        with self.assertRaises(z.ze.ResourceNotFound):
            zot.items()

    @httprettified
    def testResponseMiscError(self):
        """ Ensure that an error is properly raised for unspecified errors
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items?content=json&key=myuserkey',
            body=self.items_doc,
            status=500)
        with self.assertRaises(z.ze.HTTPError):
            zot.items()

    @httprettified
    def testGetItems(self):
        """ Ensure that we can retrieve a list of all items """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/itemTypes',
            body=self.item_types)
        t = zot.item_types()
        self.assertEqual(t[0]['itemType'], 'artwork')
        self.assertEqual(t[-1]['itemType'], 'webpage')

    @httprettified
    def testGetTemplate(self):
        """ Ensure that item templates are retrieved and converted into dicts
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/items/new?itemType=book',
            body=self.item_templt)
        t = zot.item_template('book')
        self.assertEqual('book', t['itemType'])

    def testCreateCollectionError(self):
        """ Ensure that collection creation fails with the wrong dict
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        t = {'foo': 'bar'}
        with self.assertRaises(z.ze.ParamNotPassed):
            t = zot.create_collection(t)

    @httprettified
    def testCreateItem(self):
        """ Ensure that items can be created
        """
        # first, retrieve an item template
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/items/new?itemType=book',
            body=self.item_templt)
        t = zot.item_template('book')
        # Update the item type
        t['itemType'] = 'journalArticle'
        # Add keys which should be removed before the data is sent
        t['key'] = 'KEYABC123'
        t['etag'] = 'TAGABC123'
        t['group_id'] = 'GROUPABC123'
        t['updated'] = '14 March, 2011'
        tn = dict(t)
        tn['key'] = 'KEYABC124'
        ls = []
        ls.append(t)
        ls.append(tn)
        # register a 403 response
        HTTPretty.register_uri(
            HTTPretty.POST,
            'https://api.zotero.org/users/myuserID/items?key=myuserkey',
            body=self.items_doc,
            status=403)
        with self.assertRaises(z.ze.UserNotAuthorised) as e:
            _ = zot.create_items(ls)
        exc = str(e.exception)
        # this test is a kludge; we're checking the POST data in the 403 response
        self.assertIn("journalArticle", exc)
        self.assertNotIn("KEYABC123", exc)
        self.assertNotIn("TAGABC123", exc)
        self.assertNotIn("GROUPABC123", exc)

    @httprettified
    def testUpdateItem(self):
        """ Test that we can update an item
            This test is a kludge; it only tests that the mechanism for
            internal key removal is OK, and that we haven't made any silly
            list/dict comprehension or genexpr errors
        """
        import json
        # first, retrieve an item
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items?content=json&key=myuserkey',
            body=self.items_doc)
        items_data = zot.items()
        items_data[0]['title'] = 'flibble'
        json.dumps(*zot._cleanup(items_data[0]))

    def testEtagsParsing(self):
        """ Tests item and item update response etag parsing
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        self.assertEqual(z.etags(self.created_response), ['1ed002db69174ae2ae0e3b90499df15e'])
        self.assertEqual(
            z.etags(self.items_doc),
            ['7252daf2495feb8ec89c61f391bcba24'])

    def testTooManyItems(self):
        """ Should fail because we're passing too many items
        """
        itms = [i for i in xrange(51)]
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
    #         'https://api.zotero.org/users/myuserID/items?content=json&key=myuserkey',
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
