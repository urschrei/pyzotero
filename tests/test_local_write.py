"""
Tests for local API write support (#344).

This file is part of Pyzotero.
"""

import json
import os
import unittest
from unittest.mock import patch

import httpx2

from pyzotero import errors as ze
from pyzotero import zotero as z
from pyzotero._helpers import get_zotero_client

from .mock_client import MockClient

LOCAL = "http://localhost:23119/api"
SERVER_ID = "Teu5iBeFPFcF"


def local_zotero(mock, **kwargs):
    """Return a Zotero instance in local mode, backed by the mock client."""
    return z.Zotero("0", "user", local=True, client=mock.client, **kwargs)


class ServerIDTests(unittest.TestCase):
    """Caching, sending and validating Zotero-Server-ID."""

    def test_server_id_starts_unset(self):
        zot = local_zotero(MockClient())
        self.assertIsNone(zot.server_id)

    def test_server_id_captured_from_read(self):
        """Every local response carries the header, so reads populate it free"""
        mock = MockClient()
        mock.register(
            "GET",
            f"{LOCAL}/users/0/items",
            body="[]",
            headers={"Zotero-Server-ID": SERVER_ID},
        )
        zot = local_zotero(mock)
        zot.items()
        self.assertEqual(zot.server_id, SERVER_ID)

    def test_server_id_sent_on_subsequent_reads(self):
        mock = MockClient()
        mock.register(
            "GET",
            f"{LOCAL}/users/0/items",
            body="[]",
            headers={"Zotero-Server-ID": SERVER_ID},
        )
        zot = local_zotero(mock)
        zot.items()
        self.assertNotIn("Zotero-Server-ID", mock.requests[0].headers)
        zot.items()
        self.assertEqual(mock.requests[1].headers["Zotero-Server-ID"], SERVER_ID)

    def test_supplied_server_id_sent_from_the_start(self):
        """A caller that persisted the ID doesn't need the bootstrap round-trip"""
        mock = MockClient()
        mock.register("GET", f"{LOCAL}/users/0/items", body="[]")
        zot = local_zotero(mock, server_id=SERVER_ID)
        zot.items()
        self.assertEqual(mock.requests[0].headers["Zotero-Server-ID"], SERVER_ID)

    def test_server_id_is_writable(self):
        zot = local_zotero(MockClient())
        zot.server_id = SERVER_ID
        self.assertEqual(zot.server_id, SERVER_ID)
        zot.server_id = None
        self.assertIsNone(zot.server_id)

    def test_server_id_rejects_non_string(self):
        zot = local_zotero(MockClient())
        with self.assertRaises(TypeError):
            zot.server_id = 12345

    def test_captured_id_is_not_overwritten(self):
        """A cached ID wins: a mismatch is the server's to reject, not ours to absorb"""
        mock = MockClient()
        mock.register(
            "GET",
            f"{LOCAL}/users/0/items",
            body="[]",
            headers={"Zotero-Server-ID": "DIFFERENT"},
        )
        zot = local_zotero(mock, server_id=SERVER_ID)
        zot.items()
        self.assertEqual(zot.server_id, SERVER_ID)

    def test_no_local_headers_in_web_mode(self):
        mock = MockClient()
        mock.register(
            "GET",
            "https://api.zotero.org/users/myuserID/items",
            body="[]",
            headers={"Zotero-Server-ID": SERVER_ID},
        )
        zot = z.Zotero("myuserID", "user", "myuserkey", client=mock.client)
        zot.items()
        self.assertIsNone(zot.server_id)
        zot.items()
        self.assertNotIn("Zotero-Server-ID", mock.requests[1].headers)


class EnsureServerIDTests(unittest.TestCase):
    """Bootstrapping the ID before a write."""

    def test_bootstrap_uses_trailing_slash(self):
        """The bare /api path 404s; the endpoint carrying the header is /api/"""
        mock = MockClient()
        mock.register(
            "GET",
            f"{LOCAL}/",
            body="Nothing to see here.",
            content_type="text/plain",
            headers={"Zotero-Server-ID": SERVER_ID},
        )
        zot = local_zotero(mock)
        self.assertEqual(zot._ensure_server_id(), SERVER_ID)
        self.assertEqual(mock.requests[0].url, f"{LOCAL}/")

    def test_bootstrap_is_skipped_when_known(self):
        mock = MockClient()
        zot = local_zotero(mock, server_id=SERVER_ID)
        self.assertEqual(zot._ensure_server_id(), SERVER_ID)
        self.assertEqual(mock.requests, [])

    def test_bootstrap_without_header_raises(self):
        """A Zotero without write support returns no ID; say so rather than 428"""
        mock = MockClient()
        mock.register(
            "GET", f"{LOCAL}/", body="Nothing to see here.", content_type="text/plain"
        )
        zot = local_zotero(mock)
        with self.assertRaises(ze.UnsupportedParamsError) as caught:
            zot._ensure_server_id()
        self.assertIn("Zotero-Server-ID", str(caught.exception))


class AuthorizeLocalTests(unittest.TestCase):
    """POST /api/local/authorize."""

    def setUp(self):
        self.mock = MockClient()
        self.zot = local_zotero(self.mock, server_id=SERVER_ID)

    def register_authorize(self, body, status=200, content_type="application/json"):
        self.mock.register(
            "POST",
            f"{LOCAL}/local/authorize",
            body=body,
            status=status,
            content_type=content_type,
        )

    def test_authorize_sends_app_name_and_stores_key(self):
        self.register_authorize(json.dumps({"key": "abc123", "remember": True}))
        result = self.zot.authorize_local("Pyzotero test")
        self.assertEqual(result, {"key": "abc123", "remember": True})
        self.assertEqual(self.zot.local_api_key, "abc123")
        request = self.mock.requests[0]
        self.assertEqual(request.json(), {"appName": "Pyzotero test"})
        self.assertEqual(request.headers["Zotero-Server-ID"], SERVER_ID)

    def test_authorize_requires_server_id(self):
        """The authorize endpoint validates the header like any other write"""
        mock = MockClient()
        mock.register(
            "GET",
            f"{LOCAL}/",
            body="",
            content_type="text/plain",
            headers={"Zotero-Server-ID": SERVER_ID},
        )
        mock.register(
            "POST",
            f"{LOCAL}/local/authorize",
            body=json.dumps({"key": "abc123", "remember": False}),
        )
        zot = local_zotero(mock)
        zot.authorize_local("Pyzotero test")
        self.assertEqual(mock.requests[1].headers["Zotero-Server-ID"], SERVER_ID)

    def test_single_use_key_is_reported(self):
        self.register_authorize(json.dumps({"key": "abc123", "remember": False}))
        self.assertFalse(self.zot.authorize_local("Pyzotero test")["remember"])

    def test_denial_raises(self):
        self.register_authorize(json.dumps({"denied": True}), status=403)
        with self.assertRaises(ze.LocalAPIDeniedError):
            self.zot.authorize_local("Pyzotero test")

    def test_rate_limit_raises_rather_than_parsing_text_as_json(self):
        self.mock.register(
            "POST",
            f"{LOCAL}/local/authorize",
            body="Too many authorization requests",
            status=429,
            content_type="text/plain",
            headers={"Retry-After": "42"},
        )
        with self.assertRaises(ze.TooManyRequestsError) as caught:
            self.zot.authorize_local("Pyzotero test")
        self.assertIn("42", str(caught.exception))

    def test_blank_app_name_rejected(self):
        with self.assertRaises(ze.ParamNotPassedError):
            self.zot.authorize_local("   ")

    def test_authorize_rejected_in_web_mode(self):
        zot = z.Zotero("myuserID", "user", "myuserkey", client=MockClient().client)
        with self.assertRaises(ze.UnsupportedParamsError):
            zot.authorize_local("Pyzotero test")


class WriteHeaderTests(unittest.TestCase):
    """Headers injected into local writes."""

    def test_write_sends_server_id_and_key(self):
        mock = MockClient()
        mock.register(
            "POST",
            f"{LOCAL}/users/0/collections",
            body=json.dumps({"success": {"0": "COLLKEY"}}),
        )
        zot = local_zotero(mock, server_id=SERVER_ID, local_api_key="abc123")
        zot.create_collections([{"name": "Test"}])
        headers = mock.requests[0].headers
        self.assertEqual(headers["Zotero-Server-ID"], SERVER_ID)
        self.assertEqual(headers["Zotero-API-Key"], "abc123")

    def test_write_preserves_method_headers(self):
        mock = MockClient()
        mock.register("PATCH", f"{LOCAL}/users/0/items/ITEMKEY", body="", status=204)
        zot = local_zotero(mock, server_id=SERVER_ID, local_api_key="abc123")
        zot.addto_collection(
            "COLLKEY",
            {"key": "ITEMKEY", "version": 7, "data": {"collections": []}},
        )
        headers = mock.requests[0].headers
        self.assertEqual(headers["If-Unmodified-Since-Version"], "7")
        self.assertEqual(headers["Zotero-Server-ID"], SERVER_ID)

    def test_write_bootstraps_server_id_first(self):
        mock = MockClient()
        mock.register(
            "GET",
            f"{LOCAL}/",
            body="",
            content_type="text/plain",
            headers={"Zotero-Server-ID": SERVER_ID},
        )
        mock.register(
            "POST",
            f"{LOCAL}/users/0/collections",
            body=json.dumps({"success": {"0": "COLLKEY"}}),
        )
        zot = local_zotero(mock, local_api_key="abc123")
        zot.create_collections([{"name": "Test"}])
        self.assertEqual(mock.requests[0].url, f"{LOCAL}/")
        self.assertEqual(mock.requests[1].headers["Zotero-Server-ID"], SERVER_ID)

    def test_no_key_header_when_none_set(self):
        """A missing key is the server's to reject, so the error is the same
        whether the key is absent or expired
        """
        mock = MockClient()
        mock.register(
            "POST",
            f"{LOCAL}/users/0/collections",
            body=json.dumps({"success": {"0": "COLLKEY"}}),
        )
        zot = local_zotero(mock, server_id=SERVER_ID)
        zot.create_collections([{"name": "Test"}])
        self.assertNotIn("Zotero-API-Key", mock.requests[0].headers)

    def test_web_writes_are_untouched(self):
        mock = MockClient()
        mock.register(
            "POST",
            "https://api.zotero.org/users/myuserID/collections",
            body=json.dumps({"success": {"0": "COLLKEY"}}),
        )
        zot = z.Zotero("myuserID", "user", "myuserkey", client=mock.client)
        zot.create_collections([{"name": "Test"}])
        headers = mock.requests[0].headers
        self.assertNotIn("Zotero-Server-ID", headers)
        self.assertNotIn("Zotero-API-Key", headers)


class UploadTests(unittest.TestCase):
    """The upload receiver is a local API endpoint, unlike S3."""

    def test_upload_step_two_sends_server_id_when_local(self):
        mock = MockClient()
        zot = local_zotero(mock, server_id=SERVER_ID, local_api_key="abc123")
        authdata = {
            "url": f"{LOCAL}/local/uploads/UPLOADKEY",
            "params": {"key": "abcdef1234567890"},
            "uploadKey": "UPLOADKEY",
        }
        upload = z.Zupload(zot, [{"filename": __file__}])
        with (
            patch.object(
                httpx2,
                "post",
                return_value=httpx2.Response(
                    201, request=httpx2.Request("POST", authdata["url"])
                ),
            ) as mock_post,
            patch.object(z.Zupload, "_register_upload", return_value=None),
        ):
            upload._upload_file(authdata, __file__, "ITEMKEY")
        self.assertEqual(
            mock_post.call_args.kwargs["headers"]["Zotero-Server-ID"], SERVER_ID
        )
        # the receiver doesn't authenticate, so no key is leaked to it
        self.assertNotIn("Zotero-API-Key", mock_post.call_args.kwargs["headers"])

    def test_upload_step_two_stays_bare_for_web(self):
        mock = MockClient()
        zot = z.Zotero("myuserID", "user", "myuserkey", client=mock.client)
        authdata = {
            "url": "https://uploads.zotero.org/",
            "params": {"key": "abcdef1234567890"},
            "uploadKey": "UPLOADKEY",
        }
        upload = z.Zupload(zot, [{"filename": __file__}])
        with (
            patch.object(
                httpx2,
                "post",
                return_value=httpx2.Response(
                    201, request=httpx2.Request("POST", authdata["url"])
                ),
            ) as mock_post,
            patch.object(z.Zupload, "_register_upload", return_value=None),
        ):
            upload._upload_file(authdata, __file__, "ITEMKEY")
        self.assertEqual(list(mock_post.call_args.kwargs["headers"]), ["User-Agent"])


class ErrorMappingTests(unittest.TestCase):
    """401, 412 and 428 each cover more than one condition."""

    def write(self, status, body):
        mock = MockClient()
        mock.register(
            "POST",
            f"{LOCAL}/users/0/collections",
            body=body,
            status=status,
            content_type="text/plain",
        )
        zot = local_zotero(mock, server_id=SERVER_ID, local_api_key="abc123")
        zot.create_collections([{"name": "Test"}])

    def test_missing_key_raises_local_key_error(self):
        with self.assertRaises(ze.LocalAPIKeyRequiredError) as caught:
            self.write(
                401, "API key required -- POST /api/local/authorize to obtain one"
            )
        self.assertIn("authorize_local()", str(caught.exception))

    def test_expired_key_raises_local_key_error(self):
        with self.assertRaises(ze.LocalAPIKeyRequiredError):
            self.write(401, "Invalid or expired API key")

    def test_local_key_error_is_still_a_user_not_authorised_error(self):
        with self.assertRaises(ze.UserNotAuthorisedError):
            self.write(401, "Invalid or expired API key")

    def test_server_id_mismatch(self):
        with self.assertRaises(ze.ServerIDMismatchError) as caught:
            self.write(412, "Zotero-Server-ID does not match this server")
        self.assertIn("partitioned by server ID", str(caught.exception))

    def test_server_id_mismatch_is_still_a_precondition_failure(self):
        with self.assertRaises(ze.PreConditionFailedError):
            self.write(412, "Zotero-Server-ID does not match this server")

    def test_other_412_unchanged(self):
        with self.assertRaises(ze.PreConditionFailedError) as caught:
            self.write(412, "collection version mismatch: expected 3, found 4")
        self.assertNotIsInstance(caught.exception, ze.ServerIDMismatchError)

    def test_missing_server_id(self):
        with self.assertRaises(ze.ServerIDRequiredError):
            self.write(428, "Zotero-Server-ID not provided")

    def test_other_428_unchanged(self):
        with self.assertRaises(ze.PreConditionRequiredError) as caught:
            self.write(428, "If-Unmodified-Since-Version not provided")
        self.assertNotIsInstance(caught.exception, ze.ServerIDRequiredError)


class BatchUpdateTests(unittest.TestCase):
    """Keyed writes need a concurrency precondition on the local API."""

    def setUp(self):
        cwd = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(cwd, "api_responses", "item_fields.json")) as f:
            item_fields = f.read()
        self.mock = MockClient()
        # check_items() validates against the item field list
        self.mock.register("GET", f"{LOCAL}/itemFields", body=item_fields)
        self.mock.register("POST", f"{LOCAL}/users/0/items", body="{}")
        self.mock.register("POST", f"{LOCAL}/users/0/collections", body="{}")
        self.zot = local_zotero(self.mock, server_id=SERVER_ID, local_api_key="abc123")

    def test_last_modified_sets_precondition(self):
        self.zot.update_items([{"key": "ITEMKEY", "itemType": "book"}], 12)
        self.assertEqual(
            self.mock.last_request().headers["If-Unmodified-Since-Version"], "12"
        )

    def test_no_precondition_by_default(self):
        """Round-tripped objects carry their own version, so the header is optional"""
        self.zot.update_items([{"key": "ITEMKEY", "itemType": "book", "version": 3}])
        self.assertNotIn(
            "If-Unmodified-Since-Version", self.mock.last_request().headers
        )

    def test_collections_accept_last_modified(self):
        self.zot.update_collections([{"key": "COLLKEY", "itemType": "book"}], 5)
        self.assertEqual(
            self.mock.last_request().headers["If-Unmodified-Since-Version"], "5"
        )


class ItemTemplateTests(unittest.TestCase):
    """The local API doesn't implement /items/new."""

    def test_local_404_explains_the_gap(self):
        mock = MockClient()
        mock.register(
            "GET",
            f"{LOCAL}/items/new",
            body="No endpoint found",
            status=404,
            content_type="text/plain",
        )
        zot = local_zotero(mock)
        with self.assertRaises(ze.CallDoesNotExistError) as caught:
            zot.item_template("book")
        self.assertIn("create_items()", str(caught.exception))

    def test_web_404_is_unchanged(self):
        mock = MockClient()
        mock.register(
            "GET",
            "https://api.zotero.org/items/new",
            body="Not found",
            status=404,
            content_type="text/plain",
        )
        zot = z.Zotero("myuserID", "user", "myuserkey", client=mock.client)
        with self.assertRaises(ze.ResourceNotFoundError):
            zot.item_template("book")


class HelperTests(unittest.TestCase):
    """get_zotero_client() can build a write-capable client."""

    def test_defaults_are_unchanged(self):
        zot = get_zotero_client()
        self.assertTrue(zot.local)
        self.assertEqual(zot.locale, "en-US")
        self.assertIsNone(zot.server_id)
        self.assertIsNone(zot.local_api_key)

    def test_credentials_are_passed_through(self):
        zot = get_zotero_client(
            locale="de-DE", server_id=SERVER_ID, local_api_key="abc123"
        )
        self.assertEqual(zot.locale, "de-DE")
        self.assertEqual(zot.server_id, SERVER_ID)
        self.assertEqual(zot.local_api_key, "abc123")


if __name__ == "__main__":
    unittest.main()
