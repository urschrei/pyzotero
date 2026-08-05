"""Tests for the pyzotero MCP server tools."""

# ruff: noqa: PLR2004, PLC0415

from __future__ import annotations

import hashlib
import json
from unittest.mock import MagicMock, patch

import pytest


# The mcp extra requires Python >= 3.10, so skip the entire module on older versions
mcp_server = pytest.importorskip(
    "pyzotero.mcp_server", reason="mcp extra requires Python >= 3.10"
)


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
    mock.everything.return_value = ITEMS_FIXTURE
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
    """Minimal stand-in for FastMCP that records what gets registered."""

    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


@pytest.fixture
def write_zot():
    """Patch _write_client to return a mock, and return the mock."""
    mock = MagicMock()
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


class TestWriteClient:
    def test_missing_key_raises_with_remedy(self, monkeypatch):
        monkeypatch.delenv(mcp_server.WRITE_KEY_ENV, raising=False)
        with pytest.raises(RuntimeError, match="pyzotero authorize"):
            mcp_server._write_client()

    def test_key_and_server_id_passed_through(self, monkeypatch):
        monkeypatch.setenv(mcp_server.WRITE_KEY_ENV, "key123")
        monkeypatch.setenv(mcp_server.SERVER_ID_ENV, "srv123")
        with patch("pyzotero.mcp_server.get_zotero_client") as client:
            mcp_server._write_client()
        client.assert_called_once_with(server_id="srv123", local_api_key="key123")

    def test_absent_server_id_is_none(self, monkeypatch):
        monkeypatch.setenv(mcp_server.WRITE_KEY_ENV, "key123")
        monkeypatch.delenv(mcp_server.SERVER_ID_ENV, raising=False)
        with patch("pyzotero.mcp_server.get_zotero_client") as client:
            mcp_server._write_client()
        client.assert_called_once_with(server_id=None, local_api_key="key123")


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
