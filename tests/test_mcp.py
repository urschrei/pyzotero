"""Tests for the pyzotero MCP server tools."""

# ruff: noqa: PLR2004, PLC0415

from __future__ import annotations

import hashlib
import json
from unittest.mock import MagicMock, patch

import pytest

from pyzotero._helpers import save_local_key
from pyzotero._import import DOILookupError


# Skip only when the optional mcp extra is absent. Import the module itself
# directly, so that an incompatible mcp release fails the tests instead of
# skipping them.
pytest.importorskip("mcp", reason="mcp extra is not installed")
from pyzotero import mcp_server


# Fixtures
ITEM_FIXTURE = {
    "key": "ABC123",
    "version": 1,
    "meta": {"numChildren": 0},
    "data": {
        "key": "ABC123",
        "version": 1,
        "itemType": "journalArticle",
        "title": "Test Article",
        "creators": [
            {"creatorType": "author", "firstName": "Jane", "lastName": "Doe"},
            {"creatorType": "author", "firstName": "John", "lastName": "Smith"},
        ],
        "date": "2024",
        "publicationTitle": "Test Journal",
        "volume": "42",
        "issue": "1",
        "DOI": "10.1234/test",
        "url": "https://example.com/article",
    },
}

ITEMS_FIXTURE = [
    ITEM_FIXTURE,
    {
        "key": "DEF456",
        "version": 1,
        "meta": {"numChildren": 0},
        "data": {
            "key": "DEF456",
            "version": 1,
            "itemType": "book",
            "title": "Test Book",
            "creators": [{"creatorType": "author", "name": "Organisation"}],
            "date": "2023",
            "publicationTitle": "",
            "volume": "",
            "issue": "",
            "DOI": "",
            "url": "",
        },
    },
]

CHILDREN_FIXTURE = [
    {
        "key": "CHILD01",
        "data": {
            "key": "CHILD01",
            "itemType": "attachment",
            "title": "Full Text PDF",
            "parentItem": "ABC123",
            "contentType": "application/pdf",
        },
        "links": {"enclosure": {"href": "http://localhost:23119/file/ABC123/CHILD01"}},
    },
    {
        "key": "CHILD02",
        "data": {
            "key": "CHILD02",
            "itemType": "note",
            "note": "Some note content",
            "parentItem": "ABC123",
        },
    },
]

COLLECTIONS_FIXTURE = [
    {
        "data": {"key": "COL001", "name": "Physics", "parentCollection": False},
        "meta": {"numItems": 10},
    },
    {
        "data": {"key": "COL002", "name": "Quantum", "parentCollection": "COL001"},
        "meta": {"numItems": 5},
    },
]

TAGS_FIXTURE = ["climate", "machine learning", "physics"]

FULLTEXT_FIXTURE = {
    "content": "This is the full text of the document.",
    "indexedPages": 10,
    "totalPages": 10,
}

S2_PAPER_FIXTURE = {
    "paperId": "abc123def",
    "doi": "10.1234/test",
    "title": "A Test Paper",
    "authors": [{"authorId": "1", "name": "Jane Doe"}],
    "year": 2024,
    "venue": "Nature",
    "citationCount": 50,
    "referenceCount": 30,
    "isOpenAccess": True,
    "openAccessPdfUrl": "https://example.com/pdf",
}


def _mock_zotero():
    """Create a mock Zotero client."""
    mock = MagicMock()
    mock.top.return_value = ITEMS_FIXTURE
    mock.items.return_value = ITEMS_FIXTURE
    mock.item.return_value = ITEM_FIXTURE
    mock.children.return_value = CHILDREN_FIXTURE
    mock.collections.return_value = COLLECTIONS_FIXTURE
    mock.tags.return_value = TAGS_FIXTURE
    mock.collection_tags.return_value = TAGS_FIXTURE
    mock.fulltext_item.return_value = FULLTEXT_FIXTURE
    mock.collection_items.return_value = ITEMS_FIXTURE
    mock.collection_items_top.return_value = ITEMS_FIXTURE
    mock.everything.side_effect = lambda results: results
    return mock


@pytest.fixture
def mock_zot():
    """Patch get_zotero_client to return a mock."""
    mock = _mock_zotero()
    with patch("pyzotero.mcp_server.get_zotero_client", return_value=mock):
        yield mock


class TestSearch:
    def test_search_basic(self, mock_zot):
        result = json.loads(mcp_server.search(query="test"))
        assert result["count"] == 2
        assert result["items"][0]["title"] == "Test Article"
        assert result["items"][0]["key"] == "ABC123"
        mock_zot.top.assert_called_once()

    def test_search_with_collection(self, mock_zot):
        result = json.loads(mcp_server.search(query="test", collection="COL001"))
        assert result["count"] == 2
        mock_zot.collection_items_top.assert_called_once()

    def test_search_fulltext(self, mock_zot):
        # For fulltext, items() is called and results are split by parentItem
        mock_zot.items.return_value = ITEMS_FIXTURE  # no parentItem = top-level
        result = json.loads(mcp_server.search(query="test", fulltext=True))
        assert result["count"] == 2
        mock_zot.items.assert_called_once()

    def test_search_with_itemtype(self, mock_zot):
        json.loads(mcp_server.search(itemtype="book"))
        call_kwargs = mock_zot.top.call_args
        assert call_kwargs[1]["itemType"] == "book"

    def test_search_with_tags(self, mock_zot):
        json.loads(mcp_server.search(tag="climate,adaptation"))
        call_kwargs = mock_zot.top.call_args
        assert call_kwargs[1]["tag"] == ["climate", "adaptation"]

    def test_search_with_single_tag(self, mock_zot):
        json.loads(mcp_server.search(tag="climate"))
        call_kwargs = mock_zot.top.call_args
        assert call_kwargs[1]["tag"] == "climate"

    def test_search_creators_format(self, mock_zot):
        result = json.loads(mcp_server.search())
        # First item has firstName/lastName creators
        assert result["items"][0]["creators"] == ["Jane Doe", "John Smith"]
        # Second item has a 'name' creator
        assert result["items"][1]["creators"] == ["Organisation"]

    def test_search_error(self, mock_zot):
        mock_zot.top.side_effect = Exception("Connection refused")
        result = json.loads(mcp_server.search())
        assert "error" in result
        assert "Connection refused" in result["error"]


class TestGetItem:
    def test_get_item(self, mock_zot):
        result = json.loads(mcp_server.get_item(key="ABC123"))
        assert result["data"]["title"] == "Test Article"

    def test_get_item_not_found(self, mock_zot):
        mock_zot.item.return_value = None
        result = json.loads(mcp_server.get_item(key="NOTFOUND"))
        assert "error" in result

    def test_get_item_error(self, mock_zot):
        mock_zot.item.side_effect = Exception("404")
        result = json.loads(mcp_server.get_item(key="BAD"))
        assert "error" in result


class TestGetChildren:
    def test_get_children(self, mock_zot):
        result = json.loads(mcp_server.get_children(key="ABC123"))
        assert len(result) == 2
        assert result[0]["data"]["itemType"] == "attachment"

    def test_get_children_empty(self, mock_zot):
        mock_zot.children.return_value = []
        result = json.loads(mcp_server.get_children(key="ABC123"))
        assert result == []


class TestListCollections:
    def test_list_collections(self, mock_zot):
        result = json.loads(mcp_server.list_collections())
        assert len(result) == 2
        assert result[0]["id"] == "COL001"
        assert result[0]["name"] == "Physics"
        assert result[0]["items"] == 10
        assert result[0]["parent"] is None

    def test_list_collections_with_parent(self, mock_zot):
        result = json.loads(mcp_server.list_collections())
        assert result[1]["parent"]["id"] == "COL001"
        assert result[1]["parent"]["name"] == "Physics"

    def test_list_collections_with_limit(self, mock_zot):
        json.loads(mcp_server.list_collections(limit=5))
        call_kwargs = mock_zot.collections.call_args
        assert call_kwargs[1]["limit"] == 5

    def test_list_collections_zero_limit_means_all(self, mock_zot):
        json.loads(mcp_server.list_collections(limit=0))
        call_kwargs = mock_zot.collections.call_args
        assert "limit" not in call_kwargs[1]


class TestListTags:
    def test_list_tags(self, mock_zot):
        result = json.loads(mcp_server.list_tags())
        assert result == ["climate", "machine learning", "physics"]
        mock_zot.tags.assert_called_once()

    def test_list_tags_by_collection(self, mock_zot):
        json.loads(mcp_server.list_tags(collection="COL001"))
        mock_zot.collection_tags.assert_called_once_with("COL001")


class TestGetFulltext:
    def test_get_fulltext(self, mock_zot):
        result = json.loads(mcp_server.get_fulltext(key="CHILD01"))
        assert "content" in result
        assert result["indexedPages"] == 10

    def test_get_fulltext_empty(self, mock_zot):
        mock_zot.fulltext_item.return_value = None
        result = json.loads(mcp_server.get_fulltext(key="CHILD01"))
        assert "error" in result


class TestFindRelated:
    @patch("pyzotero.mcp_server.get_recommendations")
    def test_find_related(self, mock_recs, mock_zot):
        mock_recs.return_value = {"papers": [S2_PAPER_FIXTURE]}
        mock_zot.everything.return_value = []
        result = json.loads(
            mcp_server.find_related(doi="10.1234/test", check_library=False)
        )
        assert result["count"] == 1
        assert result["papers"][0]["title"] == "A Test Paper"

    @patch("pyzotero.mcp_server.get_recommendations")
    def test_find_related_with_library_check(self, mock_recs, mock_zot):
        mock_recs.return_value = {"papers": [S2_PAPER_FIXTURE]}
        # Mock library to contain the paper
        mock_zot.everything.return_value = [
            {"data": {"DOI": "10.1234/test", "key": "ABC123"}}
        ]
        result = json.loads(mcp_server.find_related(doi="10.1234/test"))
        assert result["papers"][0]["inLibrary"] is True

    @patch("pyzotero.mcp_server.get_recommendations")
    def test_find_related_not_found(self, mock_recs, mock_zot):
        from pyzotero.semantic_scholar import PaperNotFoundError

        mock_recs.side_effect = PaperNotFoundError()
        result = json.loads(mcp_server.find_related(doi="10.9999/missing"))
        assert "error" in result

    @patch("pyzotero.mcp_server.get_recommendations")
    def test_find_related_empty(self, mock_recs, mock_zot):
        mock_recs.return_value = {"papers": []}
        result = json.loads(
            mcp_server.find_related(doi="10.1234/test", check_library=False)
        )
        assert result["count"] == 0
        assert result["papers"] == []


class TestGetCitations:
    @patch("pyzotero.mcp_server.s2_get_citations")
    def test_get_citations(self, mock_cit, mock_zot):
        mock_cit.return_value = {"papers": [S2_PAPER_FIXTURE]}
        result = json.loads(
            mcp_server.get_citations(doi="10.1234/test", check_library=False)
        )
        assert result["count"] == 1

    @patch("pyzotero.mcp_server.s2_get_citations")
    def test_get_citations_with_min_citations(self, mock_cit, mock_zot):
        low_citations_paper = {**S2_PAPER_FIXTURE, "citationCount": 5}
        mock_cit.return_value = {"papers": [low_citations_paper]}
        result = json.loads(
            mcp_server.get_citations(
                doi="10.1234/test", min_citations=10, check_library=False
            )
        )
        assert result["count"] == 0


class TestGetReferences:
    @patch("pyzotero.mcp_server.s2_get_references")
    def test_get_references(self, mock_ref, mock_zot):
        mock_ref.return_value = {"papers": [S2_PAPER_FIXTURE]}
        result = json.loads(
            mcp_server.get_references(doi="10.1234/test", check_library=False)
        )
        assert result["count"] == 1

    @patch("pyzotero.mcp_server.s2_get_references")
    def test_get_references_rate_limit(self, mock_ref, mock_zot):
        from pyzotero.semantic_scholar import RateLimitError

        mock_ref.side_effect = RateLimitError()
        result = json.loads(mcp_server.get_references(doi="10.1234/test"))
        assert "error" in result
        assert "Rate limit" in result["error"]


class TestSearchSemanticScholar:
    @patch("pyzotero.mcp_server.search_papers")
    def test_search_s2(self, mock_search, mock_zot):
        mock_search.return_value = {
            "total": 100,
            "papers": [S2_PAPER_FIXTURE],
        }
        result = json.loads(
            mcp_server.search_semantic_scholar(query="test query", check_library=False)
        )
        assert result["count"] == 1
        assert result["total"] == 100

    @patch("pyzotero.mcp_server.search_papers")
    def test_search_s2_empty(self, mock_search, mock_zot):
        mock_search.return_value = {"total": 0, "papers": []}
        result = json.loads(
            mcp_server.search_semantic_scholar(query="nonexistent", check_library=False)
        )
        assert result["count"] == 0

    @patch("pyzotero.mcp_server.search_papers")
    def test_search_s2_passes_params(self, mock_search, mock_zot):
        mock_search.return_value = {"total": 0, "papers": []}
        mcp_server.search_semantic_scholar(
            query="test",
            limit=50,
            year="2020-2024",
            open_access=True,
            sort="citations",
            min_citations=10,
            check_library=False,
        )
        mock_search.assert_called_once_with(
            "test",
            limit=50,
            year="2020-2024",
            open_access_only=True,
            sort="citations",
            min_citations=10,
        )

    @patch("pyzotero.mcp_server.search_papers")
    def test_search_s2_empty_year_and_sort(self, mock_search, mock_zot):
        mock_search.return_value = {"total": 0, "papers": []}
        mcp_server.search_semantic_scholar(
            query="test", year="", sort="", check_library=False
        )
        mock_search.assert_called_once_with(
            "test",
            limit=20,
            year=None,
            open_access_only=False,
            sort=None,
            min_citations=0,
        )


# Write tools (#333): registered only when the server is started with
# --enable-writes, so that they're absent from the tool list otherwise.


class _FakeServer:
    """Minimal stand-in for MCPServer that records what gets registered."""

    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


def _collection(key, name, parent=False):
    return {"key": key, "data": {"key": key, "name": name, "parentCollection": parent}}


# The collections that the write tool tests refer to by key
WRITE_COLLECTIONS = [
    _collection(key, f"Collection {key}")
    for key in ("COLL1", "PARENT1", "PARENT", "C1", "OLD", "NEW")
]


@pytest.fixture
def write_zot():
    """Patch _write_client to return a mock, and return the mock."""
    mock = MagicMock()
    mock.collections.return_value = WRITE_COLLECTIONS
    mock.everything.side_effect = lambda results: results
    mock.create_items.return_value = {"success": {"0": "NEWKEY"}, "failed": {}}
    mock.create_collections.return_value = {"success": {"0": "NEWCOLL"}, "failed": {}}
    mock.item.return_value = {
        "key": "ABC123",
        "version": 3,
        "data": {"key": "ABC123", "version": 3, "title": "Old", "tags": []},
    }
    mock.children.return_value = []
    with patch("pyzotero.mcp_server._write_client", return_value=mock):
        yield mock


@pytest.fixture
def write_tools(write_zot):
    """Register the write tools, deletes included, onto a fake server."""
    server = _FakeServer()
    mcp_server.register_write_tools(server, enable_deletes=True)
    return server.tools


class TestWriteGating:
    def test_write_tools_are_not_importable_symbols(self):
        """They're closures registered on demand, so nothing leaks at import"""
        for name in ("create_item", "update_item", "delete_item"):
            assert not hasattr(mcp_server, name)

    def test_deletes_excluded_by_default(self):
        server = _FakeServer()
        names = mcp_server.register_write_tools(server)
        assert "create_item" in names
        assert "remove_from_collection" in names
        assert "move_to_collection" in names
        assert "delete_item" not in names
        assert "delete_item" not in server.tools

    def test_deletes_registered_when_enabled(self):
        server = _FakeServer()
        names = mcp_server.register_write_tools(server, enable_deletes=True)
        assert "delete_item" in names
        assert "delete_item" in server.tools

    def test_registered_names_match_registered_tools(self):
        server = _FakeServer()
        names = mcp_server.register_write_tools(server, enable_deletes=True)
        assert sorted(names) == sorted(server.tools)


USER_LIBRARY = {"library_id": "0", "library_type": "user"}


class TestWriteClient:
    @pytest.fixture(autouse=True)
    def _no_stored_key(self, monkeypatch, tmp_path):
        """Point the key file at an empty directory, whatever the user has"""
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        monkeypatch.delenv(mcp_server.WRITE_KEY_ENV, raising=False)
        monkeypatch.delenv(mcp_server.SERVER_ID_ENV, raising=False)

    def test_missing_key_raises_with_remedy(self):
        with pytest.raises(RuntimeError, match="pyzotero authorize"):
            mcp_server._write_client()

    def test_key_and_server_id_passed_through(self, monkeypatch):
        monkeypatch.setenv(mcp_server.WRITE_KEY_ENV, "key123")
        monkeypatch.setenv(mcp_server.SERVER_ID_ENV, "srv123")
        with patch("pyzotero._helpers.get_zotero_client") as client:
            mcp_server._write_client()
        client.assert_called_once_with(
            "en-US", server_id="srv123", local_api_key="key123", **USER_LIBRARY
        )

    def test_absent_server_id_is_none(self, monkeypatch):
        monkeypatch.setenv(mcp_server.WRITE_KEY_ENV, "key123")
        with patch("pyzotero._helpers.get_zotero_client") as client:
            mcp_server._write_client()
        client.assert_called_once_with(
            "en-US", server_id=None, local_api_key="key123", **USER_LIBRARY
        )

    def test_key_file_used_when_env_absent(self):
        """The file that 'pyzotero authorize' writes serves the MCP server too"""
        save_local_key("filekey", "filesrv")
        with patch("pyzotero._helpers.get_zotero_client") as client:
            mcp_server._write_client()
        client.assert_called_once_with(
            "en-US", server_id="filesrv", local_api_key="filekey", **USER_LIBRARY
        )

    def test_env_takes_precedence_over_key_file(self, monkeypatch):
        save_local_key("filekey", "filesrv")
        monkeypatch.setenv(mcp_server.WRITE_KEY_ENV, "envkey")
        with patch("pyzotero._helpers.get_zotero_client") as client:
            mcp_server._write_client()
        client.assert_called_once_with(
            "en-US", server_id=None, local_api_key="envkey", **USER_LIBRARY
        )


class TestWriteTools:
    def test_create_item_builds_payload(self, write_tools, write_zot):
        result = json.loads(
            write_tools["create_item"](
                "book",
                fields={"title": "A Book"},
                creators=[{"creatorType": "author", "lastName": "Doe"}],
                tags=["one", "two"],
                collections=["COLL1"],
            )
        )
        assert result["created"] == "NEWKEY"
        payload = write_zot.create_items.call_args[0][0][0]
        assert payload == {
            "itemType": "book",
            "title": "A Book",
            "creators": [{"creatorType": "author", "lastName": "Doe"}],
            "tags": [{"tag": "one"}, {"tag": "two"}],
            "collections": ["COLL1"],
        }

    def test_create_item_reports_rejection(self, write_tools, write_zot):
        write_zot.create_items.return_value = {
            "success": {},
            "failed": {"0": {"code": 400, "message": "Invalid field"}},
        }
        result = json.loads(write_tools["create_item"]("book"))
        assert "error" in result
        assert result["detail"]["0"]["message"] == "Invalid field"

    def test_update_item_merges_fields(self, write_tools, write_zot):
        result = json.loads(write_tools["update_item"]("ABC123", {"title": "New"}))
        assert result["updated"] == "ABC123"
        sent = write_zot.update_item.call_args[0][0]
        assert sent["data"]["title"] == "New"
        # the existing version is preserved, so the precondition still applies
        assert sent["data"]["version"] == 3

    def test_add_tags(self, write_tools, write_zot):
        write_tools["add_tags"]("ABC123", ["alpha", "beta"])
        assert write_zot.add_tags.call_args[0][1:] == ("alpha", "beta")

    def test_create_collection_with_parent(self, write_tools, write_zot):
        result = json.loads(write_tools["create_collection"]("Kids", parent="PARENT1"))
        assert result["created"] == "NEWCOLL"
        assert write_zot.create_collections.call_args[0][0][0] == {
            "name": "Kids",
            "parentCollection": "PARENT1",
        }

    def test_create_collection_without_parent(self, write_tools, write_zot):
        write_tools["create_collection"]("Top")
        assert write_zot.create_collections.call_args[0][0][0] == {"name": "Top"}

    def test_add_to_collection(self, write_tools, write_zot):
        write_tools["add_to_collection"]("ABC123", "COLL1")
        args = write_zot.addto_collection.call_args[0]
        assert args[0] == "COLL1"
        assert args[1]["key"] == "ABC123"

    def test_remove_from_collection(self, write_tools, write_zot):
        result = json.loads(write_tools["remove_from_collection"]("ABC123", "COLL1"))
        assert result == {"item": "ABC123", "removedFrom": "COLL1"}
        args = write_zot.deletefrom_collection.call_args[0]
        assert args[0] == "COLL1"
        assert args[1]["key"] == "ABC123"

    def test_move_to_collection(self, write_tools, write_zot):
        result = json.loads(write_tools["move_to_collection"]("ABC123", "OLD", "NEW"))
        assert result == {"item": "ABC123", "movedFrom": "OLD", "movedTo": "NEW"}
        args = write_zot.moveto_collection.call_args[0]
        assert args[:2] == ("OLD", "NEW")
        assert args[2]["key"] == "ABC123"

    def test_delete_item(self, write_tools, write_zot):
        result = json.loads(write_tools["delete_item"]("ABC123"))
        assert result["deleted"] == "ABC123"
        assert write_zot.delete_item.call_args[0][0]["key"] == "ABC123"

    def test_errors_are_returned_as_json(self, write_tools, write_zot):
        write_zot.create_items.side_effect = RuntimeError("boom")
        result = json.loads(write_tools["create_item"]("book"))
        assert result["error"] == "boom"


class TestAttachmentTool:
    def test_relative_path_rejected(self, write_tools):
        result = json.loads(write_tools["add_attachment"]("ABC123", "notes.pdf"))
        assert "absolute path" in result["error"]

    def test_missing_file_rejected(self, write_tools, tmp_path):
        missing = tmp_path / "nope.pdf"
        result = json.loads(write_tools["add_attachment"]("ABC123", str(missing)))
        assert "No file at" in result["error"]

    def test_directory_rejected(self, write_tools, tmp_path):
        result = json.loads(write_tools["add_attachment"]("ABC123", str(tmp_path)))
        assert "No file at" in result["error"]

    def test_template_carries_full_path_and_parent(
        self, write_tools, write_zot, tmp_path
    ):
        target = tmp_path / "paper.pdf"
        target.write_bytes(b"%PDF-1.4\n")
        write_zot.upload_attachments.return_value = {
            "success": [{"key": "ATTKEY", "filename": str(target)}],
            "failure": [],
            "unchanged": [],
        }
        result = json.loads(write_tools["add_attachment"]("ABC123", str(target)))
        assert result["attached"] == "ATTKEY"
        assert result["parent"] == "ABC123"
        assert result["filename"] == "paper.pdf"
        payload, parent = write_zot.upload_attachments.call_args[0]
        assert parent == "ABC123"
        # the full path is kept: Zupload reads the file from it, and sends only
        # the basename to the API (#341)
        assert payload[0]["filename"] == str(target)
        assert payload[0]["itemType"] == "attachment"
        assert payload[0]["linkMode"] == "imported_file"
        # contentType is left out so the upload machinery detects it
        assert "contentType" not in payload[0]

    def test_title_defaults_to_filename(self, write_tools, write_zot, tmp_path):
        target = tmp_path / "paper.pdf"
        target.write_bytes(b"%PDF-1.4\n")
        write_zot.upload_attachments.return_value = {
            "success": [{"key": "ATTKEY"}],
            "failure": [],
            "unchanged": [],
        }
        write_tools["add_attachment"]("ABC123", str(target))
        assert write_zot.upload_attachments.call_args[0][0][0]["title"] == "paper.pdf"
        write_tools["add_attachment"]("ABC123", str(target), title="Custom")
        assert write_zot.upload_attachments.call_args[0][0][0]["title"] == "Custom"

    def test_identical_file_is_not_duplicated(self, write_tools, write_zot, tmp_path):
        """Uploading always creates a new item, so a retry would otherwise duplicate"""
        target = tmp_path / "paper.pdf"
        target.write_bytes(b"%PDF-1.4\n")
        digest = hashlib.md5(target.read_bytes()).hexdigest()  # noqa: S324
        write_zot.children.return_value = [
            {"key": "EXISTING", "data": {"filename": "paper.pdf", "md5": digest}}
        ]
        result = json.loads(write_tools["add_attachment"]("ABC123", str(target)))
        assert result["unchanged"] == "EXISTING"
        write_zot.upload_attachments.assert_not_called()

    def test_same_name_different_contents_is_attached(
        self, write_tools, write_zot, tmp_path
    ):
        target = tmp_path / "paper.pdf"
        target.write_bytes(b"%PDF-1.4\n")
        write_zot.children.return_value = [
            {
                "key": "EXISTING",
                "data": {"filename": "paper.pdf", "md5": "differentmd5"},
            }
        ]
        write_zot.upload_attachments.return_value = {
            "success": [{"key": "ATTKEY"}],
            "failure": [],
            "unchanged": [],
        }
        result = json.loads(write_tools["add_attachment"]("ABC123", str(target)))
        assert result["attached"] == "ATTKEY"

    def test_unchanged_from_server_reported(self, write_tools, write_zot, tmp_path):
        target = tmp_path / "paper.pdf"
        target.write_bytes(b"%PDF-1.4\n")
        write_zot.upload_attachments.return_value = {
            "success": [],
            "failure": [],
            "unchanged": [{"filename": str(target)}],
        }
        result = json.loads(write_tools["add_attachment"]("ABC123", str(target)))
        assert "unchanged" in result

    def test_rejection_surfaces_server_reason(self, write_tools, write_zot, tmp_path):
        target = tmp_path / "paper.pdf"
        target.write_bytes(b"%PDF-1.4\n")
        write_zot.upload_attachments.return_value = {
            "success": [],
            "failure": [{"filename": str(target), "error": {"message": "Too large"}}],
            "unchanged": [],
        }
        result = json.loads(write_tools["add_attachment"]("ABC123", str(target)))
        assert result["error"] == "Attachment was rejected"
        assert result["detail"]["error"]["message"] == "Too large"


# Search sorting, notes, annotations and BibTeX export


class TestSearchSort:
    def test_sort_and_direction_passed(self, mock_zot):
        mcp_server.search(sort="dateAdded", direction="desc", limit=5)
        params = mock_zot.top.call_args[1]
        assert params == {"limit": 5, "sort": "dateAdded", "direction": "desc"}

    def test_no_sort_by_default(self, mock_zot):
        mcp_server.search(query="x")
        assert "sort" not in mock_zot.top.call_args[1]


NOTE_ITEM = {
    "key": "NOTE01",
    "data": {
        "key": "NOTE01",
        "itemType": "note",
        "parentItem": "ABC123",
        "note": "<h1>Title</h1><p>First &amp; para</p><ul><li>one</li><li>two</li></ul>",
        "tags": [{"tag": "summary"}],
        "dateModified": "2026-01-01T00:00:00Z",
    },
}


class TestGetNotes:
    def test_child_notes_of_item(self, mock_zot):
        mock_zot.everything.side_effect = lambda x: x
        mock_zot.children.return_value = [CHILDREN_FIXTURE[0], NOTE_ITEM]
        result = json.loads(mcp_server.get_notes(key="ABC123"))
        assert result["count"] == 1
        note = result["notes"][0]
        assert note["key"] == "NOTE01"
        assert note["text"] == "Title\n\nFirst & para\n\n- one\n- two"
        assert note["tags"] == ["summary"]

    def test_query_searches_all_notes(self, mock_zot):
        mock_zot.items.return_value = [NOTE_ITEM]
        mcp_server.get_notes(query="para", limit=5)
        mock_zot.items.assert_called_once_with(
            itemType="note", limit=5, q="para", qmode="everything"
        )

    def test_recent_notes_without_key_or_query(self, mock_zot):
        mock_zot.items.return_value = []
        mcp_server.get_notes()
        assert mock_zot.items.call_args[1]["sort"] == "dateModified"


def _annotation(key, sort_index, **fields):
    return {
        "key": key,
        "data": {
            "key": key,
            "itemType": "annotation",
            "annotationSortIndex": sort_index,
            "tags": [],
            **fields,
        },
    }


class TestGetAnnotations:
    @pytest.fixture
    def annotated(self, mock_zot):
        pdf = {
            "key": "PDF01",
            "data": {
                "key": "PDF01",
                "itemType": "attachment",
                "title": "Full Text PDF",
            },
        }
        annotations = [
            _annotation(
                "ANN2",
                "00002|000100|00050",
                annotationType="note",
                annotationComment="Later",
            ),
            _annotation(
                "ANN1",
                "00001|000200|00100",
                annotationType="highlight",
                annotationText="Quoted",
                annotationColor="#ffd400",
                annotationPageLabel="3",
            ),
        ]
        mock_zot.everything.side_effect = lambda x: x
        mock_zot.item.side_effect = lambda key: pdf if key == "PDF01" else ITEM_FIXTURE

        # Like the local API, give annotations only when they are asked for
        def children(key, **kwargs):
            if key != "PDF01":
                return [pdf, NOTE_ITEM]
            return annotations if kwargs.get("itemType") == "annotation" else []

        mock_zot.children.side_effect = children
        return mock_zot

    def test_from_parent_item(self, annotated):
        result = json.loads(mcp_server.get_annotations("ABC123"))
        assert result["count"] == 2
        [attachment] = result["attachments"]
        assert attachment["key"] == "PDF01"
        first, second = attachment["annotations"]
        assert first == {
            "key": "ANN1",
            "type": "highlight",
            "text": "Quoted",
            "color": "#ffd400",
            "page": "3",
            "tags": [],
        }
        assert second["comment"] == "Later"

    def test_from_attachment(self, annotated):
        result = json.loads(mcp_server.get_annotations("PDF01"))
        assert result["count"] == 2
        assert [c[0][0] for c in annotated.children.call_args_list] == ["PDF01"]


class TestExportBibtex:
    def test_export_chunks_keys_and_dumps(self, mock_zot):
        import bibtexparser

        def fake_items(**kwargs):
            db = bibtexparser.bibdatabase.BibDatabase()
            db.entries = [
                {"ENTRYTYPE": "article", "ID": k, "title": f"T {k}"}
                for k in kwargs["itemKey"].split(",")
            ]
            return db

        mock_zot.items.side_effect = fake_items
        keys = [f"K{i}" for i in range(51)]
        result = json.loads(mcp_server.export_bibtex(keys))
        assert result["count"] == 51
        assert mock_zot.items.call_count == 2
        assert mock_zot.items.call_args_list[0][1]["format"] == "bibtex"
        assert "@article{K50," in result["bibtex"]

    def test_export_local_api_plain_text(self, mock_zot):
        """The local API sends export formats as text/plain, so they arrive as bytes"""
        mock_zot.items.side_effect = lambda **kwargs: "".join(
            f"\n@article{{{k},\n\ttitle = {{T\u00e9 {k}}},\n}}\n"
            for k in kwargs["itemKey"].split(",")
        ).encode("utf-8")
        result = json.loads(mcp_server.export_bibtex(["A1", "B2"]))
        assert result["count"] == 2
        assert result["bibtex"].startswith("@article{A1,")
        assert "Té B2" in result["bibtex"]


class TestNoteHTML:
    def test_line_breaks_are_single(self):
        assert mcp_server._note_to_text("<p>a<br/>b<br>c</p>") == "a\nb\nc"

    def test_plain_text_is_escaped_into_paragraphs(self):
        html = mcp_server._text_to_note_html("a < b\nnext line\n\nsecond")
        assert html == "<p>a &lt; b<br>next line</p><p>second</p>"


# Write tools added for notes, collections and imports


class TestNewWriteTools:
    def test_registered(self, write_tools):
        for name in (
            "create_note",
            "update_note",
            "update_collection",
            "add_by_identifier",
            "import_items",
            "merge_items",
            "set_related",
        ):
            assert name in write_tools

    def test_create_child_note(self, write_tools, write_zot):
        result = json.loads(
            write_tools["create_note"]("Hello <world>", parent_key="ABC123", tags=["t"])
        )
        assert result["created"] == "NEWKEY"
        payload = write_zot.create_items.call_args[0][0][0]
        assert payload == {
            "itemType": "note",
            "note": "<p>Hello &lt;world&gt;</p>",
            "tags": [{"tag": "t"}],
            "parentItem": "ABC123",
        }

    def test_create_note_html_kept(self, write_tools, write_zot):
        write_tools["create_note"]("<p><b>x</b></p>", is_html=True, collections=["C1"])
        payload = write_zot.create_items.call_args[0][0][0]
        assert payload["note"] == "<p><b>x</b></p>"
        assert payload["collections"] == ["C1"]
        assert "parentItem" not in payload

    def test_child_note_with_collections_rejected(self, write_tools, write_zot):
        result = json.loads(
            write_tools["create_note"]("x", parent_key="ABC123", collections=["C1"])
        )
        assert "error" in result
        write_zot.create_items.assert_not_called()

    def test_update_note(self, write_tools, write_zot):
        write_zot.item.return_value = {
            "key": "NOTE01",
            "data": {"key": "NOTE01", "version": 2, "itemType": "note", "note": ""},
        }
        write_tools["update_note"]("NOTE01", "new text")
        assert (
            write_zot.update_item.call_args[0][0]["data"]["note"] == "<p>new text</p>"
        )

    def test_update_note_rejects_other_items(self, write_tools, write_zot):
        result = json.loads(write_tools["update_note"]("ABC123", "x"))
        assert "not a note" in result["error"]
        write_zot.update_item.assert_not_called()

    @pytest.fixture
    def collection(self, write_zot):
        write_zot.collection.return_value = {
            "key": "COLL1",
            "data": {
                "key": "COLL1",
                "version": 4,
                "name": "Old",
                "parentCollection": "PARENT",
            },
        }
        return write_zot

    def test_rename_collection(self, write_tools, collection):
        result = json.loads(write_tools["update_collection"]("COLL1", name="New"))
        assert result == {"updated": "COLL1", "name": "New", "parent": "PARENT"}
        assert collection.update_collection.call_args[0][0]["version"] == 4

    def test_move_collection_to_top_level(self, write_tools, collection):
        result = json.loads(write_tools["update_collection"]("COLL1", parent=""))
        sent = collection.update_collection.call_args[0][0]
        assert sent["parentCollection"] is False
        assert sent["name"] == "Old"
        assert result["parent"] is None

    def test_update_collection_needs_a_change(self, write_tools, collection):
        result = json.loads(write_tools["update_collection"]("COLL1"))
        assert "error" in result
        collection.update_collection.assert_not_called()

    def test_collection_cannot_be_own_parent(self, write_tools, collection):
        result = json.loads(write_tools["update_collection"]("COLL1", parent="COLL1"))
        assert "own parent" in result["error"]


BIB_SOURCE = r"""
@article{one, title={First Paper}, author={Doe, Jane}, journal={J}, year=2020,
          doi={10.1234/ONE}}
@book{two, title={Second Book}, author={Roe, Rick}, year=2021}
"""


@pytest.fixture
def import_zot(write_zot):
    """Give the write client a schema and an empty library."""
    fields = {
        "journalArticle": ["title", "publicationTitle", "date", "DOI", "extra"],
        "book": ["title", "date", "publisher", "extra"],
    }
    write_zot.item_type_fields.side_effect = lambda t: [{"field": f} for f in fields[t]]
    write_zot.item_creator_types.side_effect = lambda t: [
        {"creatorType": "author"},
        {"creatorType": "editor"},
    ]
    write_zot.items.return_value = []
    write_zot.top.return_value = []
    write_zot.create_items.return_value = {
        "success": {"0": "KEY0", "1": "KEY1"},
        "failed": {},
    }
    return write_zot


class TestImportItems:
    def test_bibtex_creates_items(self, write_tools, import_zot):
        result = json.loads(
            write_tools["import_items"](
                BIB_SOURCE, collections=["C1"], tags=["imported"]
            )
        )
        assert result["counts"] == {"created": 2}
        assert [i["key"] for i in result["items"]] == ["KEY0", "KEY1"]
        sent = import_zot.create_items.call_args[0][0]
        assert sent[0]["DOI"] == "10.1234/ONE"
        assert sent[0]["collections"] == ["C1"]
        assert sent[0]["tags"] == [{"tag": "imported"}]
        assert sent[1]["itemType"] == "book"
        # citationKey isn't a field in this schema, so it went to Extra
        assert sent[1]["extra"] == "Citation Key: two"

    def test_existing_doi_is_skipped(self, write_tools, import_zot):
        existing = {
            "key": "OLD1",
            "data": {
                "key": "OLD1",
                "DOI": "https://doi.org/10.1234/one",
                "collections": [],
            },
        }
        import_zot.items.return_value = [existing]
        import_zot.create_items.return_value = {"success": {"0": "KEY1"}, "failed": {}}
        result = json.loads(write_tools["import_items"](BIB_SOURCE))
        assert result["counts"] == {"exists": 1, "created": 1}
        assert result["items"][0] == {
            "title": "First Paper",
            "itemType": "journalArticle",
            "key": "OLD1",
            "status": "exists",
        }
        assert len(import_zot.create_items.call_args[0][0]) == 1
        import_zot.addto_collection.assert_not_called()

    def test_existing_title_is_filed(self, write_tools, import_zot):
        existing = {
            "key": "OLD2",
            "data": {
                "key": "OLD2",
                "title": "Second book",
                "date": "2021",
                "collections": [],
            },
        }
        import_zot.top.return_value = [existing]
        import_zot.item.return_value = existing
        import_zot.create_items.return_value = {"success": {"0": "KEY0"}, "failed": {}}
        result = json.loads(
            write_tools["import_items"](
                BIB_SOURCE, collections=["C1"], tags=["t"], if_exists="file"
            )
        )
        assert result["items"][1]["status"] == "filed"
        import_zot.addto_collection.assert_called_once_with("C1", existing)
        import_zot.add_tags.assert_called_once_with(existing, "t")

    def test_title_match_needs_same_year(self, write_tools, import_zot):
        import_zot.top.return_value = [
            {
                "key": "OLD2",
                "data": {"key": "OLD2", "title": "Second Book", "date": "1999"},
            }
        ]
        result = json.loads(write_tools["import_items"](BIB_SOURCE))
        assert result["counts"] == {"created": 2}

    def test_create_mode_skips_lookup(self, write_tools, import_zot):
        write_tools["import_items"](BIB_SOURCE, if_exists="create")
        import_zot.items.assert_not_called()
        import_zot.top.assert_not_called()

    def test_rejected_item_reported(self, write_tools, import_zot):
        import_zot.create_items.return_value = {
            "success": {"0": "KEY0"},
            "failed": {"1": {"code": 400, "message": "bad field"}},
        }
        result = json.loads(write_tools["import_items"](BIB_SOURCE))
        assert result["counts"] == {"created": 1, "failed": 1}
        assert result["items"][1]["error"] == "bad field"

    def test_csljson_single_object(self, write_tools, import_zot):
        source = json.dumps({"type": "book", "title": "CSL Book"})
        result = json.loads(write_tools["import_items"](source, format="csljson"))
        assert result["counts"] == {"created": 1}

    def test_file_path(self, write_tools, import_zot, tmp_path):
        bib = tmp_path / "refs.bib"
        bib.write_text(BIB_SOURCE, encoding="utf-8")
        result = json.loads(write_tools["import_items"](file_path=str(bib)))
        assert result["counts"] == {"created": 2}

    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [
            ({}, "either data or file_path"),
            ({"data": "x", "file_path": "/x"}, "either data or file_path"),
            ({"file_path": "refs.bib"}, "absolute"),
            ({"data": "x", "format": "ris"}, "format must be"),
            ({"data": "no entries here"}, "No entries"),
            ({"data": BIB_SOURCE, "if_exists": "merge"}, "if_exists must be"),
        ],
    )
    def test_bad_arguments(self, write_tools, import_zot, kwargs, message):
        result = json.loads(write_tools["import_items"](**kwargs))
        assert message in result["error"]
        import_zot.create_items.assert_not_called()


class TestAddByIdentifier:
    def test_mixed_success_and_failure(self, write_tools, import_zot):
        csl = {"type": "article-journal", "title": "By DOI", "DOI": "10.1/a"}

        def fake_fetch(doi):
            if doi == "10.1/bad":
                msg = "DOI not found: 10.1/bad"
                raise DOILookupError(msg)
            return csl

        with patch("pyzotero._import.fetch_doi_csl", side_effect=fake_fetch):
            result = json.loads(
                write_tools["add_by_identifier"](["10.1/bad", "10.1/a", "nonsense"])
            )
        assert result["counts"] == {"failed": 2, "created": 1}
        assert result["items"][0] == {
            "identifier": "10.1/bad",
            "status": "failed",
            "error": "DOI not found: 10.1/bad",
        }
        assert result["items"][1]["type"] == "doi"
        assert "Not a DOI, arXiv ID or ISBN" in result["items"][2]["error"]
        assert result["items"][1]["key"] == "KEY0"
        assert import_zot.create_items.call_args[0][0][0]["DOI"] == "10.1/a"


# Server flags


class TestMain:
    @pytest.fixture
    def run(self, monkeypatch):
        monkeypatch.setattr(mcp_server, "_LIBRARY", dict(mcp_server._LIBRARY))
        registered = MagicMock(return_value=["create_item"])
        monkeypatch.setattr(mcp_server, "register_write_tools", registered)
        server_run = MagicMock()
        monkeypatch.setattr(mcp_server.mcp, "run", server_run)

        def main(*argv):
            monkeypatch.setattr("sys.argv", ["pyzotero-mcp", *argv])
            mcp_server.main()
            return server_run, registered

        return main

    def test_defaults(self, run):
        server_run, registered = run()
        server_run.assert_called_once_with(transport="stdio")
        registered.assert_not_called()
        assert mcp_server._LIBRARY == {"library_id": "0", "library_type": "user"}

    def test_group(self, run):
        run("--group", "12345")
        assert mcp_server._LIBRARY == {"library_id": "12345", "library_type": "group"}

    def test_group_must_be_numeric(self, run):
        with pytest.raises(SystemExit):
            run("--group", "my-group")

    def test_http_transport(self, run):
        server_run, _ = run("--transport", "streamable-http", "--port", "9000")
        server_run.assert_called_once_with(
            transport="streamable-http", host="127.0.0.1", port=9000
        )

    def test_writes_refused_off_loopback(self, run):
        with pytest.raises(SystemExit):
            run(
                "--transport",
                "streamable-http",
                "--host",
                "0.0.0.0",  # noqa: S104
                "--enable-writes",
            )

    def test_writes_allowed_on_loopback_http(self, run):
        _, registered = run("--transport", "sse", "--enable-writes")
        registered.assert_called_once()

    def test_read_client_uses_group(self, run):
        run("--group", "42")
        with patch("pyzotero.mcp_server.get_zotero_client") as client:
            mcp_server._read_client()
        client.assert_called_once_with(library_id="42", library_type="group")


# Collections by name or path


NAMED_COLLECTIONS = [
    _collection("PHYS0001", "Physics"),
    _collection("QUAN0001", "Quantum", "PHYS0001"),
    _collection("CHEM0001", "Chemistry"),
    _collection("QUAN0002", "Quantum", "CHEM0001"),
    _collection("READ0001", "To Read"),
]


class TestCollectionResolution:
    @pytest.fixture
    def zot(self):
        mock = MagicMock()
        mock.collections.return_value = NAMED_COLLECTIONS
        mock.everything.side_effect = lambda results: results
        return mock

    @pytest.mark.parametrize(
        ("spec", "key"),
        [
            ("READ0001", "READ0001"),
            ("To Read", "READ0001"),
            ("to read", "READ0001"),
            ("Physics/Quantum", "QUAN0001"),
            ("/chemistry/quantum/", "QUAN0002"),
        ],
    )
    def test_resolves(self, zot, spec, key):
        assert mcp_server._resolve_collection(zot, spec) == key

    def test_ambiguous_name_lists_paths(self, zot):
        with pytest.raises(ValueError, match="ambiguous") as err:
            mcp_server._resolve_collection(zot, "Quantum")
        assert "Physics/Quantum (QUAN0001)" in str(err.value)
        assert "Chemistry/Quantum (QUAN0002)" in str(err.value)

    def test_unknown_suggests(self, zot):
        with pytest.raises(ValueError, match="Did you mean: Physics"):
            mcp_server._resolve_collection(zot, "Physic")

    def test_empty_needs_no_lookup(self, zot):
        assert mcp_server._resolve_collections(zot, None) == []
        zot.collections.assert_not_called()

    def test_search_by_name(self, mock_zot):
        mock_zot.collections.return_value = NAMED_COLLECTIONS
        mcp_server.search(collection="To Read")
        assert mock_zot.collection_items_top.call_args[0][0] == "READ0001"

    def test_write_tool_by_path(self, write_tools, write_zot):
        write_zot.collections.return_value = NAMED_COLLECTIONS
        result = json.loads(
            write_tools["add_to_collection"]("ABC123", "Physics/Quantum")
        )
        assert result["addedTo"] == "QUAN0001"

    def test_unknown_collection_creates_nothing(self, write_tools, write_zot):
        result = json.loads(write_tools["create_item"]("book", collections=["Nowhere"]))
        assert "No collection matches" in result["error"]
        write_zot.create_items.assert_not_called()


# Duplicates, merging and related items


def _record(key, title, item_type="journalArticle", date="2020", **fields):
    return {
        "key": key,
        "version": 5,
        "library": {"type": "user", "id": 123, "name": "me"},
        "meta": {"numChildren": 0},
        "data": {
            "key": key,
            "version": 5,
            "itemType": item_type,
            "title": title,
            "date": date,
            "creators": [],
            "tags": [],
            "collections": [],
            "relations": {},
            **fields,
        },
    }


class TestFindDuplicates:
    def test_groups(self, mock_zot):
        mock_zot.top.return_value = [
            _record("A1", "Paper", DOI="10.1/x"),
            _record("A2", "Paper (preprint)", extra="DOI: https://doi.org/10.1/X"),
            _record("B1", "A Book", "book", "2001"),
            _record("B2", "a book!", "book", "2001"),
            _record("B3", "A Book", "book", "1999"),
            _record("C1", "Erratum", DOI="10.1/c1"),
            _record("C2", "Erratum", DOI="10.1/c2"),
            _record("S1", "A Book", "bookSection", "2001"),
            {"key": "N1", "data": {"key": "N1", "itemType": "note", "note": "x"}},
        ]
        result = json.loads(mcp_server.find_duplicates())
        groups = [
            (g["match"], [i["key"] for i in g["items"]]) for g in result["groups"]
        ]
        assert groups == [("doi", ["A1", "A2"]), ("title", ["B1", "B2"])]
        assert result["total"] == 2

    def test_title_group_covered_by_doi_group_not_repeated(self, mock_zot):
        mock_zot.top.return_value = [
            _record("A1", "Paper", DOI="10.1/x"),
            _record("A2", "Paper", DOI="10.1/X"),
        ]
        result = json.loads(mcp_server.find_duplicates())
        assert [g["match"] for g in result["groups"]] == ["doi"]

    def test_pagination(self, mock_zot):
        mock_zot.top.return_value = [
            _record(f"{n}{i}", f"Title {n}") for n in "ABC" for i in (1, 2)
        ]
        result = json.loads(mcp_server.find_duplicates(limit=1, offset=1))
        assert result["total"] == 3
        assert [i["key"] for i in result["groups"][0]["items"]] == ["B1", "B2"]


@pytest.fixture
def library(write_zot):
    """Back the write client with an in-memory set of items, keyed by item key."""
    items = {}

    def item(key):
        return json.loads(json.dumps(items[key]))

    def update_item(payload):
        data = payload.get("data", payload)
        current = items[data["key"]]
        current["data"].update({k: v for k, v in data.items() if k != "version"})
        current["version"] += 1

    write_zot.item.side_effect = item
    write_zot.update_item.side_effect = update_item
    write_zot.children.side_effect = lambda key: [
        i for i in items.values() if i["data"].get("parentItem") == key
    ]
    return items


class TestMergeItems:
    @pytest.fixture
    def dups(self, library):
        library["KEEP"] = _record(
            "KEEP", "Paper", tags=[{"tag": "a"}], collections=["C1"], volume=""
        )
        library["DUP1"] = _record(
            "DUP1",
            "Paper",
            volume="12",
            abstractNote="Abstract",
            tags=[{"tag": "a"}, {"tag": "b"}],
            collections=["C1", "C2"],
            creators=[{"creatorType": "author", "name": "Org"}],
            relations={"dc:relation": "http://zotero.org/users/123/items/OTHER"},
        )
        library["NOTE"] = {
            "key": "NOTE",
            "version": 2,
            "data": {"key": "NOTE", "itemType": "note", "parentItem": "DUP1"},
        }
        return library

    def test_preview_changes_nothing(self, write_tools, write_zot, dups):
        result = json.loads(write_tools["merge_items"]("KEEP", ["DUP1"]))
        assert result["merged"] is False
        assert result["fillFields"] == {"volume": "12", "abstractNote": "Abstract"}
        assert result["addTags"] == ["b"]
        assert result["addCollections"] == ["C2"]
        assert result["addCreators"] is True
        assert result["moveChildren"] == ["NOTE"]
        write_zot.update_item.assert_not_called()

    def test_confirm_merges(self, write_tools, write_zot, dups):
        result = json.loads(write_tools["merge_items"]("KEEP", ["DUP1"], confirm=True))
        assert result["merged"] is True
        keep = dups["KEEP"]["data"]
        assert keep["volume"] == "12"
        assert [t["tag"] for t in keep["tags"]] == ["a", "b"]
        assert keep["collections"] == ["C1", "C2"]
        assert keep["creators"] == [{"creatorType": "author", "name": "Org"}]
        assert keep["relations"] == {
            "dc:relation": ["http://zotero.org/users/123/items/OTHER"],
            "dc:replaces": ["http://zotero.org/users/123/items/DUP1"],
        }
        assert dups["NOTE"]["data"]["parentItem"] == "KEEP"
        assert dups["DUP1"]["data"]["deleted"] is True
        # every write carried the item's version as it was just before
        for call in write_zot.update_item.call_args_list:
            assert "version" in call[0][0] or "version" in call[0][0].get("data", {})

    def test_unsigned_library_omits_replaces(self, write_tools, dups):
        for item in dups.values():
            item["library"] = {"type": "user", "id": 0}
        write_tools["merge_items"]("KEEP", ["DUP1"], confirm=True)
        assert "dc:replaces" not in dups["KEEP"]["data"]["relations"]

    def test_type_mismatch(self, write_tools, write_zot, dups):
        dups["DUP1"]["data"]["itemType"] = "book"
        result = json.loads(write_tools["merge_items"]("KEEP", ["DUP1"], confirm=True))
        assert "one type" in result["error"]
        write_zot.update_item.assert_not_called()

    def test_child_items_refused(self, write_tools, dups):
        result = json.loads(write_tools["merge_items"]("KEEP", ["NOTE"]))
        assert "only top-level items" in result["error"]

    def test_keep_key_not_a_duplicate(self, write_tools, dups):
        result = json.loads(write_tools["merge_items"]("KEEP", ["KEEP"]))
        assert "not including keep_key" in result["error"]


class TestSetRelated:
    @pytest.fixture
    def pair(self, library):
        library["AAA"] = _record("AAA", "First")
        library["BBB"] = _record("BBB", "Second")
        return library

    def test_link_both_ways(self, write_tools, pair):
        result = json.loads(write_tools["set_related"]("AAA", link=["BBB"]))
        assert result == {"key": "AAA", "related": ["BBB"]}
        assert pair["BBB"]["data"]["relations"]["dc:relation"] == [
            "http://zotero.org/users/123/items/AAA"
        ]

    def test_link_is_idempotent(self, write_tools, write_zot, pair):
        write_tools["set_related"]("AAA", link=["BBB"])
        calls = write_zot.update_item.call_count
        write_tools["set_related"]("AAA", link=["BBB"])
        assert write_zot.update_item.call_count == calls

    def test_unlink(self, write_tools, pair):
        write_tools["set_related"]("AAA", link=["BBB"])
        result = json.loads(write_tools["set_related"]("AAA", unlink=["BBB"]))
        assert result["related"] == []
        assert "dc:relation" not in pair["BBB"]["data"]["relations"]

    def test_group_library_uri(self, write_tools, pair):
        for item in pair.values():
            item["library"] = {"type": "group", "id": 42}
        write_tools["set_related"]("AAA", link=["BBB"])
        assert pair["AAA"]["data"]["relations"]["dc:relation"] == [
            "http://zotero.org/groups/42/items/BBB"
        ]

    def test_unsigned_library_refused(self, write_tools, write_zot, pair):
        pair["AAA"]["library"] = {"type": "user", "id": 0}
        result = json.loads(write_tools["set_related"]("AAA", link=["BBB"]))
        assert "signed in" in result["error"]
        write_zot.update_item.assert_not_called()

    def test_self_link_refused(self, write_tools, pair):
        result = json.loads(write_tools["set_related"]("AAA", link=["AAA"]))
        assert "itself" in result["error"]


# Open-access PDFs for add_by_identifier


class TestAddByDOIWithPDF:
    @pytest.fixture
    def doi_csl(self):
        csl = {"type": "article-journal", "title": "By DOI", "DOI": "10.1/a"}
        with patch("pyzotero._import.fetch_doi_csl", return_value=csl):
            yield

    def test_pdf_attached_to_new_item(self, write_tools, import_zot, doi_csl):
        def fake_download(url, path):
            path.write_bytes(b"%PDF-1.7 test")
            return path

        import_zot.children.return_value = []
        import_zot.upload_attachments.return_value = {
            "success": [{"key": "ATT1"}],
            "failure": [],
            "unchanged": [],
        }
        with (
            patch(
                "pyzotero.mcp_server.open_access_pdf_url",
                return_value="https://x/a.pdf",
            ),
            patch("pyzotero.mcp_server.download_pdf", side_effect=fake_download),
        ):
            result = json.loads(
                write_tools["add_by_identifier"](["10.1/a"], attach_pdf=True)
            )
        pdf = result["items"][0]["pdf"]
        assert pdf["attached"] == "ATT1"
        assert pdf["source"] == "https://x/a.pdf"
        assert pdf["filename"] == "By DOI.pdf"
        template = import_zot.upload_attachments.call_args[0][0][0]
        assert template["title"] == "Full Text PDF"

    def test_no_pdf_found(self, write_tools, import_zot, doi_csl):
        with patch("pyzotero.mcp_server.open_access_pdf_url", return_value=None):
            result = json.loads(
                write_tools["add_by_identifier"](["10.1/a"], attach_pdf=True)
            )
        assert result["items"][0]["pdf"] == "no open-access PDF found"

    def test_download_failure_reported(self, write_tools, import_zot, doi_csl):
        with (
            patch(
                "pyzotero.mcp_server.open_access_pdf_url", return_value="https://x/a"
            ),
            patch(
                "pyzotero.mcp_server.download_pdf",
                side_effect=mcp_server.PDFDownloadError("https://x/a is not a PDF"),
            ),
        ):
            result = json.loads(
                write_tools["add_by_identifier"](["10.1/a"], attach_pdf=True)
            )
        assert result["items"][0]["status"] == "created"
        assert result["items"][0]["pdf"] == "https://x/a is not a PDF"

    def test_existing_items_not_fetched(self, write_tools, import_zot, doi_csl):
        import_zot.items.return_value = [
            {"key": "OLD1", "data": {"key": "OLD1", "DOI": "10.1/a"}}
        ]
        with patch("pyzotero.mcp_server.open_access_pdf_url") as lookup:
            result = json.loads(
                write_tools["add_by_identifier"](["10.1/a"], attach_pdf=True)
            )
        assert result["items"][0]["status"] == "exists"
        lookup.assert_not_called()

    def test_without_attach_pdf_no_lookup(self, write_tools, import_zot, doi_csl):
        with patch("pyzotero.mcp_server.open_access_pdf_url") as lookup:
            write_tools["add_by_identifier"](["10.1/a"])
        lookup.assert_not_called()


# ISBNs, arXiv IDs and citation keys


BOOK = {
    "itemType": "book",
    "title": "Introduction to Algorithms",
    "ISBN": "9780262033848",
    "date": "2009",
    "creators": [{"creatorType": "author", "firstName": "T.", "lastName": "Cormen"}],
}


@pytest.fixture
def book_zot(import_zot):
    """Give the import client a book schema, and serve BOOK for any ISBN."""
    import_zot.item_type_fields.side_effect = lambda t: [
        {"field": f} for f in ("title", "ISBN", "date", "publisher", "extra")
    ]
    with patch("pyzotero._import.fetch_isbn", return_value=dict(BOOK)):
        yield import_zot


def _book(key, isbn, date="2009"):
    return {
        "key": key,
        "data": {
            "key": key,
            "title": "Introduction to Algorithms",
            "date": date,
            "ISBN": isbn,
        },
    }


class TestAddByISBN:
    def test_creates_book(self, write_tools, book_zot):
        result = json.loads(write_tools["add_by_identifier"](["0-262-03384-4"]))
        assert result["items"][0]["type"] == "isbn"
        assert result["items"][0]["status"] == "created"
        assert book_zot.create_items.call_args[0][0][0]["ISBN"] == "9780262033848"

    def test_same_isbn_is_a_duplicate(self, write_tools, book_zot):
        book_zot.top.return_value = [_book("OLD1", "978-0-262-03384-8", date="2010")]
        result = json.loads(write_tools["add_by_identifier"](["9780262033848"]))
        assert result["items"][0]["status"] == "exists"
        assert result["items"][0]["key"] == "OLD1"

    def test_other_edition_is_not(self, write_tools, book_zot):
        book_zot.top.return_value = [_book("OLD1", "0-262-53196-8")]
        result = json.loads(write_tools["add_by_identifier"](["9780262033848"]))
        assert result["items"][0]["status"] == "created"

    def test_book_without_isbn_matches_by_title_and_year(self, write_tools, book_zot):
        book_zot.top.return_value = [_book("OLD1", "")]
        result = json.loads(write_tools["add_by_identifier"](["9780262033848"]))
        assert result["items"][0]["status"] == "exists"

    def test_no_pdf_lookup_for_books(self, write_tools, book_zot):
        with patch("pyzotero.mcp_server.open_access_pdf_url") as lookup:
            result = json.loads(
                write_tools["add_by_identifier"](["9780262033848"], attach_pdf=True)
            )
        assert "DOIs only" in result["items"][0]["pdf"]
        lookup.assert_not_called()


class TestAddByArxivID:
    def test_pdf_uses_arxiv_doi(self, write_tools, import_zot):
        csl = {
            "type": "article-journal",
            "title": "Preprint",
            "DOI": "10.48550/arXiv.2001.00001",
        }
        with (
            patch("pyzotero._import.fetch_doi_csl", return_value=csl),
            patch(
                "pyzotero.mcp_server.open_access_pdf_url", return_value=None
            ) as lookup,
        ):
            result = json.loads(
                write_tools["add_by_identifier"](
                    ["arXiv:2001.00001v2"], attach_pdf=True
                )
            )
        assert result["items"][0]["type"] == "arxiv"
        lookup.assert_called_once_with("10.48550/arXiv.2001.00001")


class TestFindByCitationKey:
    def test_field_and_extra(self, mock_zot):
        by_field = _record("A1", "First", citationKey="lecun2015")
        by_extra = _record("B1", "Second", extra="tex.x: y\nCitation Key: smith2020")
        near_miss = _record("C1", "Third", extra="Citation Key: LeCun2015")

        def items(q, **kwargs):
            return [
                i
                for i in (by_field, by_extra, near_miss)
                if q.lower() in json.dumps(i).lower()
            ]

        mock_zot.items.side_effect = items
        result = json.loads(
            mcp_server.find_by_citation_key(["lecun2015", "smith2020", "nobody2000"])
        )
        assert [i["key"] for i in result["found"]["lecun2015"]] == ["A1"]
        assert [i["key"] for i in result["found"]["smith2020"]] == ["B1"]
        assert result["notFound"] == ["nobody2000"]
        assert mock_zot.items.call_args[1]["qmode"] == "everything"
