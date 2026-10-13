"""MCP server exposing local Zotero library access and Semantic Scholar integration."""

from __future__ import annotations

import argparse
import functools
import hashlib
import html
import json
import sys
from collections.abc import Callable
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, TypeVar

import bibtexparser
from mcp.server.mcpserver import MCPServer

from pyzotero._helpers import (
    LOCAL_KEY_ENV,
    LOCAL_SERVER_ID_ENV,
    annotate_with_library,
    build_doi_index,
    format_creators,
    format_s2_paper,
    get_write_client,
    get_zotero_client,
    normalise_doi,
)
from pyzotero._import import (
    DOILookupError,
    bibtex_to_zotero,
    csl_to_zotero,
    fetch_doi_csl,
    fit_to_schema,
    parse_bibtex,
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

mcp = MCPServer("zotero")

F = TypeVar("F", bound=Callable[..., str])

# The library that every tool uses. main() changes it for --group.
_LIBRARY = {"library_id": "0", "library_type": "user"}

# The local API accepts at most 50 item keys or new items in one request
BATCH_SIZE = 50


def _read_client() -> Any:
    """Return a read-only client for the library that the server uses."""
    return get_zotero_client(**_LIBRARY)


def _json(obj: Any) -> str:
    """Serialise an object to a JSON string."""
    return json.dumps(obj, indent=2)


def _error(msg: str) -> str:
    """Return a JSON-encoded error message."""
    return _json({"error": msg})


def _md5(path: Path) -> str:
    """Return the hex MD5 digest of a file. Read the file in chunks."""
    digest = hashlib.md5()  # noqa: S324
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_s2_tool_lookup(
    doi: str,
    limit: int,
    min_citations: int,
    check_library: bool,
    lookup: Callable[..., dict[str, Any]],
) -> str:
    """Drive the shared Semantic-Scholar-by-DOI lookup flow and return JSON.

    Fetches papers via ``lookup(doi, id_type="doi", limit=limit)``, applies
    the ``min_citations`` filter, optionally annotates each paper with its
    presence in the local Zotero library, and serialises the payload.
    """
    result = lookup(doi, id_type="doi", limit=limit)
    papers = result.get("papers", [])

    if min_citations > 0:
        papers = filter_by_citations(papers, min_citations)

    if not papers:
        return _json({"count": 0, "papers": []})

    if check_library:
        zot = _read_client()
        doi_map = build_doi_index(zot)
        output_papers = annotate_with_library(papers, doi_map)
    else:
        output_papers = [format_s2_paper(p) for p in papers]

    return _json({"count": len(output_papers), "papers": output_papers})


def mcp_error_handler(func: F) -> F:
    """Translate exceptions raised inside an MCP tool to a JSON error payload.

    Semantic Scholar errors get short, specific messages; everything else
    falls back to the exception's str() representation.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        try:
            return func(*args, **kwargs)
        except PaperNotFoundError:
            return _error("Paper not found in Semantic Scholar.")
        except RateLimitError:
            return _error("Rate limit exceeded. Please wait and try again.")
        except SemanticScholarError as e:
            return _error(str(e))
        except Exception as e:
            return _error(str(e))

    return wrapper  # type: ignore[return-value]


@mcp.tool()
@mcp_error_handler
def search(  # noqa: PLR0912
    query: str = "",
    fulltext: bool = False,
    itemtype: str = "",
    collection: str = "",
    tag: str = "",
    limit: int = 50,
    offset: int = 0,
    sort: str = "",
    direction: str = "",
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
        sort: Sort field, e.g. "dateAdded", "dateModified", "title",
            "creator" or "date". For recently added items, use
            sort="dateAdded" with no query.
        direction: "asc" or "desc". The default depends on the sort field.

    Returns:
        JSON with count and items list.

    """
    zot = _read_client()

    params: dict[str, Any] = {"limit": limit}

    if offset > 0:
        params["start"] = offset
    if sort:
        params["sort"] = sort
    if direction:
        params["direction"] = direction
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
            parent_ids = list({item["data"]["parentItem"] for item in attachment_items})
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
        creator_names = format_creators(data.get("creators", []))

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


@mcp.tool()
@mcp_error_handler
def get_item(key: str) -> str:
    """Get a single Zotero item by its key.

    Args:
        key: The Zotero item key.

    Returns:
        JSON with the full item data.

    """
    zot = _read_client()
    result = zot.item(key)
    if not result:
        return _error(f"Item not found: {key}")
    return _json(result)


@mcp.tool()
@mcp_error_handler
def get_children(key: str) -> str:
    """Get child items (attachments, notes) of a Zotero item.

    Args:
        key: The Zotero item key.

    Returns:
        JSON array of child items.

    """
    zot = _read_client()
    results = zot.children(key)
    return _json(results)


@mcp.tool()
@mcp_error_handler
def list_collections(limit: int = 0) -> str:
    """List all collections in the local Zotero library.

    Args:
        limit: Maximum number of collections to return (0 for all).

    Returns:
        JSON array of collections with id, name, items count, and parent info.

    """
    zot = _read_client()

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


@mcp.tool()
@mcp_error_handler
def list_tags(collection: str = "") -> str:
    """List all tags in the Zotero library, optionally filtered by collection.

    Args:
        collection: Optional collection key to filter tags.

    Returns:
        JSON array of tag strings.

    """
    zot = _read_client()
    if collection:
        results = zot.collection_tags(collection)
    else:
        results = zot.tags()
    return _json(results)


@mcp.tool()
@mcp_error_handler
def get_fulltext(key: str) -> str:
    """Get full-text content of a Zotero attachment.

    Args:
        key: The key of an attachment item (not a top-level item).

    Returns:
        JSON with content, indexedPages, and totalPages.

    """
    zot = _read_client()
    result = zot.fulltext_item(key)
    if not result:
        return _error("No full-text content available")
    return _json(result)


class _NoteText(HTMLParser):
    """Collect the text of a Zotero note. Block elements become line breaks."""

    BLOCKS = frozenset(
        {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "pre"}
    )

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag == "li":
            self.parts.append("\n- ")
        elif tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        # A list item or a line break needs only the break before it
        if tag in self.BLOCKS and tag not in {"li", "br"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _note_to_text(note_html: str) -> str:
    """Convert the HTML of a Zotero note to plain text."""
    parser = _NoteText()
    parser.feed(note_html)
    parser.close()
    lines = (line.strip() for line in "".join(parser.parts).splitlines())
    text = "\n".join(lines)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip()


def _text_to_note_html(text: str) -> str:
    """Convert plain text to note HTML: a paragraph per blank-line block."""
    paragraphs = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    return "".join(
        "<p>" + "<br>".join(html.escape(line) for line in p.splitlines()) + "</p>"
        for p in paragraphs
    )


def _format_note(note: dict[str, Any]) -> dict[str, Any]:
    """Summarise a note item for tool output."""
    data = note.get("data", {})
    return {
        "key": data.get("key", ""),
        "parentItem": data.get("parentItem"),
        "text": _note_to_text(data.get("note", "")),
        "tags": [t["tag"] for t in data.get("tags", [])],
        "dateModified": data.get("dateModified", ""),
    }


@mcp.tool()
@mcp_error_handler
def get_notes(key: str = "", query: str = "", limit: int = 25) -> str:
    """Get notes as plain text: an item's notes, or notes that match a query.

    Args:
        key: An item key. Returns that item's child notes. Leave empty to
            search all notes instead.
        query: Text to search for in notes across the library. Without key
            or query, returns the most recently modified notes.
        limit: Maximum number of notes when there is no key (default 25).

    Returns:
        JSON with count and notes list (key, parentItem, text, tags).

    """
    zot = _read_client()
    if key:
        children = zot.everything(zot.children(key))
        notes = [c for c in children if c.get("data", {}).get("itemType") == "note"]
    else:
        params: dict[str, Any] = {"itemType": "note", "limit": limit}
        if query:
            params.update(q=query, qmode="everything")
        else:
            params.update(sort="dateModified", direction="desc")
        notes = zot.items(**params)
    output = [_format_note(n) for n in notes]
    return _json({"count": len(output), "notes": output})


ANNOTATION_FIELDS = {
    "annotationType": "type",
    "annotationText": "text",
    "annotationComment": "comment",
    "annotationColor": "color",
    "annotationPageLabel": "page",
}


@mcp.tool()
@mcp_error_handler
def get_annotations(key: str) -> str:
    """Get the highlights, notes and other annotations made in Zotero's reader.

    Args:
        key: The key of an item, for the annotations on all of its
            attachments, or of a single PDF, EPUB or snapshot attachment.

    Returns:
        JSON with the attachments that have annotations, each with its
        annotations in document order (type, text, comment, color, page,
        tags).

    """
    zot = _read_client()
    item = zot.item(key)
    if item.get("data", {}).get("itemType") == "attachment":
        attachments = [item]
    else:
        attachments = [
            c
            for c in zot.everything(zot.children(key))
            if c.get("data", {}).get("itemType") == "attachment"
        ]
    output = []
    total = 0
    for att in attachments:
        att_data = att.get("data", {})
        annotations = [
            c["data"]
            for c in zot.everything(zot.children(att_data["key"]))
            if c.get("data", {}).get("itemType") == "annotation"
        ]
        if not annotations:
            continue
        annotations.sort(key=lambda a: a.get("annotationSortIndex", ""))
        total += len(annotations)
        output.append(
            {
                "key": att_data["key"],
                "title": att_data.get("title", ""),
                "annotations": [
                    {
                        "key": a["key"],
                        **{
                            out: a[field]
                            for field, out in ANNOTATION_FIELDS.items()
                            if a.get(field)
                        },
                        "tags": [t["tag"] for t in a.get("tags", [])],
                    }
                    for a in annotations
                ],
            }
        )
    return _json({"count": total, "attachments": output})


@mcp.tool()
@mcp_error_handler
def export_bibtex(keys: list[str]) -> str:
    """Export items as BibTeX, using Zotero's own BibTeX exporter.

    Args:
        keys: Item keys to export.

    Returns:
        JSON with count and the BibTeX source.

    """
    zot = _read_client()
    database = bibtexparser.bibdatabase.BibDatabase()
    for chunk in chunks(keys, BATCH_SIZE):
        result = zot.items(itemKey=",".join(chunk), format="bibtex")
        database.entries.extend(result.entries)
    return _json(
        {
            "count": len(database.entries),
            "bibtex": bibtexparser.dumps(database),
        }
    )


@mcp.tool()
@mcp_error_handler
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
    return _run_s2_tool_lookup(
        doi, limit, min_citations, check_library, get_recommendations
    )


@mcp.tool()
@mcp_error_handler
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
    return _run_s2_tool_lookup(
        doi, limit, min_citations, check_library, s2_get_citations
    )


@mcp.tool()
@mcp_error_handler
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
    return _run_s2_tool_lookup(
        doi, limit, min_citations, check_library, s2_get_references
    )


@mcp.tool()
@mcp_error_handler
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
        zot = _read_client()
        doi_map = build_doi_index(zot)
        output_papers = annotate_with_library(papers, doi_map)
    else:
        output_papers = [format_s2_paper(p) for p in papers]

    return _json({"count": len(output_papers), "total": total, "papers": output_papers})


WRITE_KEY_ENV = LOCAL_KEY_ENV
SERVER_ID_ENV = LOCAL_SERVER_ID_ENV


def _write_client() -> Any:
    """Return a Zotero client that has write access to the local API.

    The key comes from the environment, or else from the file that
    ``pyzotero authorize`` writes. See :func:`get_write_client`.
    """
    return get_write_client(**_LIBRARY)


AddTool = Callable[[Callable[..., str]], None]


def _register_item_tools(add: AddTool) -> None:
    """Register tools that create and modify items."""

    def list_item_fields(item_type: str) -> str:
        """List the fields and creator types valid for a Zotero item type.

        Call this before create_item to find the fields that an item type accepts.

        Args:
            item_type: A Zotero item type, e.g. "journalArticle" or "book".

        Returns:
            JSON with the field names and creator types for that item type.

        """
        zot = _read_client()
        return _json(
            {
                "itemType": item_type,
                "fields": [
                    f["field"]  # ty: ignore[invalid-argument-type]
                    for f in zot.item_type_fields(item_type)
                ],
                "creatorTypes": [
                    c["creatorType"]  # ty: ignore[invalid-argument-type]
                    for c in zot.item_creator_types(item_type)
                ],
            }
        )

    def create_item(
        item_type: str,
        fields: dict[str, Any] | None = None,
        creators: list[dict[str, str]] | None = None,
        tags: list[str] | None = None,
        collections: list[str] | None = None,
    ) -> str:
        """Create a new item in the local Zotero library.

        Args:
            item_type: A Zotero item type, e.g. "journalArticle" or "book".
            fields: Field values, e.g. {"title": "...", "date": "2024"}. Use
                list_item_fields to find the fields that the item type accepts.
            creators: Creator dicts, each with creatorType and either
                (firstName, lastName) or name.
            tags: Tag names to attach.
            collections: Collection keys to file the item under.

        Returns:
            JSON with the created item's key, or the server's rejection reason.

        """
        zot = _write_client()
        item: dict[str, Any] = {"itemType": item_type, **(fields or {})}
        if creators:
            item["creators"] = creators
        if tags:
            item["tags"] = [{"tag": tag} for tag in tags]
        if collections:
            item["collections"] = collections
        resp = zot.create_items([item])
        if resp.get("success"):
            return _json({"created": resp["success"]["0"], "itemType": item_type})
        return _json({"error": "Item was rejected", "detail": resp.get("failed")})

    def update_item(key: str, fields: dict[str, Any]) -> str:
        """Update fields on an existing item. Other fields stay unchanged.

        Args:
            key: The item key.
            fields: Field values to set, e.g. {"title": "New title"}. To
                move a note or attachment under another item, set
                {"parentItem": "<key>"}; {"parentItem": false} makes it
                top-level.

        Returns:
            JSON confirming the key and the fields written.

        """
        zot = _write_client()
        item = zot.item(key)
        item["data"].update(fields)
        zot.update_item(item)
        return _json({"updated": key, "fields": sorted(fields)})

    def add_tags(key: str, tags: list[str]) -> str:
        """Add one or more tags to an existing item.

        Args:
            key: The item key.
            tags: Tag names to add.

        Returns:
            JSON confirming the key and the item's full tag list.

        """
        zot = _write_client()
        zot.add_tags(zot.item(key), *tags)
        return _json(
            {"updated": key, "tags": [t["tag"] for t in zot.item(key)["data"]["tags"]]}
        )

    for tool in (list_item_fields, create_item, update_item, add_tags):
        add(tool)


def _register_collection_tools(add: AddTool) -> None:
    """Register tools that create collections and change item membership."""

    def create_collection(name: str, parent: str = "") -> str:
        """Create a new collection.

        Args:
            name: The collection name.
            parent: Optional parent collection key, to nest the new collection.

        Returns:
            JSON with the created collection's key.

        """
        zot = _write_client()
        payload: dict[str, Any] = {"name": name}
        if parent:
            payload["parentCollection"] = parent
        resp = zot.create_collections([payload])
        if resp.get("success"):
            return _json({"created": resp["success"]["0"], "name": name})
        return _json({"error": "Collection was rejected", "detail": resp.get("failed")})

    def add_to_collection(item_key: str, collection_key: str) -> str:
        """File an existing item under a collection.

        Args:
            item_key: The item key.
            collection_key: The collection key.

        Returns:
            JSON confirming the item and collection.

        """
        zot = _write_client()
        zot.addto_collection(collection_key, zot.item(item_key))
        return _json({"item": item_key, "addedTo": collection_key})

    def remove_from_collection(item_key: str, collection_key: str) -> str:
        """Remove an item from a collection. The item itself is unchanged.

        This is the inverse of add_to_collection. The item stays in the
        library and in its other collections.

        Args:
            item_key: The item key.
            collection_key: The collection key.

        Returns:
            JSON confirming the item and collection.

        """
        zot = _write_client()
        zot.deletefrom_collection(collection_key, zot.item(item_key))
        return _json({"item": item_key, "removedFrom": collection_key})

    def move_to_collection(
        item_key: str, from_collection_key: str, to_collection_key: str
    ) -> str:
        """Move an item from one collection to another in one step.

        Prefer this over get_item followed by update_item with a rewritten
        collections list: membership of other collections is kept. If the
        item is not in the source collection, it is added to the destination
        all the same.

        Args:
            item_key: The item key.
            from_collection_key: The key of the collection to remove the item from.
            to_collection_key: The key of the collection to add the item to.

        Returns:
            JSON confirming the item, the source and the destination.

        """
        zot = _write_client()
        zot.moveto_collection(
            from_collection_key, to_collection_key, zot.item(item_key)
        )
        return _json(
            {
                "item": item_key,
                "movedFrom": from_collection_key,
                "movedTo": to_collection_key,
            }
        )

    def update_collection(key: str, name: str = "", parent: str | None = None) -> str:
        """Rename a collection, or move it under another collection.

        The collection keeps its key, its subcollections and its items.

        Args:
            key: The collection key.
            name: The new name. Leave empty to keep the current name.
            parent: The key of the new parent collection, or "" to make the
                collection top-level. Omit to keep the current parent.

        Returns:
            JSON with the collection's key, name and parent.

        """
        if not name and parent is None:
            msg = "Give a new name, a new parent, or both"
            raise ValueError(msg)
        if parent == key:
            msg = "A collection cannot be its own parent"
            raise ValueError(msg)
        zot = _write_client()
        data = zot.collection(key)["data"]
        if name:
            data["name"] = name
        if parent is not None:
            data["parentCollection"] = parent or False
        zot.update_collection(data)
        return _json(
            {
                "updated": key,
                "name": data["name"],
                "parent": data.get("parentCollection") or None,
            }
        )

    for tool in (
        create_collection,
        update_collection,
        add_to_collection,
        remove_from_collection,
        move_to_collection,
    ):
        add(tool)


def _register_attachment_tools(add: AddTool) -> None:
    """Register the file attachment tool."""

    def add_attachment(item_key: str, file_path: str, title: str = "") -> str:
        """Attach a file on disk to an existing Zotero item.

        Zotero copies the file into its storage. The attachment stays
        available if the source file moves or is deleted. If the library
        syncs, the attachment also syncs.

        Args:
            item_key: The key of the item that gets the attachment.
            file_path: An absolute path to the file. This server runs as a
                subprocess of the MCP client, so its working directory is not
                yours. A relative path would point to an unknown location.
                Thus the server rejects relative paths.
            title: Optional title for the attachment. The default is the
                filename.

        Returns:
            JSON with the key of the new attachment, or the reason for a
            rejection. If the file is already attached to the item, the
            result reports it as unchanged and no copy occurs. Thus a retried
            call is safe. The server does not replace the contents of an
            attachment: a file with different contents becomes a second
            attachment.

        """
        path = Path(file_path)
        if not path.is_absolute():
            msg = f"file_path must be an absolute path, got {file_path!r}"
            raise ValueError(msg)
        if not path.is_file():
            msg = f"No file at {file_path}"
            raise FileNotFoundError(msg)
        zot = _write_client()
        # An upload always creates a new attachment item. Without a check, a
        # call that stops or is retried would attach the file a second time.
        # Thus, compare the file with the item's attachments first.
        checksum = _md5(path)
        for child in zot.children(item_key):
            data = child.get("data", {})
            if data.get("filename") == path.name and data.get("md5") == checksum:
                return _json(
                    {
                        "unchanged": child["key"],
                        "parent": item_key,
                        "detail": "this file is already attached to the item",
                    }
                )
        # item_template() is not available here: the local API has no
        # /items/new. Thus, build the attachment template directly. The
        # upload code finds the contentType from the path.
        template = {
            "itemType": "attachment",
            "linkMode": "imported_file",
            "title": title or path.name,
            "filename": str(path),
            "note": "",
            "tags": [],
            "relations": {},
        }
        result = zot.upload_attachments([template], item_key)
        if result["success"]:
            return _json(
                {
                    "attached": result["success"][0]["key"],
                    "parent": item_key,
                    "filename": path.name,
                }
            )
        if result["unchanged"]:
            return _json(
                {
                    "unchanged": item_key,
                    "detail": "an identical file is already attached",
                }
            )
        detail = result["failure"][0] if result["failure"] else None
        return _json({"error": "Attachment was rejected", "detail": detail})

    add(add_attachment)


def _register_note_tools(add: AddTool) -> None:
    """Register the tools that create and edit notes."""

    def create_note(
        content: str,
        parent_key: str = "",
        is_html: bool = False,
        tags: list[str] | None = None,
        collections: list[str] | None = None,
    ) -> str:
        """Create a note, attached to an item or standalone.

        Args:
            content: The note text. Plain text by default: blank lines
                separate paragraphs.
            parent_key: The key of the item that the note belongs to. Leave
                empty for a standalone note.
            is_html: If true, content is HTML and is stored as given.
            tags: Tag names to attach.
            collections: Collection keys, for a standalone note only. A child
                note belongs to its parent's collections.

        Returns:
            JSON with the created note's key, or the server's rejection reason.

        """
        if parent_key and collections:
            msg = "A child note cannot be filed in collections; its parent is"
            raise ValueError(msg)
        zot = _write_client()
        note: dict[str, Any] = {
            "itemType": "note",
            "note": content if is_html else _text_to_note_html(content),
            "tags": [{"tag": t} for t in tags or []],
        }
        if parent_key:
            note["parentItem"] = parent_key
        if collections:
            note["collections"] = collections
        resp = zot.create_items([note])
        if resp.get("success"):
            return _json(
                {"created": resp["success"]["0"], "parent": parent_key or None}
            )
        return _json({"error": "Note was rejected", "detail": resp.get("failed")})

    def update_note(key: str, content: str, is_html: bool = False) -> str:
        """Replace the text of a note.

        Args:
            key: The note key.
            content: The new note text. Plain text by default: blank lines
                separate paragraphs.
            is_html: If true, content is HTML and is stored as given.

        Returns:
            JSON confirming the key.

        """
        zot = _write_client()
        item = zot.item(key)
        if item["data"].get("itemType") != "note":
            msg = f"Item {key} is not a note"
            raise ValueError(msg)
        item["data"]["note"] = content if is_html else _text_to_note_html(content)
        zot.update_item(item)
        return _json({"updated": key})

    add(create_note)
    add(update_note)


IF_EXISTS_MODES = ("skip", "file", "create")


def _title_key(title: str) -> str:
    """Normalise a title for comparison: lower case, letters and digits only."""
    return "".join(ch for ch in title.casefold() if ch.isalnum())


def _item_doi(item: dict[str, Any]) -> str:
    """Return an item's normalised DOI, from its DOI field or from Extra."""
    if item.get("DOI"):
        return normalise_doi(item["DOI"])
    for line in item.get("extra", "").splitlines():
        label, _, value = line.partition(":")
        if label.strip().upper() == "DOI" and value.strip():
            return normalise_doi(value)
    return ""


def _find_existing(zot: Any, item: dict[str, Any]) -> dict[str, Any] | None:
    """Return the library item that ``item`` duplicates, by DOI or by title.

    Items with a DOI match on DOI only. Items without one match on title,
    and on year when both have a date.
    """
    doi = _item_doi(item)
    if doi:
        for found in zot.items(q=doi, qmode="everything", limit=25):
            if _item_doi(found.get("data", {})) == doi:
                return found
        return None
    title = item.get("title") or next(
        (v for k, v in item.items() if k in {"caseName", "nameOfAct", "subject"}), ""
    )
    if not title:
        return None
    want = _title_key(title)
    year = item.get("date", "")[:4]
    for found in zot.top(q=title, limit=25):
        data = found.get("data", {})
        if _title_key(data.get("title", "")) != want:
            continue
        found_year = data.get("date", "")[:4]
        if not year or not found_year or year == found_year:
            return found
    return None


def _create_imported(  # noqa: PLR0912
    zot: Any,
    items: list[dict[str, Any]],
    collections: list[str] | None,
    tags: list[str] | None,
    if_exists: str,
) -> list[dict[str, Any]]:
    """Fit converted items to the schema, skip or file duplicates, create the rest.

    Returns one result per item, in input order.
    """
    if if_exists not in IF_EXISTS_MODES:
        msg = f"if_exists must be one of {', '.join(IF_EXISTS_MODES)}"
        raise ValueError(msg)
    schema: dict[str, tuple[set[str], list[str]]] = {}
    results: list[dict[str, Any]] = []
    pending: list[tuple[int, dict[str, Any]]] = []
    for item in items:
        item_type = item["itemType"]
        if item_type not in schema:
            schema[item_type] = (
                {f["field"] for f in zot.item_type_fields(item_type)},
                [c["creatorType"] for c in zot.item_creator_types(item_type)],
            )
        fitted, dropped = fit_to_schema(item, *schema[item_type])
        result: dict[str, Any] = {
            "title": fitted.get("title", ""),
            "itemType": item_type,
        }
        if dropped:
            result["droppedFields"] = dropped
        existing = None if if_exists == "create" else _find_existing(zot, fitted)
        if existing is not None:
            result["key"] = existing["key"]
            result["status"] = "exists"
            if if_exists == "file":
                missing = [
                    c
                    for c in collections or []
                    if c not in existing["data"].get("collections", [])
                ]
                for collection in missing:
                    zot.addto_collection(collection, existing)
                    existing = zot.item(existing["key"])
                if tags:
                    zot.add_tags(existing, *tags)
                if missing or tags:
                    result["status"] = "filed"
        else:
            if collections:
                fitted["collections"] = collections
            fitted["tags"] = fitted.get("tags", []) + [{"tag": t} for t in tags or []]
            pending.append((len(results), fitted))
        results.append(result)
    for batch in chunks(pending, BATCH_SIZE):
        resp = zot.create_items([item for _, item in batch])
        for position, (index, _) in enumerate(batch):
            key = resp.get("success", {}).get(str(position))
            if key:
                results[index].update(key=key, status="created")
            else:
                failure = resp.get("failed", {}).get(str(position), {})
                results[index].update(
                    status="failed", error=failure.get("message", "rejected")
                )
    return results


def _import_summary(results: list[dict[str, Any]]) -> str:
    """Return import results as JSON, with a count for each status."""
    counts: dict[str, int] = {}
    for result in results:
        counts[result["status"]] = counts.get(result["status"], 0) + 1
    return _json({"counts": counts, "items": results})


def _lookup_doi(doi: str) -> dict[str, Any] | str:
    """Return the converted item for a DOI, or the reason that the lookup failed."""
    try:
        return csl_to_zotero(fetch_doi_csl(doi))
    except DOILookupError as e:
        return str(e)


def _register_import_tools(add: AddTool) -> None:
    """Register the tools that add items from identifiers and citation data."""

    def add_by_doi(
        dois: list[str],
        collections: list[str] | None = None,
        tags: list[str] | None = None,
        if_exists: str = "skip",
    ) -> str:
        """Add items by DOI, with metadata from the DOI's registration agency.

        doi.org supplies the metadata: Crossref, DataCite or mEDRA,
        depending on the DOI.

        Args:
            dois: DOIs, bare or as doi.org URLs.
            collections: Collection keys to file the new items under.
            tags: Tag names to attach to the new items.
            if_exists: What to do when the library already has an item with
                the DOI: "skip" (the default) reports it and changes nothing,
                "file" adds it to the collections and tags given, and
                "create" adds a duplicate.

        Returns:
            JSON with a count for each status, and a result for each DOI:
            created, exists, filed or failed, with the item key.

        """
        zot = _write_client()
        lookups = [(doi, _lookup_doi(doi)) for doi in dois]
        converted = [found for _, found in lookups if isinstance(found, dict)]
        created = iter(_create_imported(zot, converted, collections, tags, if_exists))
        results = [
            {"doi": doi, **next(created)}
            if isinstance(found, dict)
            else {"doi": doi, "status": "failed", "error": found}
            for doi, found in lookups
        ]
        return _import_summary(results)

    def import_items(
        data: str = "",
        file_path: str = "",
        format: str = "bibtex",
        collections: list[str] | None = None,
        tags: list[str] | None = None,
        if_exists: str = "skip",
    ) -> str:
        """Add items from BibTeX or CSL JSON.

        Args:
            data: The BibTeX or CSL JSON source. Give this or file_path.
            file_path: An absolute path to a .bib or .json file, in place of
                data. The server's working directory is not yours, so
                relative paths are rejected.
            format: "bibtex" or "csljson".
            collections: Collection keys to file the new items under.
            tags: Tag names to attach to the new items, besides any that
                the source gives (BibTeX keywords).
            if_exists: What to do when the library already has the item (by
                DOI, or else by title and year): "skip" (the default)
                reports it and changes nothing, "file" adds it to the
                collections and tags given, and "create" adds a duplicate.

        Returns:
            JSON with a count for each status, and a result for each entry:
            created, exists, filed or failed, with the item key.

        """
        if bool(data) == bool(file_path):
            msg = "Give either data or file_path"
            raise ValueError(msg)
        if file_path:
            path = Path(file_path)
            if not path.is_absolute():
                msg = f"file_path must be an absolute path, got {file_path!r}"
                raise ValueError(msg)
            data = path.read_text(encoding="utf-8")
        if format == "bibtex":
            converted = [bibtex_to_zotero(e) for e in parse_bibtex(data)]
        elif format == "csljson":
            records = json.loads(data)
            if isinstance(records, dict):
                records = [records]
            converted = [csl_to_zotero(r) for r in records]
        else:
            msg = 'format must be "bibtex" or "csljson"'
            raise ValueError(msg)
        if not converted:
            msg = f"No entries found in the {format} source"
            raise ValueError(msg)
        zot = _write_client()
        return _import_summary(
            _create_imported(zot, converted, collections, tags, if_exists)
        )

    add(add_by_doi)
    add(import_items)


def _register_delete_tools(add: AddTool) -> None:
    """Register the delete tools. This runs only for --enable-deletes."""

    def delete_item(key: str) -> str:
        """Permanently delete an item from the local Zotero library.

        You cannot undo this operation. The local API erases the item. It
        does not move the item to the trash. If the library syncs, the
        deletion also syncs. Get the user's confirmation before you call
        this tool.

        Args:
            key: The item key.

        Returns:
            JSON confirming the deleted key.

        """
        zot = _write_client()
        zot.delete_item(zot.item(key))
        return _json({"deleted": key})

    add(delete_item)


def register_write_tools(
    server: MCPServer, *, enable_deletes: bool = False
) -> list[str]:
    """Register the write tools on ``server``. Return the registered names.

    Registration is the gate for writes, not a check in each tool. A tool
    that is not registered does not appear in the model's tool list. Thus
    content in the library cannot cause a call to it. Nothing here runs
    unless ``main()`` receives --enable-writes or --enable-deletes.
    """
    registered: list[str] = []

    def add(func: Callable[..., str]) -> None:
        server.tool()(mcp_error_handler(func))
        registered.append(func.__name__)  # ty: ignore[unresolved-attribute]

    _register_item_tools(add)
    _register_collection_tools(add)
    _register_attachment_tools(add)
    _register_note_tools(add)
    _register_import_tools(add)
    if enable_deletes:
        _register_delete_tools(add)
    return registered


LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")


def main() -> None:
    """Run the MCP server, over stdio unless --transport says otherwise."""
    parser = argparse.ArgumentParser(
        prog="pyzotero-mcp",
        description="MCP server exposing a local Zotero library. Read-only by default.",
    )
    parser.add_argument(
        "--enable-writes",
        action="store_true",
        help="register tools that create and modify library items",
    )
    parser.add_argument(
        "--enable-deletes",
        action="store_true",
        help=(
            "additionally register delete_item. Deletions via the local API are "
            "permanent, not moves to the trash. Implies --enable-writes"
        ),
    )
    parser.add_argument(
        "--group",
        metavar="ID",
        help="use the group library with this numeric ID, not your personal library",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse"],
        default="stdio",
        help="the MCP transport (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="the address to listen on for an HTTP transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="the port to listen on for an HTTP transport (default: 8000)",
    )
    args = parser.parse_args()
    if args.group is not None:
        if not args.group.isdigit():
            parser.error(f"--group takes a numeric group ID, got {args.group!r}")
        _LIBRARY.update(library_id=args.group, library_type="group")
    writes = args.enable_writes or args.enable_deletes
    http = args.transport != "stdio"
    # An HTTP server has no authentication. Off the loopback interface, other
    # machines could reach it, so it must not be able to change the library.
    if http and writes and args.host not in LOOPBACK_HOSTS:
        parser.error("write tools are only available on a loopback --host")
    if writes:
        names = register_write_tools(mcp, enable_deletes=args.enable_deletes)
        print(f"pyzotero-mcp: write tools enabled: {', '.join(names)}", file=sys.stderr)
    if http:
        mcp.run(transport=args.transport, host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
