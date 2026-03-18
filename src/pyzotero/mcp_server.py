"""MCP server exposing local Zotero library access and Semantic Scholar integration."""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from pyzotero._helpers import (
    annotate_with_library,
    build_doi_index,
    format_s2_paper,
    get_zotero_client,
)
from pyzotero.semantic_scholar import (
    PaperNotFoundError,
    RateLimitError,
    SemanticScholarError,
    filter_by_citations,
    get_citations as s2_get_citations,
    get_recommendations,
    get_references as s2_get_references,
    search_papers,
)
from pyzotero.zotero import chunks

mcp = FastMCP("zotero")


def _json(obj: Any) -> str:
    """Serialise an object to a JSON string."""
    return json.dumps(obj, indent=2)


def _error(msg: str) -> str:
    """Return a JSON-encoded error message."""
    return _json({"error": msg})


@mcp.tool()
def search(  # noqa: PLR0912, PLR0915
    query: str = "",
    fulltext: bool = False,
    itemtype: str = "",
    collection: str = "",
    tag: str = "",
    limit: int = 50,
    offset: int = 0,
) -> str:
    """Search the local Zotero library.

    Args:
        query: Search query string.
        fulltext: If true, search full-text content including PDFs.
        itemtype: Filter by item type. Use || to combine types, e.g. "book || journalArticle".
        collection: Filter by collection key.
        tag: Filter by tag. Use comma-separated values for AND search, e.g. "climate,adaptation".
        limit: Maximum results to return (default 50).
        offset: Number of results to skip for pagination.

    Returns:
        JSON with count and items list.

    """
    try:
        zot = get_zotero_client()

        params: dict[str, Any] = {"limit": limit}

        if offset > 0:
            params["start"] = offset
        if query:
            params["q"] = query
        if fulltext:
            params["qmode"] = "everything"
        if itemtype:
            params["itemType"] = itemtype
        if tag:
            # Split comma-separated tags for AND search
            tags = [t.strip() for t in tag.split(",")]
            params["tag"] = tags if len(tags) > 1 else tags[0]

        if fulltext:
            if collection:
                results = zot.collection_items(collection, **params)
            else:
                results = zot.items(**params)

            # Retrieve parent items for attachment matches
            top_level_items = []
            attachment_items = []

            for item in results:
                data = item.get("data", {})
                if "parentItem" in data:
                    attachment_items.append(item)
                else:
                    top_level_items.append(item)

            parent_items = []
            if attachment_items:
                parent_ids = list(
                    {item["data"]["parentItem"] for item in attachment_items}
                )
                for chunk in chunks(parent_ids, 50):
                    parent_items.extend(zot.get_subset(chunk))

            all_items = top_level_items + parent_items
            items_dict = {item["data"]["key"]: item for item in all_items}
            results = list(items_dict.values())
        elif collection:
            results = zot.collection_items_top(collection, **params)
        else:
            results = zot.top(**params)

        output_items = []
        for item in results:
            data = item.get("data", {})
            creators = data.get("creators", [])
            creator_names = []
            for creator in creators:
                if "lastName" in creator:
                    if "firstName" in creator:
                        creator_names.append(
                            f"{creator['firstName']} {creator['lastName']}"
                        )
                    else:
                        creator_names.append(creator["lastName"])
                elif "name" in creator:
                    creator_names.append(creator["name"])

            output_items.append(
                {
                    "key": data.get("key", ""),
                    "itemType": data.get("itemType", "Unknown"),
                    "title": data.get("title", "No title"),
                    "creators": creator_names,
                    "date": data.get("date", ""),
                    "publication": data.get("publicationTitle", ""),
                    "volume": data.get("volume", ""),
                    "issue": data.get("issue", ""),
                    "doi": data.get("DOI", ""),
                    "url": data.get("url", ""),
                }
            )

        return _json({"count": len(output_items), "items": output_items})
    except Exception as e:
        return _error(str(e))


@mcp.tool()
def get_item(key: str) -> str:
    """Get a single Zotero item by its key.

    Args:
        key: The Zotero item key.

    Returns:
        JSON with the full item data.

    """
    try:
        zot = get_zotero_client()
        result = zot.item(key)
        if not result:
            return _error(f"Item not found: {key}")
        return _json(result)
    except Exception as e:
        return _error(str(e))


@mcp.tool()
def get_children(key: str) -> str:
    """Get child items (attachments, notes) of a Zotero item.

    Args:
        key: The Zotero item key.

    Returns:
        JSON array of child items.

    """
    try:
        zot = get_zotero_client()
        results = zot.children(key)
        return _json(results)
    except Exception as e:
        return _error(str(e))


@mcp.tool()
def list_collections(limit: int = 0) -> str:
    """List all collections in the local Zotero library.

    Args:
        limit: Maximum number of collections to return (0 for all).

    Returns:
        JSON array of collections with id, name, items count, and parent info.

    """
    try:
        zot = get_zotero_client()

        params: dict[str, Any] = {}
        if limit > 0:
            params["limit"] = limit

        collections = zot.collections(**params)

        # Build parent name lookup
        collection_map = {}
        for coll in collections:
            data = coll.get("data", {})
            ckey = data.get("key", "")
            cname = data.get("name", "")
            if ckey:
                collection_map[ckey] = cname or None

        output = []
        for coll in collections:
            data = coll.get("data", {})
            meta = coll.get("meta", {})
            parent_key = data.get("parentCollection", "")

            obj: dict[str, Any] = {
                "id": data.get("key", ""),
                "name": data.get("name", "") or None,
                "items": meta.get("numItems", 0),
            }

            if parent_key:
                obj["parent"] = {
                    "id": parent_key,
                    "name": collection_map.get(parent_key),
                }
            else:
                obj["parent"] = None

            output.append(obj)

        return _json(output)
    except Exception as e:
        return _error(str(e))


@mcp.tool()
def list_tags(collection: str = "") -> str:
    """List all tags in the Zotero library, optionally filtered by collection.

    Args:
        collection: Optional collection key to filter tags.

    Returns:
        JSON array of tag strings.

    """
    try:
        zot = get_zotero_client()
        if collection:
            results = zot.collection_tags(collection)
        else:
            results = zot.tags()
        return _json(results)
    except Exception as e:
        return _error(str(e))


@mcp.tool()
def get_fulltext(key: str) -> str:
    """Get full-text content of a Zotero attachment.

    Args:
        key: The key of an attachment item (not a top-level item).

    Returns:
        JSON with content, indexedPages, and totalPages.

    """
    try:
        zot = get_zotero_client()
        result = zot.fulltext_item(key)
        if not result:
            return _error("No full-text content available")
        return _json(result)
    except Exception as e:
        return _error(str(e))


@mcp.tool()
def find_related(
    doi: str,
    limit: int = 20,
    min_citations: int = 0,
    check_library: bool = True,
) -> str:
    """Find papers related to a given paper using Semantic Scholar.

    Uses SPECTER2 embeddings for semantic similarity.

    Args:
        doi: DOI of the paper.
        limit: Maximum results (default 20, max 500).
        min_citations: Minimum citation count filter.
        check_library: If true, annotate results with local Zotero presence.

    Returns:
        JSON with count and papers list.

    """
    try:
        result = get_recommendations(doi, id_type="doi", limit=limit)
        papers = result.get("papers", [])

        if min_citations > 0:
            papers = filter_by_citations(papers, min_citations)

        if not papers:
            return _json({"count": 0, "papers": []})

        if check_library:
            zot = get_zotero_client()
            doi_map = build_doi_index(zot)
            output_papers = annotate_with_library(papers, doi_map)
        else:
            output_papers = [format_s2_paper(p) for p in papers]

        return _json({"count": len(output_papers), "papers": output_papers})
    except PaperNotFoundError:
        return _error("Paper not found in Semantic Scholar.")
    except RateLimitError:
        return _error("Rate limit exceeded. Please wait and try again.")
    except SemanticScholarError as e:
        return _error(str(e))
    except Exception as e:
        return _error(str(e))


@mcp.tool()
def get_citations(
    doi: str,
    limit: int = 100,
    min_citations: int = 0,
    check_library: bool = True,
) -> str:
    """Find papers that cite a given paper using Semantic Scholar.

    Args:
        doi: DOI of the paper.
        limit: Maximum results (default 100, max 1000).
        min_citations: Minimum citation count filter.
        check_library: If true, annotate results with local Zotero presence.

    Returns:
        JSON with count and papers list.

    """
    try:
        result = s2_get_citations(doi, id_type="doi", limit=limit)
        papers = result.get("papers", [])

        if min_citations > 0:
            papers = filter_by_citations(papers, min_citations)

        if not papers:
            return _json({"count": 0, "papers": []})

        if check_library:
            zot = get_zotero_client()
            doi_map = build_doi_index(zot)
            output_papers = annotate_with_library(papers, doi_map)
        else:
            output_papers = [format_s2_paper(p) for p in papers]

        return _json({"count": len(output_papers), "papers": output_papers})
    except PaperNotFoundError:
        return _error("Paper not found in Semantic Scholar.")
    except RateLimitError:
        return _error("Rate limit exceeded. Please wait and try again.")
    except SemanticScholarError as e:
        return _error(str(e))
    except Exception as e:
        return _error(str(e))


@mcp.tool()
def get_references(
    doi: str,
    limit: int = 100,
    min_citations: int = 0,
    check_library: bool = True,
) -> str:
    """Find papers referenced by a given paper using Semantic Scholar.

    Args:
        doi: DOI of the paper.
        limit: Maximum results (default 100, max 1000).
        min_citations: Minimum citation count filter.
        check_library: If true, annotate results with local Zotero presence.

    Returns:
        JSON with count and papers list.

    """
    try:
        result = s2_get_references(doi, id_type="doi", limit=limit)
        papers = result.get("papers", [])

        if min_citations > 0:
            papers = filter_by_citations(papers, min_citations)

        if not papers:
            return _json({"count": 0, "papers": []})

        if check_library:
            zot = get_zotero_client()
            doi_map = build_doi_index(zot)
            output_papers = annotate_with_library(papers, doi_map)
        else:
            output_papers = [format_s2_paper(p) for p in papers]

        return _json({"count": len(output_papers), "papers": output_papers})
    except PaperNotFoundError:
        return _error("Paper not found in Semantic Scholar.")
    except RateLimitError:
        return _error("Rate limit exceeded. Please wait and try again.")
    except SemanticScholarError as e:
        return _error(str(e))
    except Exception as e:
        return _error(str(e))


@mcp.tool()
def search_semantic_scholar(
    query: str,
    limit: int = 20,
    year: str = "",
    open_access: bool = False,
    sort: str = "",
    min_citations: int = 0,
    check_library: bool = True,
) -> str:
    """Search for papers on Semantic Scholar.

    Args:
        query: Search query string.
        limit: Maximum results (default 20, max 100).
        year: Year filter, e.g. "2020", "2018-2022", or "2020-".
        open_access: Only return open access papers.
        sort: Sort by "citations" or "year" (descending).
        min_citations: Minimum citation count filter.
        check_library: If true, annotate results with local Zotero presence.

    Returns:
        JSON with count, total, and papers list.

    """
    try:
        result = search_papers(
            query,
            limit=limit,
            year=year or None,
            open_access_only=open_access,
            sort=sort or None,
            min_citations=min_citations,
        )
        papers = result.get("papers", [])
        total = result.get("total", len(papers))

        if not papers:
            return _json({"count": 0, "total": total, "papers": []})

        if check_library:
            zot = get_zotero_client()
            doi_map = build_doi_index(zot)
            output_papers = annotate_with_library(papers, doi_map)
        else:
            output_papers = [format_s2_paper(p) for p in papers]

        return _json(
            {"count": len(output_papers), "total": total, "papers": output_papers}
        )
    except RateLimitError:
        return _error("Rate limit exceeded. Please wait and try again.")
    except SemanticScholarError as e:
        return _error(str(e))
    except Exception as e:
        return _error(str(e))


def main() -> None:
    """Run the MCP server over stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
