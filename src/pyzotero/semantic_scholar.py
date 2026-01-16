"""Semantic Scholar API client for pyzotero.

This module provides functions to interact with the Semantic Scholar Graph API
for fetching paper metadata, citations, references, and recommendations.

API Documentation: https://api.semanticscholar.org/api-docs
"""

import httpx
from httpx import codes as http

BASE_URL = "https://api.semanticscholar.org/graph/v1"
RECOMMENDATIONS_URL = "https://api.semanticscholar.org/recommendations/v1"

# Fields to request from the Semantic Scholar API
DEFAULT_FIELDS = [
    "paperId",
    "externalIds",
    "title",
    "abstract",
    "venue",
    "year",
    "referenceCount",
    "citationCount",
    "influentialCitationCount",
    "isOpenAccess",
    "openAccessPdf",
    "authors",
    "publicationTypes",
    "publicationDate",
]

# Timeout for API requests (seconds)
REQUEST_TIMEOUT = 30.0


class SemanticScholarError(Exception):
    """Base exception for Semantic Scholar API errors."""


class RateLimitError(SemanticScholarError):
    """Raised when API rate limit is exceeded."""

    def __init__(self, msg="Rate limit exceeded. Please wait and try again."):
        super().__init__(msg)


class PaperNotFoundError(SemanticScholarError):
    """Raised when a paper is not found."""

    def __init__(self, msg="Paper not found."):
        super().__init__(msg)


def _make_request(url, params=None):
    """Make an HTTP GET request to the Semantic Scholar API.

    Args:
        url: The full URL to request
        params: Optional dict of query parameters

    Returns:
        The JSON response as a dict

    Raises:
        RateLimitError: If rate limit is exceeded (HTTP 429)
        PaperNotFoundError: If paper is not found (HTTP 404)
        SemanticScholarError: For other API errors

    """
    with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
        response = client.get(url, params=params)

        _check_response(response)
        return response.json()


def _check_response(response):
    """Check HTTP response and raise appropriate exceptions.

    Args:
        response: httpx Response object

    Raises:
        RateLimitError: If rate limit is exceeded (HTTP 429)
        PaperNotFoundError: If paper is not found (HTTP 404)
        SemanticScholarError: For other API errors

    """
    if response.status_code == http.TOO_MANY_REQUESTS:
        raise RateLimitError

    if response.status_code == http.NOT_FOUND:
        raise PaperNotFoundError

    if response.status_code != http.OK:
        msg = f"Semantic Scholar API error: {response.status_code} - {response.text}"
        raise SemanticScholarError(msg)


def _format_paper_id(identifier, id_type=None):  # noqa: PLR0911
    """Format a paper identifier for the Semantic Scholar API.

    Semantic Scholar accepts various identifier formats:
    - DOI: DOI:10.1234/example
    - arXiv: ARXIV:1234.5678
    - Semantic Scholar ID: direct use
    - PMID: PMID:12345678
    - MAG: MAG:12345678
    - ACL: ACL:P19-1234
    - CorpusID: CorpusId:12345678

    Args:
        identifier: The paper identifier
        id_type: Optional type hint ("doi", "arxiv", "pmid", "mag", "acl", "corpus")

    Returns:
        Formatted identifier string for the API

    """
    if not identifier:
        return identifier

    identifier = identifier.strip()

    # If already prefixed, return as-is
    known_prefixes = ["DOI:", "ARXIV:", "PMID:", "MAG:", "ACL:", "CorpusId:"]
    for prefix in known_prefixes:
        if identifier.upper().startswith(prefix.upper()):
            return identifier

    # Strip common DOI URL prefixes
    doi_prefixes = ["https://doi.org/", "http://doi.org/", "doi:"]
    for prefix in doi_prefixes:
        if identifier.lower().startswith(prefix.lower()):
            identifier = identifier[len(prefix) :]
            return f"DOI:{identifier}"

    # If type hint provided, add appropriate prefix
    if id_type:
        type_map = {
            "doi": "DOI:",
            "arxiv": "ARXIV:",
            "pmid": "PMID:",
            "mag": "MAG:",
            "acl": "ACL:",
            "corpus": "CorpusId:",
        }
        prefix = type_map.get(id_type.lower())
        if prefix:
            return f"{prefix}{identifier}"

    # Heuristic detection
    # DOIs typically contain a slash and start with 10.
    if "/" in identifier and identifier.startswith("10."):
        return f"DOI:{identifier}"

    # arXiv IDs have a specific format (YYMM.NNNNN or category/YYMMNNN)
    if "." in identifier and identifier.split(".")[0].isdigit():
        return f"ARXIV:{identifier}"

    # If all else fails, assume it's a Semantic Scholar ID
    return identifier


def _normalise_paper(paper_data):
    """Normalise paper data from Semantic Scholar to a consistent format.

    Args:
        paper_data: Raw paper data from the API

    Returns:
        Normalised paper dict with consistent field names

    """
    if not paper_data:
        return None

    external_ids = paper_data.get("externalIds") or {}
    authors = paper_data.get("authors") or []
    open_access_pdf = paper_data.get("openAccessPdf") or {}

    return {
        "paperId": paper_data.get("paperId"),
        "doi": external_ids.get("DOI"),
        "arxivId": external_ids.get("ArXiv"),
        "pmid": external_ids.get("PubMed"),
        "title": paper_data.get("title"),
        "abstract": paper_data.get("abstract"),
        "venue": paper_data.get("venue"),
        "year": paper_data.get("year"),
        "authors": [
            {
                "authorId": a.get("authorId"),
                "name": a.get("name"),
            }
            for a in authors
        ],
        "citationCount": paper_data.get("citationCount"),
        "referenceCount": paper_data.get("referenceCount"),
        "influentialCitationCount": paper_data.get("influentialCitationCount"),
        "isOpenAccess": paper_data.get("isOpenAccess"),
        "openAccessPdfUrl": open_access_pdf.get("url"),
        "publicationTypes": paper_data.get("publicationTypes"),
        "publicationDate": paper_data.get("publicationDate"),
    }


def get_paper(identifier, id_type=None):
    """Get details for a single paper.

    Args:
        identifier: Paper identifier (DOI, arXiv ID, S2 ID, etc.)
        id_type: Optional type hint for the identifier

    Returns:
        Normalised paper dict

    Raises:
        PaperNotFoundError: If paper is not found
        SemanticScholarError: For API errors

    """
    paper_id = _format_paper_id(identifier, id_type)
    url = f"{BASE_URL}/paper/{paper_id}"
    params = {"fields": ",".join(DEFAULT_FIELDS)}

    data = _make_request(url, params)
    return _normalise_paper(data)


def get_citations(identifier, id_type=None, limit=100, offset=0):
    """Get papers that cite a given paper.

    Args:
        identifier: Paper identifier (DOI, arXiv ID, S2 ID, etc.)
        id_type: Optional type hint for the identifier
        limit: Maximum number of results (default 100, max 1000)
        offset: Offset for pagination

    Returns:
        Dict with 'total' count and 'papers' list

    Raises:
        PaperNotFoundError: If paper is not found
        SemanticScholarError: For API errors

    """
    paper_id = _format_paper_id(identifier, id_type)
    url = f"{BASE_URL}/paper/{paper_id}/citations"
    params = {
        "fields": ",".join(DEFAULT_FIELDS),
        "limit": min(limit, 1000),
        "offset": offset,
    }

    data = _make_request(url, params)

    # Citations API returns {"data": [...], "offset": N, "next": N}
    papers = []
    for item in data.get("data", []):
        citing_paper = item.get("citingPaper")
        if citing_paper:
            papers.append(_normalise_paper(citing_paper))

    return {
        "total": len(papers),
        "offset": data.get("offset", 0),
        "papers": papers,
    }


def get_references(identifier, id_type=None, limit=100, offset=0):
    """Get papers that a given paper references.

    Args:
        identifier: Paper identifier (DOI, arXiv ID, S2 ID, etc.)
        id_type: Optional type hint for the identifier
        limit: Maximum number of results (default 100, max 1000)
        offset: Offset for pagination

    Returns:
        Dict with 'total' count and 'papers' list

    Raises:
        PaperNotFoundError: If paper is not found
        SemanticScholarError: For API errors

    """
    paper_id = _format_paper_id(identifier, id_type)
    url = f"{BASE_URL}/paper/{paper_id}/references"
    params = {
        "fields": ",".join(DEFAULT_FIELDS),
        "limit": min(limit, 1000),
        "offset": offset,
    }

    data = _make_request(url, params)

    # References API returns {"data": [...], "offset": N, "next": N}
    papers = []
    for item in data.get("data", []):
        cited_paper = item.get("citedPaper")
        if cited_paper:
            papers.append(_normalise_paper(cited_paper))

    return {
        "total": len(papers),
        "offset": data.get("offset", 0),
        "papers": papers,
    }


def get_recommendations(identifier, id_type=None, limit=100):
    """Get recommended papers based on a seed paper.

    Uses Semantic Scholar's recommendation API which returns papers
    similar to the input based on SPECTER2 embeddings.

    Args:
        identifier: Paper identifier (DOI, arXiv ID, S2 ID, etc.)
        id_type: Optional type hint for the identifier
        limit: Maximum number of recommendations (default 100, max 500)

    Returns:
        Dict with 'papers' list of recommended papers

    Raises:
        PaperNotFoundError: If paper is not found
        SemanticScholarError: For API errors

    """
    # First, get the paper to obtain its Semantic Scholar ID
    paper = get_paper(identifier, id_type)
    paper_id = paper.get("paperId")

    if not paper_id:
        raise PaperNotFoundError

    url = f"{RECOMMENDATIONS_URL}/papers"
    params = {
        "fields": ",".join(DEFAULT_FIELDS),
        "limit": min(limit, 500),
    }

    # POST request with paper IDs in body
    with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
        response = client.post(
            url,
            params=params,
            json={"positivePaperIds": [paper_id]},
        )
        _check_response(response)
        data = response.json()

    papers = [_normalise_paper(p) for p in data.get("recommendedPapers", [])]

    return {"papers": papers}


def search_papers(
    query,
    limit=100,
    offset=0,
    year=None,
    open_access_only=False,
    sort=None,
    min_citations=None,
):
    """Search for papers by keyword query.

    Args:
        query: Search query string
        limit: Maximum number of results (default 100, max 100)
        offset: Offset for pagination
        year: Optional year filter (e.g., "2020", "2018-2022", "2020-")
        open_access_only: If True, only return open access papers
        sort: Sort order - "citationCount" (descending) or "year" (descending)
        min_citations: Minimum citation count filter (applied client-side)

    Returns:
        Dict with 'total' count, 'offset', and 'papers' list

    Raises:
        SemanticScholarError: For API errors

    """
    url = f"{BASE_URL}/paper/search"
    params = {
        "query": query,
        "fields": ",".join(DEFAULT_FIELDS),
        "limit": min(limit, 100),  # API max is 100 per request
        "offset": offset,
    }

    if year:
        params["year"] = year

    if open_access_only:
        params["openAccessPdf"] = ""

    if sort:
        # Semantic Scholar supports sorting by citationCount:desc or publicationDate:desc
        sort_map = {
            "citationCount": "citationCount:desc",
            "citations": "citationCount:desc",
            "year": "publicationDate:desc",
            "date": "publicationDate:desc",
        }
        if sort in sort_map:
            params["sort"] = sort_map[sort]

    data = _make_request(url, params)

    papers = [_normalise_paper(p) for p in data.get("data", [])]

    # Apply client-side citation filter if specified
    if min_citations is not None and min_citations > 0:
        papers = [p for p in papers if (p.get("citationCount") or 0) >= min_citations]

    return {
        "total": data.get("total", len(papers)),
        "offset": data.get("offset", 0),
        "papers": papers,
    }


def filter_by_citations(papers, min_citations):
    """Filter a list of papers by minimum citation count.

    Args:
        papers: List of normalised paper dicts
        min_citations: Minimum citation count

    Returns:
        Filtered list of papers

    """
    if min_citations is None or min_citations <= 0:
        return papers
    return [p for p in papers if (p.get("citationCount") or 0) >= min_citations]
