"""Type definitions for Pyzotero.

This module contains TypedDict definitions, type aliases, and Protocol
classes for typing the pyzotero codebase.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Protocol, TypedDict

if TYPE_CHECKING:
    from collections.abc import Callable

# Type aliases
JsonDict = dict[str, Any]
LibraryType = Literal["user", "group"]


# Zotero API structures


class ZoteroCreator(TypedDict, total=False):
    """A creator (author, editor, etc.) of a Zotero item."""

    creatorType: str
    firstName: str
    lastName: str
    name: str  # For single-field creators


class ZoteroTag(TypedDict, total=False):
    """A tag attached to a Zotero item."""

    tag: str
    type: int


class ZoteroItemData(TypedDict, total=False):
    """The data payload of a Zotero item."""

    key: str
    version: int
    itemType: str
    title: str
    creators: list[ZoteroCreator]
    abstractNote: str
    date: str
    dateAdded: str
    dateModified: str
    tags: list[ZoteroTag]
    collections: list[str]
    relations: dict[str, Any]
    parentItem: str
    contentType: str
    charset: str
    filename: str
    md5: str
    mtime: int
    linkMode: str
    url: str
    note: str
    accessDate: str
    DOI: str
    ISBN: str
    ISSN: str
    language: str
    pages: str
    publicationTitle: str
    publisher: str
    volume: str
    issue: str


class ZoteroLibrary(TypedDict):
    """Library information for a Zotero item."""

    type: str
    id: int
    name: str
    links: dict[str, Any]


class ZoteroMeta(TypedDict, total=False):
    """Metadata for a Zotero item."""

    creatorSummary: str
    parsedDate: str
    numChildren: int
    numCollections: int


class ZoteroItem(TypedDict, total=False):
    """A full Zotero item as returned by the API."""

    key: str
    version: int
    library: ZoteroLibrary
    links: dict[str, Any]
    meta: ZoteroMeta
    data: ZoteroItemData


class ZoteroCollectionData(TypedDict, total=False):
    """The data payload of a Zotero collection."""

    key: str
    version: int
    name: str
    parentCollection: str | None


class ZoteroCollection(TypedDict, total=False):
    """A Zotero collection as returned by the API."""

    key: str
    version: int
    library: ZoteroLibrary
    links: dict[str, Any]
    meta: ZoteroMeta
    data: ZoteroCollectionData


# API response structures


class CreateItemsSuccess(TypedDict):
    """Successful items from create_items response."""

    # Keys are string indices ("0", "1", etc.), values are item keys
    pass  # Dynamic keys, use dict[str, str] in practice


class CreateItemsResponse(TypedDict, total=False):
    """Response from create_items API call."""

    success: dict[str, str]
    unchanged: dict[str, str]
    failed: dict[str, Any]


class UploadResult(TypedDict):
    """Result from file upload operations."""

    success: list[JsonDict]
    failure: list[JsonDict]
    unchanged: list[JsonDict]


# Semantic Scholar structures


class S2Author(TypedDict, total=False):
    """A Semantic Scholar author."""

    authorId: str | None
    name: str | None


class NormalisedPaper(TypedDict, total=False):
    """A normalised paper from Semantic Scholar."""

    paperId: str | None
    doi: str | None
    arxivId: str | None
    pmid: str | None
    title: str | None
    abstract: str | None
    venue: str | None
    year: int | None
    authors: list[S2Author]
    citationCount: int | None
    referenceCount: int | None
    influentialCitationCount: int | None
    isOpenAccess: bool | None
    openAccessPdfUrl: str | None
    publicationTypes: list[str] | None
    publicationDate: str | None


class PaginatedPaperResult(TypedDict):
    """Paginated result containing papers."""

    total: int
    offset: int
    papers: list[NormalisedPaper]


class RecommendationsResult(TypedDict):
    """Result from recommendations API."""

    papers: list[NormalisedPaper]


# Protocols for untyped dependencies


class FeedParserEntry(Protocol):
    """Protocol for feedparser entry objects."""

    @property
    def content(self) -> list[dict[str, Any]]: ...


class FeedParserFeed(Protocol):
    """Protocol for feedparser feed object."""

    @property
    def title(self) -> str: ...


class FeedParserResult(Protocol):
    """Protocol for feedparser.parse() result.

    feedparser returns a FeedParserDict which is a dict subclass
    with attribute access.
    """

    @property
    def entries(self) -> list[Any]: ...

    @property
    def feed(self) -> Any: ...

    @property
    def bozo(self) -> bool: ...


class BibDatabase(Protocol):
    """Protocol for bibtexparser.bparser.BibTexParser result.

    The BibDatabase object has an entries attribute containing
    parsed BibTeX entries.
    """

    @property
    def entries(self) -> list[dict[str, Any]]: ...


# Zotero client protocol (for use in other modules)


class ZoteroClientProtocol(Protocol):
    """Protocol for the Zotero client, used for typing in dependent modules."""

    endpoint: str
    library_id: str | int
    library_type: str
    api_key: str | None
    client: Any  # httpx.Client
    request: Any  # httpx.Response | None
    templates: dict[str, Any]
    backoff_until: float

    def _check_backoff(self) -> None: ...

    def _set_backoff(self, duration: str | float) -> None: ...


# Processor function type
ProcessorFunc = Callable[[FeedParserResult], list[Any]]


__all__ = [
    "BibDatabase",
    "CreateItemsResponse",
    "FeedParserEntry",
    "FeedParserFeed",
    "FeedParserResult",
    "JsonDict",
    "LibraryType",
    "NormalisedPaper",
    "PaginatedPaperResult",
    "ProcessorFunc",
    "RecommendationsResult",
    "S2Author",
    "UploadResult",
    "ZoteroClientProtocol",
    "ZoteroCollection",
    "ZoteroCollectionData",
    "ZoteroCreator",
    "ZoteroItem",
    "ZoteroItemData",
    "ZoteroLibrary",
    "ZoteroMeta",
    "ZoteroTag",
]
