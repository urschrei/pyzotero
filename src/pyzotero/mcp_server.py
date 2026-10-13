"""MCP server exposing local Zotero library access and Semantic Scholar integration."""

from __future__ import annotations

import argparse
import difflib
import functools
import hashlib
import html
import json
import re
import sys
import tempfile
from collections import defaultdict
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
    MetadataLookupError,
    PDFDownloadError,
    bibtex_to_zotero,
    csl_to_zotero,
    download_pdf,
    fit_to_schema,
    isbn_set,
    lookup_identifier,
    open_access_pdf_url,
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


def _collection_paths(zot: Any) -> dict[str, tuple[str, str]]:
    """Map each collection key to its name and its "parent/child" path."""
    data = {c["data"]["key"]: c["data"] for c in zot.everything(zot.collections())}
    paths: dict[str, tuple[str, str]] = {}
    for key, coll in data.items():
        names, seen, current = [], set(), coll
        # The seen set guards against a parent cycle in corrupt data
        while current and current["key"] not in seen:
            seen.add(current["key"])
            names.append(current["name"])
            current = data.get(current.get("parentCollection") or "")
        paths[key] = (coll["name"], "/".join(reversed(names)))
    return paths


def _resolve_collections(zot: Any, specs: list[str] | None) -> list[str]:
    """Resolve collection keys, names or "parent/child" paths to keys.

    A key is matched first, then a full path, then a name, each exactly and
    then ignoring case.

    Raises:
        ValueError: a spec matches no collection, or more than one.

    """
    if not specs:
        return []
    paths = _collection_paths(zot)
    keys = []
    for raw in specs:
        spec = raw.strip().strip("/")
        if spec in paths:
            keys.append(spec)
            continue
        matches: list[str] = []
        for fold in (lambda x: x, str.casefold):
            for index in (1, 0):
                target = fold(spec)
                matches = [k for k, v in paths.items() if fold(v[index]) == target]
                if matches:
                    break
            if matches:
                break
        if len(matches) > 1:
            options = ", ".join(f"{paths[k][1]} ({k})" for k in matches)
            msg = f"Collection {raw!r} is ambiguous; give a path or key: {options}"
            raise ValueError(msg)
        if not matches:
            close = difflib.get_close_matches(spec, [v[1] for v in paths.values()])
            hint = f" Did you mean: {', '.join(close)}?" if close else ""
            msg = f"No collection matches {raw!r}.{hint}"
            raise ValueError(msg)
        keys.append(matches[0])
    return keys


def _resolve_collection(zot: Any, spec: str) -> str:
    """Resolve one collection key, name or path to a key."""
    return _resolve_collections(zot, [spec])[0]


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
        collection: Filter by collection: a key, a name, or a "parent/child" path.
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
    if collection:
        collection = _resolve_collection(zot, collection)
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
        collection: Optional collection to filter tags: a key, a name, or a
            "parent/child" path.

    Returns:
        JSON array of tag strings.

    """
    zot = _read_client()
    if collection:
        results = zot.collection_tags(_resolve_collection(zot, collection))
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
        # The local API leaves annotations out of an attachment's children
        # unless the request names their item type.
        annotations = [
            c["data"]
            for c in zot.everything(
                zot.children(att_data["key"], itemType="annotation")
            )
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
    parts = []
    for chunk in chunks(keys, BATCH_SIZE):
        result = zot.items(itemKey=",".join(chunk), format="bibtex")
        # The local API sends export formats as text/plain, which arrives as
        # bytes. The web API's application/x-bibtex arrives parsed.
        if isinstance(result, bytes):
            parts.append(result.decode("utf-8").strip())
        else:
            parts.append(bibtexparser.dumps(result).strip())
    bibtex = "\n\n".join(p for p in parts if p)
    return _json({"count": len(parse_bibtex(bibtex)), "bibtex": bibtex})


# Item types that are never duplicates of a bibliographic record
NON_RECORD_TYPES = frozenset({"note", "attachment", "annotation"})


def _item_summary(item: dict[str, Any]) -> dict[str, Any]:
    """Summarise an item for duplicate and merge output."""
    data = item.get("data", {})
    return {
        "key": data.get("key", ""),
        "itemType": data.get("itemType", ""),
        "title": data.get("title", ""),
        "creators": format_creators(data.get("creators", [])),
        "date": data.get("date", ""),
        "DOI": data.get("DOI", ""),
        "dateAdded": data.get("dateAdded", ""),
        "children": item.get("meta", {}).get("numChildren", 0),
    }


def _duplicate_groups(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group items that share a DOI, or a type, title and year.

    A title group whose items carry two different DOIs is not a duplicate
    (e.g. a paper and its erratum), and a title group that a DOI group
    already covers is not reported twice.
    """
    by_doi: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_title: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        data = item.get("data", {})
        doi = _item_doi(data)
        if doi:
            by_doi[doi].append(item)
        title = _title_key(data.get("title", ""))
        if title:
            by_title[(data["itemType"], title, data.get("date", "")[:4])].append(item)
    groups = [
        {"match": "doi", "value": doi, "items": group}
        for doi, group in sorted(by_doi.items())
        if len(group) > 1
    ]
    covered = [{i["key"] for i in g["items"]} for g in groups]
    for (_, _, year), group in sorted(by_title.items()):
        if len(group) < 2:  # noqa: PLR2004
            continue
        dois = {_item_doi(i["data"]) for i in group} - {""}
        keys = {i["key"] for i in group}
        if len(dois) > 1 or any(keys <= c for c in covered):
            continue
        title = group[0]["data"]["title"]
        value = f"{title} ({year})" if year else title
        groups.append({"match": "title", "value": value, "items": group})
    return groups


@mcp.tool()
@mcp_error_handler
def find_duplicates(limit: int = 20, offset: int = 0) -> str:
    """Find items that are probably duplicates: the same DOI, or the same type, title and year.

    Args:
        limit: Maximum number of duplicate groups to return (default 20).
        offset: Number of groups to skip, for pagination.

    Returns:
        JSON with the total number of groups, and each group's match
        reason, matched value and items (key, type, title, creators, date,
        DOI, date added, number of children). With write tools enabled,
        merge_items merges a group.

    """
    zot = _read_client()
    items = [
        i
        for i in zot.everything(zot.top())
        if i.get("data", {}).get("itemType") not in NON_RECORD_TYPES
    ]
    groups = _duplicate_groups(items)
    page = [
        {**g, "items": [_item_summary(i) for i in g["items"]]}
        for g in groups[offset : offset + limit]
    ]
    return _json({"total": len(groups), "groups": page})


def _citation_keys(data: dict[str, Any]) -> set[str]:
    """Return an item's citation keys: its citationKey field and Extra lines.

    Better BibTeX writes "Citation Key: <key>" to Extra; Zotero 7 also has a
    citationKey field.
    """
    keys = {data["citationKey"]} if data.get("citationKey") else set()
    for line in data.get("extra", "").splitlines():
        label, _, value = line.partition(":")
        if label.strip().casefold() == "citation key" and value.strip():
            keys.add(value.strip())
    return keys


@mcp.tool()
@mcp_error_handler
def find_by_citation_key(keys: list[str]) -> str:
    """Find items by citation key, e.g. the keys in a LaTeX document's \\cite commands.

    Matches Zotero's Citation Key field and the "Citation Key:" line that
    Better BibTeX writes to Extra. Matching is exact and case-sensitive.

    Args:
        keys: Citation keys.

    Returns:
        JSON with the items found for each key, and the keys not found.

    """
    zot = _read_client()
    found: dict[str, list[dict[str, Any]]] = {}
    for key in dict.fromkeys(keys):
        matches = [
            item
            for item in zot.items(q=key, qmode="everything", limit=25)
            if key in _citation_keys(item.get("data", {}))
        ]
        if matches:
            found[key] = [_item_summary(item) for item in matches]
    missing = [k for k in dict.fromkeys(keys) if k not in found]
    return _json({"found": found, "notFound": missing})


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
            collections: Collections to file the item under: keys, names, or
                "parent/child" paths.

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
            item["collections"] = _resolve_collections(zot, collections)
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
            parent: Optional parent collection, to nest the new collection: a
                key, a name, or a "parent/child" path.

        Returns:
            JSON with the created collection's key.

        """
        zot = _write_client()
        payload: dict[str, Any] = {"name": name}
        if parent:
            payload["parentCollection"] = _resolve_collection(zot, parent)
        resp = zot.create_collections([payload])
        if resp.get("success"):
            return _json({"created": resp["success"]["0"], "name": name})
        return _json({"error": "Collection was rejected", "detail": resp.get("failed")})

    def add_to_collection(item_key: str, collection_key: str) -> str:
        """File an existing item under a collection.

        Args:
            item_key: The item key.
            collection_key: The collection: a key, a name, or a "parent/child"
                path.

        Returns:
            JSON confirming the item and collection.

        """
        zot = _write_client()
        collection_key = _resolve_collection(zot, collection_key)
        zot.addto_collection(collection_key, zot.item(item_key))
        return _json({"item": item_key, "addedTo": collection_key})

    def remove_from_collection(item_key: str, collection_key: str) -> str:
        """Remove an item from a collection. The item itself is unchanged.

        This is the inverse of add_to_collection. The item stays in the
        library and in its other collections.

        Args:
            item_key: The item key.
            collection_key: The collection: a key, a name, or a "parent/child"
                path.

        Returns:
            JSON confirming the item and collection.

        """
        zot = _write_client()
        collection_key = _resolve_collection(zot, collection_key)
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
            from_collection_key: The collection to remove the item from: a
                key, a name, or a "parent/child" path.
            to_collection_key: The collection to add the item to, in the same
                forms.

        Returns:
            JSON confirming the item, the source and the destination.

        """
        zot = _write_client()
        from_collection_key, to_collection_key = _resolve_collections(
            zot, [from_collection_key, to_collection_key]
        )
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
            key: The collection: a key, a name, or a "parent/child" path.
            name: The new name. Leave empty to keep the current name.
            parent: The new parent collection, in the same forms, or "" to
                make the collection top-level. Omit to keep the current parent.

        Returns:
            JSON with the collection's key, name and parent.

        """
        if not name and parent is None:
            msg = "Give a new name, a new parent, or both"
            raise ValueError(msg)
        zot = _write_client()
        key = _resolve_collection(zot, key)
        if parent:
            parent = _resolve_collection(zot, parent)
        if parent == key:
            msg = "A collection cannot be its own parent"
            raise ValueError(msg)
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


def _attach_file(
    zot: Any, item_key: str, path: Path, title: str = ""
) -> dict[str, Any]:
    """Upload a file as a child attachment of ``item_key``, unless it is attached already.

    Returns:
        The new attachment's key, "unchanged", or the rejection.

    """
    # An upload always creates a new attachment item. Without a check, a
    # call that stops or is retried would attach the file a second time.
    # Thus, compare the file with the item's attachments first.
    checksum = _md5(path)
    for child in zot.children(item_key):
        data = child.get("data", {})
        if data.get("filename") == path.name and data.get("md5") == checksum:
            return {
                "unchanged": child["key"],
                "parent": item_key,
                "detail": "this file is already attached to the item",
            }
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
        return {
            "attached": result["success"][0]["key"],
            "parent": item_key,
            "filename": path.name,
        }
    if result["unchanged"]:
        return {
            "unchanged": item_key,
            "detail": "an identical file is already attached",
        }
    detail = result["failure"][0] if result["failure"] else None
    return {"error": "Attachment was rejected", "detail": detail}


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
        return _json(_attach_file(_write_client(), item_key, path, title))

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
            collections: Collections (keys, names or "parent/child" paths),
                for a standalone note only. A child note belongs to its
                parent's collections.

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
            note["collections"] = _resolve_collections(zot, collections)
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
    """Return the library item that ``item`` duplicates, by DOI, ISBN or title.

    Items with a DOI match on DOI only. Items without one match on title,
    and on year when both have a date. When both items have ISBNs, they must
    also share one, so that two editions of a book are not duplicates.
    """
    doi = _item_doi(item)
    if doi:
        for found in zot.items(q=doi, qmode="everything", limit=25):
            if _item_doi(found.get("data", {})) == doi:
                return found
        return None
    isbns = isbn_set(item.get("ISBN", ""))
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
        found_isbns = isbn_set(data.get("ISBN", ""))
        if isbns and found_isbns:
            if isbns & found_isbns:
                return found
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
    collections = _resolve_collections(zot, collections)
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


def _lookup(identifier: str) -> tuple[str, str, dict[str, Any] | str]:
    """Return an identifier's kind, normalised form and converted item.

    When the lookup fails, the item is replaced by the reason.
    """
    try:
        return lookup_identifier(identifier)
    except MetadataLookupError as e:
        return "unknown", identifier, str(e)


def _attach_open_access_pdf(
    zot: Any, item_key: str, doi: str, title: str
) -> dict[str, Any] | str:
    """Find, download and attach an open-access PDF. Return the outcome."""
    try:
        url = open_access_pdf_url(doi)
    except SemanticScholarError as e:
        return f"open-access lookup failed: {e}"
    if not url:
        return "no open-access PDF found"
    name = re.sub(r"[^\w\- ]+", "", title)[:80].strip() or "fulltext"
    with tempfile.TemporaryDirectory() as tmp:
        try:
            path = download_pdf(url, Path(tmp) / f"{name}.pdf")
            result = _attach_file(zot, item_key, path, "Full Text PDF")
        except PDFDownloadError as e:
            return str(e)
        # The items exist by now, so report a failed upload against its item
        # rather than failing the whole call.
        except Exception as e:
            return f"attaching the PDF failed: {e}"
    return {"source": url, **result}


def _register_import_tools(add: AddTool) -> None:
    """Register the tools that add items from identifiers and citation data."""

    def add_by_identifier(
        identifiers: list[str],
        collections: list[str] | None = None,
        tags: list[str] | None = None,
        if_exists: str = "skip",
        attach_pdf: bool = False,
    ) -> str:
        """Add items by DOI, arXiv ID or ISBN, looking up their metadata.

        DOIs go to doi.org, which passes them to their registration agency
        (Crossref, DataCite or mEDRA). arXiv IDs go through the DOI that
        arXiv registers for each paper. ISBNs go to Open Library, then
        Google Books.

        Args:
            identifiers: DOIs (bare or as doi.org URLs), arXiv IDs (e.g.
                "2001.00001", "arXiv:hep-th/9901001" or an arxiv.org URL) and
                ISBNs (ISBN-10 or ISBN-13), in any mix.
            collections: Collections to file the new items under: keys,
                names, or "parent/child" paths.
            tags: Tag names to attach to the new items.
            if_exists: What to do when the library already has the item (by
                DOI, or by title, year and ISBN): "skip" (the default)
                reports it and changes nothing, "file" adds it to the
                collections and tags given, and "create" adds a duplicate.
            attach_pdf: If true, attach an open-access PDF to each new
                article or preprint where one exists: from arXiv, or a
                location that Semantic Scholar knows.

        Returns:
            JSON with a count for each status, and a result for each
            identifier: its type, and created, exists, filed or failed, with
            the item key. With attach_pdf, each new item's result has a
            "pdf" entry: the attachment, or why there is none.

        """
        zot = _write_client()
        lookups = [(text, *_lookup(text)) for text in identifiers]
        converted = [item for *_, item in lookups if isinstance(item, dict)]
        created = iter(_create_imported(zot, converted, collections, tags, if_exists))
        results = [
            {"identifier": text, "type": kind, **next(created)}
            if isinstance(item, dict)
            else {"identifier": text, "status": "failed", "error": item}
            for text, kind, _, item in lookups
        ]
        if attach_pdf:
            for result, (_, kind, value, _) in zip(results, lookups, strict=True):
                if result["status"] != "created":
                    continue
                if kind == "isbn":
                    result["pdf"] = "open-access PDFs are looked up for DOIs only"
                    continue
                doi = f"10.48550/arXiv.{value}" if kind == "arxiv" else value
                result["pdf"] = _attach_open_access_pdf(
                    zot, result["key"], doi, result.get("title", "")
                )
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
            collections: Collections to file the new items under: keys,
                names, or "parent/child" paths.
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

    add(add_by_identifier)
    add(import_items)


# Fields that a merge does not copy from a duplicate into an empty field
MERGE_SKIP_FIELDS = frozenset(
    {
        "key",
        "version",
        "itemType",
        "dateAdded",
        "dateModified",
        "relations",
        "tags",
        "collections",
        "creators",
        "parentItem",
        "deleted",
        "inPublications",
    }
)


def _item_uri(item: dict[str, Any], key: str) -> str | None:
    """Return the zotero.org URI that relations use for ``key``, if known.

    The API reports a user library's ID only when Zotero is signed in to a
    zotero.org account. Otherwise the URI uses a local user key that the
    API does not reveal, so None is returned.
    """
    library = item.get("library", {})
    if not library.get("id"):
        return None
    return f"http://zotero.org/{library['type']}s/{library['id']}/items/{key}"


def _relation_list(relations: dict[str, Any], predicate: str) -> list[str]:
    """Return a relation's values as a list. The API gives one value as a string."""
    value = relations.get(predicate, [])
    return [value] if isinstance(value, str) else list(value)


def _merge_plan(
    master: dict[str, Any],
    duplicates: list[dict[str, Any]],
    children: list[dict[str, Any]],
) -> dict[str, Any]:
    """Work out what merging ``duplicates`` into ``master`` changes."""
    data = master["data"]
    fields: dict[str, Any] = {}
    for dup in duplicates:
        for field, value in dup["data"].items():
            if field in MERGE_SKIP_FIELDS or not value or data.get(field):
                continue
            fields.setdefault(field, value)
    creators = None
    if not data.get("creators"):
        creators = next(
            (d["data"]["creators"] for d in duplicates if d["data"].get("creators")),
            None,
        )
    have_tags = {t["tag"] for t in data.get("tags", [])}
    tags = list(
        dict.fromkeys(
            t["tag"]
            for d in duplicates
            for t in d["data"].get("tags", [])
            if t["tag"] not in have_tags
        )
    )
    have_colls = set(data.get("collections", []))
    collections = list(
        dict.fromkeys(
            c
            for d in duplicates
            for c in d["data"].get("collections", [])
            if c not in have_colls
        )
    )
    # Keep the duplicates' relations, and record that the master replaces
    # them, as Zotero's own merge does, so that citations of a duplicate in
    # a word processor document still resolve.
    relations = {
        k: _relation_list(data.get("relations", {}), k)
        for k in data.get("relations", {})
    }
    master_uri = _item_uri(master, data["key"])
    for dup in duplicates:
        for predicate in dup["data"].get("relations", {}):
            for uri in _relation_list(dup["data"]["relations"], predicate):
                if uri != master_uri and uri not in relations.setdefault(predicate, []):
                    relations[predicate].append(uri)
        dup_uri = _item_uri(dup, dup["data"]["key"])
        if dup_uri and dup_uri not in relations.setdefault("dc:replaces", []):
            relations["dc:replaces"].append(dup_uri)
    relations = {k: v for k, v in relations.items() if v}
    return {
        "fields": fields,
        "creators": creators,
        "tags": tags,
        "collections": collections,
        "relations": relations,
        "children": [c["key"] for c in children],
    }


def _check_mergeable(master: dict[str, Any], duplicates: list[dict[str, Any]]) -> None:
    """Raise ValueError unless all the items are top-level items of one type."""
    for item in [master, *duplicates]:
        data = item["data"]
        if data["itemType"] in NON_RECORD_TYPES or data.get("parentItem"):
            msg = (
                f"Item {data['key']} is a {data['itemType']}; "
                "only top-level items can be merged"
            )
            raise ValueError(msg)
        if data["itemType"] != master["data"]["itemType"]:
            msg = (
                f"Item {data['key']} is a {data['itemType']} and "
                f"{master['data']['key']} is a {master['data']['itemType']}; "
                "Zotero merges only items of one type"
            )
            raise ValueError(msg)


def _apply_merge(
    zot: Any, keep_key: str, duplicates: list[dict[str, Any]], plan: dict[str, Any]
) -> None:
    """Carry out a plan from :func:`_merge_plan`.

    Each write re-reads its item first: the local API rejects a write whose
    version is not the item's current version.
    """
    for child in plan["children"]:
        version = zot.item(child)["version"]
        zot.update_item({"key": child, "version": version, "parentItem": keep_key})
    item = zot.item(keep_key)
    data = item["data"]
    data.update(plan["fields"])
    if plan["creators"]:
        data["creators"] = plan["creators"]
    data["tags"] = data.get("tags", []) + [{"tag": t} for t in plan["tags"]]
    data["collections"] = data.get("collections", []) + plan["collections"]
    data["relations"] = plan["relations"]
    zot.update_item(item)
    for dup in duplicates:
        version = zot.item(dup["key"])["version"]
        zot.update_item({"key": dup["key"], "version": version, "deleted": True})


def _set_relation(zot: Any, item_key: str, other: str, *, linked: bool) -> None:
    """Add or remove one item's dc:relation link to another item."""
    target = zot.item(item_key)
    relations = target["data"].setdefault("relations", {})
    uris = _relation_list(relations, "dc:relation")
    uri = _item_uri(target, other)
    if linked and uri not in uris:
        uris.append(uri)
    elif not linked and uri in uris:
        uris.remove(uri)
    else:
        return
    if uris:
        relations["dc:relation"] = uris
    else:
        relations.pop("dc:relation", None)
    zot.update_item(target)


def _register_maintenance_tools(add: AddTool) -> None:
    """Register the tools that merge duplicates and link related items."""

    def merge_items(
        keep_key: str, duplicate_keys: list[str], confirm: bool = False
    ) -> str:
        """Merge duplicate items into one, as Zotero's "Merge items" does.

        The kept item gains the duplicates' notes and attachments, tags,
        collections and related items, and any field that it has empty and a
        duplicate has filled. The duplicates then move to Zotero's trash,
        from which they can be restored. Use find_duplicates to find
        candidates.

        Call first without confirm to see what would change, show that to
        the user, and call again with confirm=true to merge.

        Args:
            keep_key: The key of the item to keep.
            duplicate_keys: The keys of the items to merge into it.
            confirm: If false (the default), change nothing and return the
                plan.

        Returns:
            JSON with the plan, and whether it was carried out.

        """
        if not duplicate_keys or keep_key in duplicate_keys:
            msg = "Give one or more duplicate keys, not including keep_key"
            raise ValueError(msg)
        zot = _write_client()
        master = zot.item(keep_key)
        duplicates = [zot.item(k) for k in dict.fromkeys(duplicate_keys)]
        _check_mergeable(master, duplicates)
        children = [
            c
            for d in duplicates
            for c in zot.everything(zot.children(d["key"]))
            if c["data"].get("parentItem") == d["key"]
        ]
        plan = _merge_plan(master, duplicates, children)
        result = {
            "keep": _item_summary(master),
            "trash": [_item_summary(d) for d in duplicates],
            "fillFields": plan["fields"],
            "addCreators": bool(plan["creators"]),
            "addTags": plan["tags"],
            "addCollections": plan["collections"],
            "moveChildren": plan["children"],
            "merged": False,
        }
        if confirm:
            _apply_merge(zot, keep_key, duplicates, plan)
            result["merged"] = True
        return _json(result)

    def set_related(
        key: str, link: list[str] | None = None, unlink: list[str] | None = None
    ) -> str:
        """Add or remove "related item" links, in both directions, as Zotero's Related pane does.

        Args:
            key: The item key.
            link: Keys of items to link to it.
            unlink: Keys of items to unlink from it.

        Returns:
            JSON with the item's related item keys after the change.

        """
        link, unlink = link or [], unlink or []
        if not link and not unlink:
            msg = "Give items to link or to unlink"
            raise ValueError(msg)
        if key in link or key in unlink:
            msg = "An item cannot be related to itself"
            raise ValueError(msg)
        zot = _write_client()
        item = zot.item(key)
        if not _item_uri(item, key):
            msg = (
                "Related-item links need the library's zotero.org ID, which Zotero "
                "reports only when it is signed in to a zotero.org account"
            )
            raise ValueError(msg)

        for other in link:
            _set_relation(zot, key, other, linked=True)
            _set_relation(zot, other, key, linked=True)
        for other in unlink:
            _set_relation(zot, key, other, linked=False)
            _set_relation(zot, other, key, linked=False)
        related = _relation_list(
            zot.item(key)["data"].get("relations", {}), "dc:relation"
        )
        return _json(
            {"key": key, "related": [uri.rsplit("/", 1)[-1] for uri in related]}
        )

    add(merge_items)
    add(set_related)


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
    _register_maintenance_tools(add)
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
