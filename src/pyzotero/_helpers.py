"""Shared helpers used by both the CLI and MCP server."""

from __future__ import annotations

from typing import Any

from pyzotero import zotero


def get_zotero_client(locale: str = "en-US") -> zotero.Zotero:
    """Get a Zotero client configured for local access."""
    return zotero.Zotero(library_id="0", library_type="user", local=True, locale=locale)


def normalize_doi(doi: str) -> str:
    """Normalise a DOI for case-insensitive matching.

    Strips common prefixes (https://doi.org/, http://doi.org/, doi:) and converts to lowercase.
    DOIs are case-insensitive per the DOI specification.
    """
    if not doi:
        return ""

    # Strip whitespace
    doi = doi.strip()

    # Strip common prefixes
    prefixes = ["https://doi.org/", "http://doi.org/", "doi:"]
    for prefix in prefixes:
        if doi.lower().startswith(prefix.lower()):
            doi = doi[len(prefix) :]
            break

    # Convert to lowercase for case-insensitive matching
    return doi.lower().strip()


def build_doi_index(zot: zotero.Zotero) -> dict[str, str]:
    """Build a mapping of normalised DOIs to Zotero item keys.

    Returns:
        Dict mapping normalised DOIs to item keys

    """
    doi_map: dict[str, str] = {}
    all_items = zot.everything(zot.items())

    for item in all_items:
        data = item.get("data", {})
        item_doi = data.get("DOI", "")

        if item_doi:
            normalised_doi = normalize_doi(item_doi)
            item_key = data.get("key", "")

            if normalised_doi and item_key:
                doi_map[normalised_doi] = item_key

    return doi_map


def build_doi_index_full(zot: zotero.Zotero) -> dict[str, dict[str, str]]:
    """Build a mapping of normalised DOIs to Zotero item keys and original DOIs.

    Returns:
        Dict mapping normalised DOIs to dicts with 'key' and 'original' fields

    """
    doi_map: dict[str, dict[str, str]] = {}
    all_items = zot.everything(zot.items())

    for item in all_items:
        data = item.get("data", {})
        item_doi = data.get("DOI", "")

        if item_doi:
            normalised_doi = normalize_doi(item_doi)
            item_key = data.get("key", "")

            if normalised_doi and item_key:
                doi_map[normalised_doi] = {"key": item_key, "original": item_doi}

    return doi_map


def format_s2_paper(
    paper: dict[str, Any], in_library: bool | None = None
) -> dict[str, Any]:
    """Format a Semantic Scholar paper for output.

    Args:
        paper: Normalised paper dict from semantic_scholar module
        in_library: Boolean indicating if paper is in local Zotero

    Returns:
        Formatted dict for output

    """
    result: dict[str, Any] = {
        "paperId": paper.get("paperId"),
        "doi": paper.get("doi"),
        "title": paper.get("title"),
        "authors": [a.get("name") for a in (paper.get("authors") or [])],
        "year": paper.get("year"),
        "venue": paper.get("venue"),
        "citationCount": paper.get("citationCount"),
        "referenceCount": paper.get("referenceCount"),
        "isOpenAccess": paper.get("isOpenAccess"),
        "openAccessPdfUrl": paper.get("openAccessPdfUrl"),
    }

    if in_library is not None:
        result["inLibrary"] = in_library

    return result


def annotate_with_library(
    papers: list[dict[str, Any]], doi_map: dict[str, str]
) -> list[dict[str, Any]]:
    """Annotate papers with in_library status based on DOI matching.

    Args:
        papers: List of normalised paper dicts
        doi_map: Dict mapping normalised DOIs to Zotero item keys

    Returns:
        List of formatted paper dicts with inLibrary field

    """
    results = []
    for paper in papers:
        doi = paper.get("doi")
        in_library = False
        if doi:
            normalised = normalize_doi(doi)
            in_library = normalised in doi_map
        results.append(format_s2_paper(paper, in_library))
    return results
