"""
Tests for the Pyzotero module

This file is part of Pyzotero.
"""
# ruff: noqa: N802

import datetime
import json
import os
import time
import unittest
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import httpretty
import pytz
import whenever
from dateutil import parser
from httpretty import HTTPretty

try:
    from pyzotero.pyzotero import zotero as z
    from pyzotero.pyzotero.zotero import DEFAULT_ITEM_LIMIT
except ModuleNotFoundError:
    from pyzotero import zotero as z
    from pyzotero.zotero import DEFAULT_ITEM_LIMIT
from urllib.parse import urlencode


class ZoteroTests(unittest.TestCase):
    """Tests for pyzotero"""

    cwd = os.path.dirname(os.path.realpath(__file__))

    def get_doc(self, doc_name, cwd=cwd):
        """Return the requested test document"""
        with open(os.path.join(cwd, "api_responses", f"{doc_name}")) as f:
            return f.read()

    def setUp(self):
        """Set stuff up"""
        self.item_doc = self.get_doc("item_doc.json")
        self.items_doc = self.get_doc("items_doc.json")
        self.item_versions = self.get_doc("item_versions.json")
        self.collection_versions = self.get_doc("collection_versions.json")
        self.collections_doc = self.get_doc("collections_doc.json")
        self.collection_doc = self.get_doc("collection_doc.json")
        self.collection_tags = self.get_doc("collection_tags.json")
        self.citation_doc = self.get_doc("citation_doc.xml")
        # self.biblio_doc = self.get_doc('bib_doc.xml')
        self.attachments_doc = self.get_doc("attachments_doc.json")
        self.tags_doc = self.get_doc("tags_doc.json")
        self.groups_doc = self.get_doc("groups_doc.json")
        self.item_templt = self.get_doc("item_template.json")
        self.item_types = self.get_doc("item_types.json")
        self.item_fields = self.get_doc("item_fields.json")
        self.keys_response = self.get_doc("keys_doc.txt")
        self.creation_doc = self.get_doc("creation_doc.json")
        self.item_file = self.get_doc("item_file.pdf")

        # Add the item file to the mock response by default
        HTTPretty.enable()
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserID/items",
            content_type="application/json",
            body=self.items_doc,
        )

    def testBuildUrlCorrectHandleEndpoint(self):
        """Url should be concat correctly by build_url"""
        url = z.build_url("http://localhost:23119/api", "/users/0")
        self.assertEqual(url, "http://localhost:23119/api/users/0")
        url = z.build_url("http://localhost:23119/api/", "/users/0")
        self.assertEqual(url, "http://localhost:23119/api/users/0")

    @httpretty.activate
    def testFailWithoutCredentials(self):
        """Instance creation should fail, because we're leaving out a
        credential
        """
        with self.assertRaises(z.ze.MissingCredentialsError):
            z.Zotero("myuserID")

    @httpretty.activate
    def testRequestBuilder(self):
        """Should url-encode all added parameters"""
        zot = z.Zotero("myuserID", "user", "myuserkey")
        zot.add_parameters(limit=0, start=7)
        self.assertEqual(
            parse_qs(f"start=7&limit={DEFAULT_ITEM_LIMIT}&format=json"),
            parse_qs(urlencode(zot.url_params, doseq=True)),
        )

    @httpretty.activate
    def testLocale(self):
        """Should correctly add locale to request because it's an initial request"""
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserID/items",
            content_type="application/json",
            body=self.item_doc,
        )
        zot = z.Zotero("myuserID", "user", "myuserkey")
        _ = zot.items()
        req = zot.request
        self.assertIn("locale=en-US", str(req.url))

    @httpretty.activate
    def testLocalePreservedWithMethodParams(self):
        """Should preserve locale when methods provide their own parameters"""
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserID/items/top",
            content_type="application/json",
            body=self.items_doc,
        )
        # Test with non-default locale
        zot = z.Zotero("myuserID", "user", "myuserkey", locale="de-DE")
        # Call top() with limit which internally adds parameters
        _ = zot.top(limit=1)
        req = zot.request
        # Check that locale is preserved in the URL
        self.assertIn("locale=de-DE", str(req.url))
        # Also verify the method parameter is present
        self.assertIn("limit=1", str(req.url))

    @httpretty.activate
    def testRequestBuilderLimitNone(self):
        """Should skip limit = 100 param if limit is set to None"""
        zot = z.Zotero("myuserID", "user", "myuserkey")
        zot.add_parameters(limit=None, start=7)
        self.assertEqual(
            parse_qs("start=7&format=json"), parse_qs(urlencode(zot.url_params))
        )

    @httpretty.activate
    def testRequestBuilderLimitNegativeOne(self):
        """Should skip limit = 100 param if limit is set to -1"""
        zot = z.Zotero("myuserID", "user", "myuserkey")
        zot.add_parameters(limit=-1, start=7)
        self.assertEqual(
            parse_qs("start=7&format=json"),
            parse_qs(urlencode(zot.url_params, doseq=True)),
        )

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
        """Should successfully return a list of item dicts, key should match
        input doc's zapi:key value, and author should have been correctly
        parsed out of the XHTML payload
        """
        zot = z.Zotero("myuserID", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserID/items",
            content_type="application/json",
            body=self.item_doc,
        )
        items_data = zot.items()
        self.assertEqual("X42A7DEE", items_data["data"]["key"])
        self.assertEqual(
            "Institute of Physics (Great Britain)",
            items_data["data"]["creators"][0]["name"],
        )
        self.assertEqual("book", items_data["data"]["itemType"])
        test_dt = parser.parse("2011-01-13T03:37:29Z")
        incoming_dt = parser.parse(items_data["data"]["dateModified"])
        self.assertEqual(test_dt, incoming_dt)

    @httpretty.activate
    def testBackoff(self):
        """Test that backoffs are correctly processed"""
        zot = z.Zotero("myuserID", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserID/items",
            content_type="application/json",
            body=self.item_doc,
            adding_headers={"backoff": 0.2},
        )
        zot.items()
        self.assertTrue(zot.backoff)
        time.sleep(0.3)
        # Timer will have expired, triggering backoff reset
        self.assertFalse(zot.backoff)

    @httpretty.activate
    def testGetItemFile(self):
        """
        Should successfully return a binary string with a PDF content
        """
        zot = z.Zotero("myuserid", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserid/items/MYITEMID/file",
            content_type="application/pdf",
            body=self.item_file,
        )
        items_data = zot.file("myitemid")
        self.assertEqual(b"One very strange PDF\n", items_data)

    @httpretty.activate
    def testParseAttachmentsJSONDoc(self):
        """Ensure that attachments are being correctly parsed"""
        zot = z.Zotero("myuserid", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserid/items",
            content_type="application/json",
            body=self.attachments_doc,
        )
        attachments_data = zot.items()
        self.assertEqual("1641 Depositions", attachments_data["data"]["title"])

    @httpretty.activate
    def testParseKeysResponse(self):
        """Check that parsing plain keys returned by format = keys works"""
        zot = z.Zotero("myuserid", "user", "myuserkey")
        zot.url_params = {"format": "keys"}
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserid/items?format=keys",
            content_type="text/plain",
            body=self.keys_response,
        )
        response = zot.items()
        self.assertEqual("JIFWQ4AN", response[:8].decode("utf-8"))

    @httpretty.activate
    def testParseItemVersionsResponse(self):
        """Check that parsing version dict returned by format = versions works"""
        zot = z.Zotero("myuserid", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserid/items?format=versions",
            content_type="application/json",
            body=self.item_versions,
        )
        iversions = zot.item_versions()
        self.assertEqual(iversions["RRK27C5F"], 4000)
        self.assertEqual(iversions["EAWCSKSF"], 4087)
        self.assertEqual(len(iversions), 2)

    @httpretty.activate
    def testParseCollectionVersionsResponse(self):
        """Check that parsing version dict returned by format = versions works"""
        zot = z.Zotero("myuserid", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserid/collections?format=versions",
            content_type="application/json",
            body=self.collection_versions,
        )
        iversions = zot.collection_versions()
        self.assertEqual(iversions["RRK27C5F"], 4000)
        self.assertEqual(iversions["EAWCSKSF"], 4087)
        self.assertEqual(len(iversions), 2)

    @httpretty.activate
    def testParseChildItems(self):
        """Try and parse child items"""
        zot = z.Zotero("myuserid", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserid/items/ABC123/children",
            content_type="application/json",
            body=self.items_doc,
        )
        items_data = zot.children("ABC123")
        self.assertEqual("NM66T6EF", items_data[0]["key"])

    @httpretty.activate
    def testCitUTF8(self):
        """Ensure that unicode citations are correctly processed by Pyzotero"""
        zot = z.Zotero("myuserID", "user", "myuserkey")
        url = "https://api.zotero.org/users/myuserID/items/GW8V2CK7"
        HTTPretty.register_uri(
            HTTPretty.GET,
            url,
            content_type="application/atom+xml",
            body=self.citation_doc,
        )
        cit = zot.item("GW8V2CK7", content="citation", style="chicago-author-date")
        self.assertEqual(cit[0], "<span>(Ans\\xe6lm and Tka\\u010dik 2014)</span>")

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
        """Should successfully return a single collection dict,
        'name' key value should match input doc's name value
        """
        zot = z.Zotero("myuserID", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserID/collections/KIMI8BSG",
            content_type="application/json",
            body=self.collection_doc,
        )
        collections_data = zot.collection("KIMI8BSG")
        self.assertEqual("LoC", collections_data["data"]["name"])

    @httpretty.activate
    def testParseCollectionTagsJSONDoc(self):
        """Should successfully return a list of tags,
        which should match input doc's number of tag items and 'tag' values
        """
        zot = z.Zotero("myuserID", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserID/collections/KIMI8BSG/tags",
            content_type="application/json",
            body=self.collection_tags,
        )
        collections_data = zot.collection_tags("KIMI8BSG")
        self.assertEqual(3, len(collections_data))
        for item in collections_data:
            self.assertTrue(item in ["apple", "banana", "cherry"])

    @httpretty.activate
    def testParseCollectionsJSONDoc(self):
        """Should successfully return a list of collection dicts, key should
        match input doc's zapi:key value, and 'title' value should match
        input doc's title value
        """
        zot = z.Zotero("myuserID", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserID/collections",
            content_type="application/json",
            body=self.collections_doc,
        )
        collections_data = zot.collections()
        self.assertEqual("LoC", collections_data[0]["data"]["name"])

    @httpretty.activate
    def testParseTagsJSON(self):
        """Should successfully return a list of tags"""
        zot = z.Zotero("myuserID", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserID/tags?limit=1",
            content_type="application/json",
            body=self.tags_doc,
        )
        tags_data = zot.tags()
        self.assertEqual("Community / Economic Development", tags_data[0])

    @httpretty.activate
    def testUrlBuild(self):
        """Ensure that URL parameters are successfully encoded by the http library"""
        zot = z.Zotero("myuserID", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserID/tags?limit=1",
            content_type="application/json",
            body=self.tags_doc,
        )
        _ = zot.tags(limit=1)
        # Check that all expected parameters are present
        url_str = str(zot.request.url)
        self.assertIn("locale=en-US", url_str)
        self.assertIn("limit=1", url_str)
        self.assertIn("format=json", url_str)
        self.assertTrue(
            url_str.startswith("https://api.zotero.org/users/myuserID/tags?")
        )

    @httpretty.activate
    def testParseLinkHeaders(self):
        """Should successfully parse link headers"""
        zot = z.Zotero("myuserID", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserID/tags?limit=1",
            content_type="application/json",
            body=self.tags_doc,
            adding_headers={
                "Link": '<https://api.zotero.org/users/436/items/top?limit=1&start=1>; rel="next", <https://api.zotero.org/users/436/items/top?limit=1&start=2319>; rel="last", <https://www.zotero.org/users/436/items/top>; rel="alternate"'
            },
        )
        zot.tags()
        self.assertEqual(zot.links["next"], "/users/436/items/top?limit=1&start=1")
        self.assertEqual(zot.links["last"], "/users/436/items/top?limit=1&start=2319")
        self.assertEqual(zot.links["alternate"], "/users/436/items/top")

    @httpretty.activate
    def testParseLinkHeadersPreservesAllParameters(self):
        """Test that the self link preserves all parameters, not just the first 2"""
        zot = z.Zotero("myuserID", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserID/items/top",
            content_type="application/json",
            body=self.items_doc,
            adding_headers={
                "Link": '<https://api.zotero.org/users/myuserID/items/top?start=1>; rel="next"'
            },
        )
        # Call with multiple parameters including limit
        zot.top(limit=1)
        # The self link should preserve all parameters except format
        self.assertIn("limit=1", zot.links["self"])
        self.assertIn("locale=", zot.links["self"])
        # format should be stripped
        self.assertNotIn("format=", zot.links["self"])

    @httpretty.activate
    def testParseGroupsJSONDoc(self):
        """Should successfully return a list of group dicts, ID should match
        input doc's zapi:key value, and 'total_items' value should match
        input doc's zapi:numItems value
        """
        zot = z.Zotero("myuserID", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserID/groups",
            content_type="application/json",
            body=self.groups_doc,
        )
        groups_data = zot.groups()
        self.assertEqual("smart_cities", groups_data[0]["data"]["name"])

    def testParamsReset(self):
        """Should preserve existing URL parameters when add_parameters is called multiple times"""
        zot = z.Zotero("myuserID", "user", "myuserkey")
        zot.add_parameters(start=5, limit=10)
        zot._build_query("/whatever")
        zot.add_parameters(start=2)
        # Should get default limit=100 since no limit specified in second call
        self.assertEqual(
            parse_qs(f"start=2&format=json&limit={DEFAULT_ITEM_LIMIT}"),
            parse_qs(urlencode(zot.url_params, doseq=True)),
        )

    @httpretty.activate
    def testParamsBlankAfterCall(self):
        """self.url_params should be blank after an API call"""
        zot = z.Zotero("myuserID", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserID/items",
            content_type="application/json",
            body=self.items_doc,
        )
        zot.items()
        self.assertEqual(None, zot.url_params)

    @httpretty.activate
    def testResponseForbidden(self):
        """Ensure that an error is properly raised for 403"""
        zot = z.Zotero("myuserID", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserID/items",
            content_type="application/json",
            body=self.items_doc,
            status=403,
        )
        with self.assertRaises(z.ze.UserNotAuthorisedError):
            zot.items()

    @httpretty.activate
    def testTimeout(self):
        """Ensure that an error is properly raised for 503"""
        zot = z.Zotero("myuserID", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserID/items",
            content_type="application/json",
            body=self.items_doc,
            status=503,
        )
        with self.assertRaises(z.ze.HTTPError):
            zot.items()

    @httpretty.activate
    def testResponseUnsupported(self):
        """Ensure that an error is properly raised for 400"""
        zot = z.Zotero("myuserID", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserID/items",
            content_type="application/json",
            body=self.items_doc,
            status=400,
        )
        with self.assertRaises(z.ze.UnsupportedParamsError):
            zot.items()

    @httpretty.activate
    def testResponseNotFound(self):
        """Ensure that an error is properly raised for 404"""
        zot = z.Zotero("myuserID", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserID/items",
            body=self.items_doc,
            content_type="application/json",
            status=404,
        )
        with self.assertRaises(z.ze.ResourceNotFoundError):
            zot.items()

    @httpretty.activate
    def testResponseMiscError(self):
        """Ensure that an error is properly raised for unspecified errors"""
        zot = z.Zotero("myuserID", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserID/items",
            content_type="application/json",
            body=self.items_doc,
            status=500,
        )
        with self.assertRaises(z.ze.HTTPError):
            zot.items()

    @httpretty.activate
    def testGetItems(self):
        """Ensure that we can retrieve a list of all items"""
        zot = z.Zotero("myuserID", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/itemTypes",
            content_type="application/json",
            body=self.item_types,
        )
        resp = zot.item_types()
        self.assertEqual(resp[0]["itemType"], "artwork")

    @httpretty.activate
    def testGetTemplate(self):
        """Ensure that item templates are retrieved and converted into dicts"""
        zot = z.Zotero("myuserID", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/items/new?itemType=book",
            content_type="application/json",
            body=self.item_templt,
        )
        t = zot.item_template("book")
        self.assertEqual("book", t["itemType"])

    def testCreateCollectionError(self):
        """Ensure that collection creation fails with the wrong dict"""
        zot = z.Zotero("myuserID", "user", "myuserkey")
        t = [{"foo": "bar"}]
        with self.assertRaises(z.ze.ParamNotPassedError):
            t = zot.create_collections(t)

    @httpretty.activate
    def testNoApiKey(self):
        """Ensure that pyzotero works when api_key is not set"""
        zot = z.Zotero("myuserID", "user")
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserID/items",
            content_type="application/json",
            body=self.item_doc,
        )
        items = zot.items()
        self.assertEqual(len(items), 6)  # this isn't a very good assertion

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
    def testCollectionCreation(self):
        """Tests creation of a new collection"""
        zot = z.Zotero("myuserID", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.POST,
            "https://api.zotero.org/users/myuserID/collections",
            body=self.creation_doc,
            content_type="application/json",
            status=200,
        )
        # now let's test something
        resp = zot.create_collections([{"name": "foo", "key": "ABC123"}])
        self.assertTrue("ABC123", resp["success"]["0"])
        request = httpretty.last_request()
        self.assertFalse("If-Unmodified-Since-Version" in request.headers)

    @httpretty.activate
    def testCollectionCreationLastModified(self):
        """Tests creation of a new collection with last_modified param"""
        zot = z.Zotero("myuserID", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.POST,
            "https://api.zotero.org/users/myuserID/collections",
            body=self.creation_doc,
            content_type="application/json",
            status=200,
        )
        # now let's test something
        resp = zot.create_collections(
            [{"name": "foo", "key": "ABC123"}], last_modified=5
        )
        self.assertEqual("ABC123", resp["success"]["0"])
        request = httpretty.last_request()
        self.assertEqual(request.headers["If-Unmodified-Since-Version"], "5")

    @httpretty.activate
    def testCollectionUpdate(self):
        """Tests update of a collection"""
        zot = z.Zotero("myuserID", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.PUT,
            "https://api.zotero.org/users/myuserID/collections/ABC123",
            body="",
            content_type="application/json",
            status=200,
        )
        # now let's test something
        resp = zot.update_collection({"name": "foo", "key": "ABC123", "version": 3})
        self.assertEqual(True, resp)
        request = httpretty.last_request()
        self.assertEqual(request.headers["If-Unmodified-Since-Version"], "3")

    @httpretty.activate
    def testCollectionUpdateLastModified(self):
        """Tests update of a collection with last_modified set"""
        zot = z.Zotero("myuserID", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.PUT,
            "https://api.zotero.org/users/myuserID/collections/ABC123",
            body="",
            content_type="application/json",
            status=200,
        )
        # now let's test something
        resp = zot.update_collection(
            {"name": "foo", "key": "ABC123", "version": 3}, last_modified=5
        )
        self.assertEqual(True, resp)
        request = httpretty.last_request()
        self.assertEqual(request.headers["If-Unmodified-Since-Version"], "5")

    @httpretty.activate
    def testItemCreation(self):
        """Tests creation of a new item using a template"""
        zot = z.Zotero("myuserID", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/items/new?itemType=book",
            body=self.item_templt,
            content_type="application/json",
        )
        template = zot.item_template("book")
        httpretty.reset()
        HTTPretty.register_uri(
            HTTPretty.POST,
            "https://api.zotero.org/users/myuserID/items",
            body=self.creation_doc,
            content_type="application/json",
            status=200,
        )
        # now let's test something
        resp = zot.create_items([template])
        self.assertEqual("ABC123", resp["success"]["0"])
        request = httpretty.last_request()
        self.assertFalse("If-Unmodified-Since-Version" in request.headers)

    @httpretty.activate
    def testItemCreationLastModified(self):
        """Checks 'If-Unmodified-Since-Version' header correctly set on create_items"""
        zot = z.Zotero("myuserID", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.POST,
            "https://api.zotero.org/users/myuserID/items",
            body=self.creation_doc,
            content_type="application/json",
            status=200,
        )
        # now let's test something
        zot.create_items([{"key": "ABC123"}], last_modified=5)
        request = httpretty.last_request()
        self.assertEqual(request.headers["If-Unmodified-Since-Version"], "5")

    @httpretty.activate
    def testItemUpdate(self):
        """Tests item update using update_item"""
        zot = z.Zotero("myuserID", "user", "myuserkey")
        update = {"key": "ABC123", "version": 3, "itemType": "book"}
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/itemFields",
            body=self.item_fields,
            content_type="application/json",
        )
        HTTPretty.register_uri(
            HTTPretty.PATCH,
            "https://api.zotero.org/users/myuserID/items/ABC123",
            body="",
            content_type="application/json",
            status=204,
        )
        # now let's test something
        resp = zot.update_item(update)
        self.assertEqual(resp, True)
        request = httpretty.last_request()
        self.assertEqual(request.headers["If-Unmodified-Since-Version"], "3")

    @httpretty.activate
    def testItemUpdateLastModified(self):
        """Tests item update using update_item with last_modified parameter"""
        zot = z.Zotero("myuserID", "user", "myuserkey")
        update = {"key": "ABC123", "version": 3, "itemType": "book"}
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/itemFields",
            body=self.item_fields,
            content_type="application/json",
        )
        HTTPretty.register_uri(
            HTTPretty.PATCH,
            "https://api.zotero.org/users/myuserID/items/ABC123",
            body="",
            content_type="application/json",
            status=204,
        )
        # now let's test something
        resp = zot.update_item(update, last_modified=5)
        self.assertEqual(resp, True)
        request = httpretty.last_request()
        self.assertEqual(request.headers["If-Unmodified-Since-Version"], "5")

    def testTooManyItems(self):
        """Should fail because we're passing too many items"""
        itms = [i for i in range(51)]
        zot = z.Zotero("myuserID", "user", "myuserkey")
        with self.assertRaises(z.ze.TooManyItemsError):
            zot.create_items(itms)

    @httpretty.activate
    def testRateLimitWithBackoff(self):
        """Test 429 response handling when a backoff header is received"""
        zot = z.Zotero("myuserID", "user", "myuserkey")
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserID/items",
            status=429,
            adding_headers={"backoff": 0.1},
        )
        zot.items()
        self.assertTrue(zot.backoff)

    @httpretty.activate
    def testDeleteTags(self):
        """Tests deleting tags"""
        zot = z.Zotero("myuserID", "user", "myuserkey")

        # Mock the initial request to get version info
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserID/tags?limit=1",
            content_type="application/json",
            body=self.tags_doc,
            adding_headers={"last-modified-version": "42"},
        )

        # Mock the delete endpoint
        HTTPretty.register_uri(
            HTTPretty.DELETE, "https://api.zotero.org/users/myuserID/tags", status=204
        )

        # Test tag deletion
        resp = zot.delete_tags("tag1", "tag2")

        # Verify the request
        request = httpretty.last_request()
        self.assertEqual(request.method, "DELETE")
        self.assertEqual(request.headers["If-Unmodified-Since-Version"], "42")
        self.assertTrue(resp)

    @httpretty.activate
    def testAddToCollection(self):
        """Tests adding an item to a collection"""
        zot = z.Zotero("myuserID", "user", "myuserkey")

        # Mock the PATCH endpoint for adding to collection
        HTTPretty.register_uri(
            HTTPretty.PATCH,
            "https://api.zotero.org/users/myuserID/items/ITEMKEY",
            status=204,
        )

        # Create a test item
        item = {"key": "ITEMKEY", "version": 5, "data": {"collections": []}}

        # Test adding to collection
        resp = zot.addto_collection("COLLECTIONKEY", item)

        # Verify the request
        request = httpretty.last_request()
        self.assertEqual(request.method, "PATCH")
        self.assertEqual(request.headers["If-Unmodified-Since-Version"], "5")

        # Check the body contains the collection key

        body = json.loads(request.body.decode("utf-8"))
        self.assertEqual(body["collections"], ["COLLECTIONKEY"])

        self.assertTrue(resp)

    @httpretty.activate
    def testDeleteItem(self):
        """Tests deleting an item"""
        zot = z.Zotero("myuserID", "user", "myuserkey")

        # Mock the DELETE endpoint
        HTTPretty.register_uri(
            HTTPretty.DELETE,
            "https://api.zotero.org/users/myuserID/items/ITEMKEY",
            status=204,
        )

        # Create a test item
        item = {"key": "ITEMKEY", "version": 7}

        # Test deletion
        resp = zot.delete_item(item)

        # Verify the request
        request = httpretty.last_request()
        self.assertEqual(request.method, "DELETE")
        self.assertEqual(request.headers["If-Unmodified-Since-Version"], "7")

        self.assertTrue(resp)

    @httpretty.activate
    def testDeleteMultipleItems(self):
        """Tests deleting multiple items at once"""
        zot = z.Zotero("myuserID", "user", "myuserkey")

        # Mock the DELETE endpoint for multiple items
        HTTPretty.register_uri(
            HTTPretty.DELETE, "https://api.zotero.org/users/myuserID/items", status=204
        )

        # Create test items
        items = [{"key": "ITEM1", "version": 5}, {"key": "ITEM2", "version": 3}]

        # Test deletion
        resp = zot.delete_item(items)

        # Verify the request
        request = httpretty.last_request()
        self.assertEqual(request.method, "DELETE")
        self.assertEqual(request.headers["If-Unmodified-Since-Version"], "5")

        # Extract and parse the query string
        parsed_url = urlparse(request.url)
        query_params = parse_qs(parsed_url.query)

        self.assertIn("itemKey", query_params)
        self.assertEqual(query_params["itemKey"][0], "ITEM1,ITEM2")

        self.assertTrue(resp)

    @httpretty.activate
    def testFileUpload(self):
        """Tests file upload process with attachments"""
        zot = z.Zotero("myuserID", "user", "myuserkey")

        # Create a temporary file for testing
        temp_file_path = os.path.join(self.cwd, "api_responses", "test_upload_file.txt")
        with open(temp_file_path, "w") as f:
            f.write("Test file content for upload")

        # Mock Step 0: Create preliminary item registration
        prelim_response = {"success": {"0": "ITEMKEY123"}}
        HTTPretty.register_uri(
            HTTPretty.POST,
            "https://api.zotero.org/users/myuserID/items",
            content_type="application/json",
            body=json.dumps(prelim_response),
            status=200,
        )

        # Create the upload payload
        payload = [
            {
                "filename": "test_upload_file.txt",
                "title": "Test File",
                "linkMode": "imported_file",
            }
        ]

        # Create mock auth data to be returned by _get_auth
        mock_auth_data = {
            "url": "https://uploads.zotero.org/",
            "params": {
                "key": "abcdef1234567890",
                "prefix": "prefix",
                "suffix": "suffix",
            },
            "uploadKey": "upload_key_123",
        }

        # Patch the necessary methods to avoid HTTP calls and file system checks
        with (
            patch.object(z.Zupload, "_verify", return_value=None),
            patch.object(z.Zupload, "_get_auth", return_value=mock_auth_data),
            patch.object(z.Zupload, "_upload_file", return_value=None),
        ):
            # Create the upload object and initiate upload
            upload = z.Zupload(
                zot, payload, basedir=os.path.join(self.cwd, "api_responses")
            )
            result = upload.upload()

            # Verify the result structure
            self.assertIn("success", result)
            self.assertIn("failure", result)
            self.assertIn("unchanged", result)
            self.assertEqual(len(result["success"]), 1)
            self.assertEqual(result["success"][0]["key"], "ITEMKEY123")

        # Clean up
        os.remove(temp_file_path)

    @httpretty.activate
    def testFileUploadExists(self):
        """Tests file upload process when the file already exists on the server"""
        zot = z.Zotero("myuserID", "user", "myuserkey")

        # Create a temporary file for testing
        temp_file_path = os.path.join(self.cwd, "api_responses", "test_upload_file.txt")
        with open(temp_file_path, "w") as f:
            f.write("Test file content for upload")

        # Mock Step 0: Create preliminary item registration
        prelim_response = {"success": {"0": "ITEMKEY123"}}
        HTTPretty.register_uri(
            HTTPretty.POST,
            "https://api.zotero.org/users/myuserID/items",
            content_type="application/json",
            body=json.dumps(prelim_response),
            status=200,
        )

        # Create the upload payload
        payload = [
            {
                "filename": "test_upload_file.txt",
                "title": "Test File",
                "linkMode": "imported_file",
            }
        ]

        # Create mock auth data to be returned by _get_auth with exists=True
        mock_auth_data = {"exists": True}

        # Patch the necessary methods to avoid HTTP calls and file system checks
        with (
            patch.object(z.Zupload, "_verify", return_value=None),
            patch.object(z.Zupload, "_get_auth", return_value=mock_auth_data),
        ):
            # Create the upload object and initiate upload
            upload = z.Zupload(
                zot, payload, basedir=os.path.join(self.cwd, "api_responses")
            )
            result = upload.upload()

            # Verify the result structure
            self.assertIn("success", result)
            self.assertIn("failure", result)
            self.assertIn("unchanged", result)
            self.assertEqual(len(result["unchanged"]), 1)
            self.assertEqual(result["unchanged"][0]["key"], "ITEMKEY123")

        # Clean up
        os.remove(temp_file_path)

    @httpretty.activate
    def testFileUploadWithParentItem(self):
        """Tests file upload process with a parent item ID"""
        zot = z.Zotero("myuserID", "user", "myuserkey")

        # Create a temporary file for testing
        temp_file_path = os.path.join(self.cwd, "api_responses", "test_upload_file.txt")
        with open(temp_file_path, "w") as f:
            f.write("Test file content for upload")

        # Mock Step 0: Create preliminary item registration
        prelim_response = {"success": {"0": "ITEMKEY123"}}
        HTTPretty.register_uri(
            HTTPretty.POST,
            "https://api.zotero.org/users/myuserID/items",
            content_type="application/json",
            body=json.dumps(prelim_response),
            status=200,
        )

        # Create the upload payload
        payload = [
            {
                "filename": "test_upload_file.txt",
                "title": "Test File",
                "linkMode": "imported_file",
            }
        ]

        # Test with parent ID
        parent_id = "PARENTITEM123"

        # Create mock auth data to be returned by _get_auth
        mock_auth_data = {
            "url": "https://uploads.zotero.org/",
            "params": {
                "key": "abcdef1234567890",
                "prefix": "prefix",
                "suffix": "suffix",
            },
            "uploadKey": "upload_key_123",
        }

        # Mock Step 1: Get upload authorization
        HTTPretty.register_uri(
            HTTPretty.POST,
            "https://api.zotero.org/users/myuserID/items/ITEMKEY123/file",
            content_type="application/json",
            body=json.dumps(mock_auth_data),
            status=200,
        )

        # Patch the necessary methods to avoid file system checks and skip the actual upload
        with (
            patch.object(z.Zupload, "_verify", return_value=None),
            patch.object(z.Zupload, "_upload_file", return_value=None),
        ):
            # Create the upload object with a parent ID and initiate upload
            upload = z.Zupload(
                zot,
                payload,
                parentid=parent_id,
                basedir=os.path.join(self.cwd, "api_responses"),
            )
            result = upload.upload()

            # Verify the result structure
            self.assertIn("success", result)
            self.assertEqual(len(result["success"]), 1)

            # Check that the parentItem was added to the payload
            # Get the latest request to the items endpoint
            requests = httpretty.latest_requests()
            item_request = None
            for req in requests:
                if req.url.endswith("/items"):
                    item_request = req
                    break

            self.assertIsNotNone(item_request, "No request found to the items endpoint")
            request_body = json.loads(item_request.body.decode("utf-8"))
            self.assertEqual(request_body[0]["parentItem"], parent_id)

        # Clean up
        os.remove(temp_file_path)

    @httpretty.activate
    def testFileUploadFailure(self):
        """Tests file upload process when auth step fails"""
        zot = z.Zotero("myuserID", "user", "myuserkey")

        # Create a temporary file for testing
        temp_file_path = os.path.join(self.cwd, "api_responses", "test_upload_file.txt")
        with open(temp_file_path, "w") as f:
            f.write("Test file content for upload")

        # Mock Step 0: Create preliminary item registration
        prelim_response = {"success": {"0": "ITEMKEY123"}}
        HTTPretty.register_uri(
            HTTPretty.POST,
            "https://api.zotero.org/users/myuserID/items",
            content_type="application/json",
            body=json.dumps(prelim_response),
            status=200,
        )

        # Mock Step 1: Authorization fails with 403
        HTTPretty.register_uri(
            HTTPretty.POST,
            "https://api.zotero.org/users/myuserID/items/ITEMKEY123/file",
            status=403,
        )

        # Create the upload payload
        payload = [
            {
                "filename": "test_upload_file.txt",
                "title": "Test File",
                "linkMode": "imported_file",
            }
        ]

        # Patch just the _verify method to avoid file system checks, but allow the real HTTP calls
        with patch.object(z.Zupload, "_verify", return_value=None):
            # Create the upload object and test for exception
            upload = z.Zupload(
                zot, payload, basedir=os.path.join(self.cwd, "api_responses")
            )

            # This should raise an error due to 403 status
            with self.assertRaises(z.ze.UserNotAuthorisedError):
                upload.upload()

        # Clean up
        os.remove(temp_file_path)

    @httpretty.activate
    def testFileUploadWithPreexistingKeys(self):
        """Tests file upload process when the payload already contains keys"""
        zot = z.Zotero("myuserID", "user", "myuserkey")

        # Create a temporary file for testing
        temp_file_path = os.path.join(self.cwd, "api_responses", "test_upload_file.txt")
        with open(temp_file_path, "w") as f:
            f.write("Test file content for upload")

        # Create the upload payload with preexisting key
        payload = [
            {
                "key": "PREEXISTING123",
                "filename": "test_upload_file.txt",
                "title": "Test File",
                "linkMode": "imported_file",
            }
        ]

        # Create mock auth data to be returned by _get_auth
        mock_auth_data = {
            "url": "https://uploads.zotero.org/",
            "params": {
                "key": "abcdef1234567890",
                "prefix": "prefix",
                "suffix": "suffix",
            },
            "uploadKey": "upload_key_123",
        }

        # Patch the necessary methods to avoid HTTP calls and file system checks
        with (
            patch.object(z.Zupload, "_verify", return_value=None),
            patch.object(z.Zupload, "_get_auth", return_value=mock_auth_data),
            patch.object(z.Zupload, "_upload_file", return_value=None),
        ):
            # Create the upload object and initiate upload
            upload = z.Zupload(
                zot, payload, basedir=os.path.join(self.cwd, "api_responses")
            )
            result = upload.upload()

            # Verify the result structure
            self.assertIn("success", result)
            self.assertEqual(len(result["success"]), 1)
            self.assertEqual(result["success"][0]["key"], "PREEXISTING123")

            # No need to check for endpoint calls since we're patching the methods

        # Clean up
        os.remove(temp_file_path)

    @httpretty.activate
    def testFileUploadInvalidPayload(self):
        """Tests file upload process with invalid payload mixing items with and without keys"""
        zot = z.Zotero("myuserID", "user", "myuserkey")

        # Create a temporary file for testing
        temp_file_path = os.path.join(self.cwd, "api_responses", "test_upload_file.txt")
        with open(temp_file_path, "w") as f:
            f.write("Test file content for upload")

        # Create the invalid upload payload (mixing items with and without keys)
        payload = [
            {"key": "PREEXISTING123", "filename": "test_upload_file.txt"},
            {"filename": "test_upload_file.txt"},  # No key
        ]

        # Patch the _verify method to avoid file system checks
        with patch.object(z.Zupload, "_verify", return_value=None):
            # Create the upload object and test for exception
            upload = z.Zupload(
                zot, payload, basedir=os.path.join(self.cwd, "api_responses")
            )

            # This should raise an UnsupportedParamsError
            with self.assertRaises(z.ze.UnsupportedParamsError):
                upload.upload()

        # Clean up
        os.remove(temp_file_path)

    @httpretty.activate
    def testAttachmentSimple(self):
        """Test attachment_simple method with a single file"""
        zot = z.Zotero("myuserID", "user", "myuserkey")

        # Create a temporary test file
        temp_file_path = os.path.join(self.cwd, "api_responses", "test_attachment.txt")
        with open(temp_file_path, "w") as f:
            f.write("Test attachment content")

        # Mock the item template response
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/items/new?itemType=attachment&linkMode=imported_file",
            content_type="application/json",
            body=json.dumps({"itemType": "attachment", "linkMode": "imported_file"}),
        )

        # Mock the item creation response
        HTTPretty.register_uri(
            HTTPretty.POST,
            "https://api.zotero.org/users/myuserID/items",
            content_type="application/json",
            body=json.dumps({"success": {"0": "ITEMKEY123"}}),
        )

        # Patch the necessary methods to avoid HTTP calls and file system checks
        with (
            patch.object(z.Zupload, "_verify", return_value=None),
            patch.object(
                z.Zupload,
                "_get_auth",
                return_value={
                    "url": "https://uploads.zotero.org/",
                    "params": {"key": "abcdef1234567890"},
                    "uploadKey": "upload_key_123",
                },
            ),
            patch.object(z.Zupload, "_upload_file", return_value=None),
        ):
            # Test attachment_simple with a single file
            result = zot.attachment_simple([temp_file_path])

            # Verify the result structure
            self.assertIn("success", result)
            self.assertEqual(len(result["success"]), 1)

            # Verify that the correct attachment template was used
            request = httpretty.last_request()
            payload = json.loads(request.body.decode("utf-8"))
            self.assertEqual(payload[0]["title"], "test_attachment.txt")
            self.assertEqual(payload[0]["filename"], temp_file_path)

        # Clean up
        os.remove(temp_file_path)

    @httpretty.activate
    def testAttachmentSimpleWithParent(self):
        """Test attachment_simple method with a parent ID"""
        zot = z.Zotero("myuserID", "user", "myuserkey")

        # Create a temporary test file
        temp_file_path = os.path.join(self.cwd, "api_responses", "test_attachment.txt")
        with open(temp_file_path, "w") as f:
            f.write("Test attachment content")

        # Mock the item template response
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/items/new?itemType=attachment&linkMode=imported_file",
            content_type="application/json",
            body=json.dumps({"itemType": "attachment", "linkMode": "imported_file"}),
        )

        # Patch the _attachment method to verify it's called correctly
        with patch.object(z.Zotero, "_attachment") as mock_attachment:
            # Set up the mock return value
            mock_attachment.return_value = {"success": [{"key": "ITEMKEY123"}]}

            # Test attachment_simple with a parent ID
            result = zot.attachment_simple([temp_file_path], parentid="PARENT123")

            # Verify the result structure matches the mock return value
            self.assertEqual(result, {"success": [{"key": "ITEMKEY123"}]})

            # Check that _attachment was called with the parent ID
            mock_attachment.assert_called_once()
            args = mock_attachment.call_args[0]
            # First argument is the templates list, second is parent ID
            self.assertEqual(len(args), 2)
            self.assertEqual(args[1], "PARENT123")

            # Verify the template was correctly set up
            templates = args[0]
            self.assertEqual(len(templates), 1)
            self.assertEqual(templates[0]["title"], "test_attachment.txt")
            self.assertEqual(templates[0]["filename"], temp_file_path)

        # Clean up
        os.remove(temp_file_path)

    @httpretty.activate
    def testAttachmentBoth(self):
        """Test attachment_both method with custom title and filename"""
        zot = z.Zotero("myuserID", "user", "myuserkey")

        # Create a temporary test file
        temp_file_path = os.path.join(self.cwd, "api_responses", "test_attachment.txt")
        with open(temp_file_path, "w") as f:
            f.write("Test attachment content")

        # Mock the item template response
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/items/new?itemType=attachment&linkMode=imported_file",
            content_type="application/json",
            body=json.dumps({"itemType": "attachment", "linkMode": "imported_file"}),
        )

        # Mock the item creation response
        HTTPretty.register_uri(
            HTTPretty.POST,
            "https://api.zotero.org/users/myuserID/items",
            content_type="application/json",
            body=json.dumps({"success": {"0": "ITEMKEY123"}}),
        )

        # Patch the necessary methods to avoid HTTP calls and file system checks
        with (
            patch.object(z.Zupload, "_verify", return_value=None),
            patch.object(
                z.Zupload,
                "_get_auth",
                return_value={
                    "url": "https://uploads.zotero.org/",
                    "params": {"key": "abcdef1234567890"},
                    "uploadKey": "upload_key_123",
                },
            ),
            patch.object(z.Zupload, "_upload_file", return_value=None),
        ):
            # Test attachment_both with custom title
            custom_title = "Custom Attachment Title"
            files = [(custom_title, temp_file_path)]
            result = zot.attachment_both(files)

            # Verify the result structure
            self.assertIn("success", result)
            self.assertEqual(len(result["success"]), 1)

            # Verify that the correct attachment template was used
            request = httpretty.last_request()
            payload = json.loads(request.body.decode("utf-8"))
            self.assertEqual(payload[0]["title"], custom_title)
            self.assertEqual(payload[0]["filename"], temp_file_path)

        # Clean up
        os.remove(temp_file_path)

    @httpretty.activate
    def testAttachmentBothWithParent(self):
        """Test attachment_both method with a parent ID"""
        zot = z.Zotero("myuserID", "user", "myuserkey")

        # Create a temporary test file
        temp_file_path = os.path.join(self.cwd, "api_responses", "test_attachment.txt")
        with open(temp_file_path, "w") as f:
            f.write("Test attachment content")

        # Mock the item template response
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/items/new?itemType=attachment&linkMode=imported_file",
            content_type="application/json",
            body=json.dumps({"itemType": "attachment", "linkMode": "imported_file"}),
        )

        # Patch the _attachment method to verify it's called correctly
        with patch.object(z.Zotero, "_attachment") as mock_attachment:
            # Set up the mock return value
            mock_attachment.return_value = {"success": [{"key": "ITEMKEY123"}]}

            # Test attachment_both with a parent ID
            custom_title = "Custom Attachment Title"
            files = [(custom_title, temp_file_path)]
            result = zot.attachment_both(files, parentid="PARENT123")

            # Verify the result structure matches the mock return value
            self.assertEqual(result, {"success": [{"key": "ITEMKEY123"}]})

            # Check that _attachment was called with the parent ID
            mock_attachment.assert_called_once()
            args = mock_attachment.call_args[0]
            # First argument is the templates list, second is parent ID
            self.assertEqual(len(args), 2)
            self.assertEqual(args[1], "PARENT123")

            # Verify the template was correctly set up
            templates = args[0]
            self.assertEqual(len(templates), 1)
            self.assertEqual(templates[0]["title"], custom_title)
            self.assertEqual(templates[0]["filename"], temp_file_path)

        # Clean up
        os.remove(temp_file_path)

    def tearDown(self):
        """Tear stuff down"""
        HTTPretty.disable()

    @httpretty.activate
    def test_updated_template_comparison(self):
        """Test that ONE_HOUR is properly used for template freshness check"""
        zot = z.Zotero("myuserID", "user", "myuserkey")

        # Test that ONE_HOUR constant matches code expectation
        self.assertEqual(z.ONE_HOUR, 3600)

        # Use a simplified approach to test checking template freshness
        zot.templates = {}

        # Create a template
        template_name = "test_template"
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserID/items/new",
            body=json.dumps({"success": True}),
            content_type="application/json",
        )

        # The _cache method should create a template with a timestamp
        zot._cache(MagicMock(json=lambda: {"data": "test"}), template_name)

        # Verify template was created with a timestamp
        self.assertIn(template_name, zot.templates)
        self.assertIn("updated", zot.templates[template_name])

    @httpretty.activate
    def test_template_cache_creation(self):
        """Test template caching in the _cache method"""
        zot = z.Zotero("myuserID", "user", "myuserkey")

        # Create a mock response to cache
        mock_response = MagicMock()
        mock_response.json.return_value = {"test": "data"}

        # Call the _cache method
        template_name = "test_key"
        result = zot._cache(mock_response, template_name)

        # Verify the template was stored correctly
        self.assertIn(template_name, zot.templates)
        self.assertEqual(zot.templates[template_name]["tmplt"], {"test": "data"})
        self.assertIn("updated", zot.templates[template_name])

        # Verify the return value is a deep copy
        self.assertEqual(result, {"test": "data"})

        # Modify the returned data and check it doesn't affect the cached template
        result["modified"] = True
        self.assertNotIn("modified", zot.templates[template_name]["tmplt"])

    @httpretty.activate
    def test_striplocal_local_mode(self):
        """Test _striplocal method in local mode"""
        zot = z.Zotero("myuserID", "user", "myuserkey", local=True)

        # Test stripping local API path
        url = "http://localhost:23119/api/users/myuserID/items"
        result = zot._striplocal(url)
        self.assertEqual(result, "http://localhost:23119/users/myuserID/items")

        # Test with more complex path
        url = "http://localhost:23119/api/users/myuserID/collections/ABC123/items"
        result = zot._striplocal(url)
        self.assertEqual(
            result, "http://localhost:23119/users/myuserID/collections/ABC123/items"
        )

    @httpretty.activate
    def test_striplocal_remote_mode(self):
        """Test _striplocal method in remote mode (shouldn't change URL)"""
        zot = z.Zotero("myuserID", "user", "myuserkey", local=False)

        # Test without changing URL in remote mode
        url = "https://api.zotero.org/users/myuserID/items"
        result = zot._striplocal(url)
        self.assertEqual(result, url)

    @httpretty.activate
    def test_set_fulltext(self):
        """Test set_fulltext method for setting full-text data"""
        zot = z.Zotero("myuserID", "user", "myuserkey")

        # Mock response from Zotero API
        HTTPretty.register_uri(
            HTTPretty.PUT,
            "https://api.zotero.org/users/myuserID/items/ABCD1234/fulltext",
            status=204,
        )

        # Test with PDF data
        pdf_payload = {
            "content": "This is the full text content",
            "indexedPages": 5,
            "totalPages": 10,
        }

        _ = zot.set_fulltext("ABCD1234", pdf_payload)

        # Verify the request
        request = httpretty.last_request()
        self.assertEqual(request.method, "PUT")
        self.assertEqual(json.loads(request.body.decode()), pdf_payload)
        self.assertEqual(request.headers["Content-Type"], "application/json")

    @httpretty.activate
    def test_new_fulltext(self):
        """Test new_fulltext method for retrieving newer full-text content"""
        zot = z.Zotero("myuserID", "user", "myuserkey")

        # Mock response from Zotero API
        mock_response = {
            "ITEM1": {"version": 123, "indexedPages": 10, "totalPages": 10},
            "ITEM2": {"version": 456, "indexedChars": 5000, "totalChars": 5000},
        }

        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserID/fulltext",
            body=json.dumps(mock_response),
            content_type="application/json",
        )

        # Set up a mock for the request attribute
        zot.request = MagicMock()
        zot.request.headers = {}

        # Test the new_fulltext method
        result = zot.new_fulltext(since=5)

        # Verify the result
        self.assertEqual(result, mock_response)

        # Check that the correct parameters were sent
        request = httpretty.last_request()
        self.assertEqual(request.querystring.get("since"), ["5"])

    @httpretty.activate
    def test_last_modified_version(self):
        """Test the last_modified_version method"""
        zot = z.Zotero("myuserID", "user", "myuserkey")

        # Mock the response with a last-modified-version header
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserID/items",
            body=self.items_doc,
            content_type="application/json",
            adding_headers={"last-modified-version": "1234"},
        )

        # Test retrieving the last modified version
        version = zot.last_modified_version()

        # Verify the result
        self.assertEqual(version, 1234)

    def test_makeiter(self):
        """Test the makeiter method that wraps iterfollow"""
        zot = z.Zotero("myuserID", "user", "myuserkey")

        # Create a mock method that returns items
        # This is a better approach than trying to test the generator directly
        mock_items = [{"key": "ITEM1"}, {"key": "ITEM2"}]

        with patch.object(zot, "iterfollow") as mock_iterfollow:
            # Set up the mock to return our test items
            mock_iterfollow.return_value = iter([mock_items])

            # Test makeiter which wraps the iterfollow generator
            # Set links manually since we're not actually calling the API
            zot.links = {"self": "/test", "next": "/test?start=5"}

            # This should call iterfollow internally
            result = zot.makeiter(lambda: None)

            # Verify makeiter sets the 'next' link to the 'self' link
            self.assertEqual(zot.links["next"], zot.links["self"])

            # Verify makeiter returns an iterable
            self.assertTrue(hasattr(result, "__iter__"))

            # Verify the mock was called
            mock_iterfollow.assert_called_once()

    def test_makeiter_preserves_limit_parameter(self):
        """Test that makeiter preserves the limit parameter in the self link"""
        zot = z.Zotero("myuserID", "user", "myuserkey")

        # Simulate a self link with multiple parameters including limit
        # This mimics what _extract_links() creates
        test_self_link = "/users/myuserID/items/top?limit=1&locale=en-US"
        zot.links = {
            "self": test_self_link,
            "next": "/users/myuserID/items/top?start=1",
        }

        # Call makeiter (with a dummy function since we're testing link manipulation)
        with patch.object(zot, "iterfollow"):
            zot.makeiter(lambda: None)

        # Verify that the 'next' link was set to 'self' and still contains limit parameter
        self.assertEqual(zot.links["next"], test_self_link)
        self.assertIn("limit=1", zot.links["next"])
        self.assertIn("locale=en-US", zot.links["next"])

    @httpretty.activate
    def test_publications_user(self):
        """Test the publications method for user libraries"""
        zot = z.Zotero("myuserID", "user", "myuserkey")

        # Mock the API response
        HTTPretty.register_uri(
            HTTPretty.GET,
            "https://api.zotero.org/users/myuserID/publications/items",
            body=self.items_doc,
            content_type="application/json",
        )

        # Get publications
        items = zot.publications()

        # Verify the result
        self.assertEqual(items[0]["key"], "NM66T6EF")

    def test_publications_group(self):
        """Test that publications method raises error for group libraries"""
        zot = z.Zotero("myGroupID", "group", "myuserkey")

        # Publications API endpoint doesn't exist for groups
        with self.assertRaises(z.ze.CallDoesNotExistError):
            zot.publications()

    def test_timezone_behavior_pytz_vs_whenever(self):
        """Test that whenever implementation produces equivalent timezone behavior to pytz"""

        # Test the old pytz behavior (what we were doing before)
        old_dt = datetime.datetime.now(datetime.timezone.utc).replace(
            tzinfo=pytz.timezone("GMT")
        )

        # Test the current whenever behavior
        current_dt = whenever.ZonedDateTime.now("GMT").py_datetime()

        # Assert that both produce GMT timezone
        self.assertEqual(old_dt.tzinfo.zone, "GMT")
        self.assertEqual(current_dt.tzinfo.tzname(None), "GMT")

        # Assert that timezone names are equivalent
        self.assertEqual(old_dt.tzinfo.zone, current_dt.tzinfo.tzname(None))

    def test_timezone_behavior_instant_vs_zoned(self):
        """Test that ZonedDateTime produces correct GMT while Instant produces UTC"""
        # Test Instant behavior (should be UTC)
        instant_dt = whenever.Instant.now().py_datetime()

        # Test ZonedDateTime behavior (should be GMT)
        zoned_dt = whenever.ZonedDateTime.now("GMT").py_datetime()

        # Assert timezone differences
        self.assertEqual(instant_dt.tzinfo.tzname(None), "UTC")
        self.assertEqual(zoned_dt.tzinfo.tzname(None), "GMT")

        # Assert they are different timezone implementations
        self.assertNotEqual(
            instant_dt.tzinfo.tzname(None), zoned_dt.tzinfo.tzname(None)
        )


if __name__ == "__main__":
    unittest.main()
