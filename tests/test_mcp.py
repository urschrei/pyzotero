"""Tests for the pyzotero MCP server tools."""

# ruff: noqa: PLR2004, PLC0415

from __future__ import annotations

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
