"""Convert CSL JSON and BibTeX records to Zotero items, and look up DOIs.

The mappings follow the CSL section of the Zotero schema
(https://github.com/zotero/zotero-schema). A converted item uses Zotero's
base field names until :func:`fit_to_schema` renames each field to the one
its item type uses, and moves what the type does not accept into Extra.
"""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

import bibtexparser
import httpx2
from bibtexparser.customization import splitname
from bibtexparser.latexenc import latex_to_unicode

from pyzotero import __version__
from pyzotero._helpers import normalise_doi
from pyzotero.semantic_scholar import PaperNotFoundError, get_paper

DOI_TIMEOUT = 30.0
PDF_TIMEOUT = 60.0
# Larger downloads are refused
MAX_PDF_BYTES = 100 * 1024 * 1024
# The DOI prefix that arXiv registers its papers under
ARXIV_DOI_PREFIX = "10.48550/arxiv."
# arXiv identifiers: 2001.00001 since 2007, hep-th/9901001 before
ARXIV_ID_RE = re.compile(
    r"^(?:\d{4}\.\d{4,5}|[a-z][a-z\-]*(?:\.[a-z]{2})?/\d{7})$", re.IGNORECASE
)
ARXIV_PREFIX_RE = re.compile(
    r"^(?:arxiv:|https?://(?:www\.)?arxiv\.org/(?:abs|pdf)/)", re.IGNORECASE
)
OPEN_LIBRARY_URL = "https://openlibrary.org/api/books"
GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"

# CSL type -> Zotero item type. Crossref and DataCite sometimes send their own
# type names in place of CSL ones, so those are accepted too.
CSL_TYPES = {
    "article": "preprint",
    "article-journal": "journalArticle",
    "article-magazine": "magazineArticle",
    "article-newspaper": "newspaperArticle",
    "bill": "bill",
    "book": "book",
    "broadcast": "tvBroadcast",
    "chapter": "bookSection",
    "dataset": "dataset",
    "document": "document",
    "entry-dictionary": "dictionaryEntry",
    "entry-encyclopedia": "encyclopediaArticle",
    "graphic": "artwork",
    "hearing": "hearing",
    "interview": "interview",
    "legal_case": "case",
    "legislation": "statute",
    "manuscript": "manuscript",
    "map": "map",
    "motion_picture": "film",
    "paper-conference": "conferencePaper",
    "patent": "patent",
    "personal_communication": "letter",
    "post": "forumPost",
    "post-weblog": "blogPost",
    "report": "report",
    "software": "computerProgram",
    "song": "audioRecording",
    "speech": "presentation",
    "standard": "standard",
    "thesis": "thesis",
    "webpage": "webpage",
    # Crossref and DataCite names
    "journal-article": "journalArticle",
    "proceedings-article": "conferencePaper",
    "book-chapter": "bookSection",
    "book-part": "bookSection",
    "book-section": "bookSection",
    "posted-content": "preprint",
    "dissertation": "thesis",
    "monograph": "book",
    "edited-book": "book",
    "reference-book": "book",
    "reference-entry": "encyclopediaArticle",
}

# CSL variable -> candidate Zotero base fields, in order of preference.
CSL_TEXT_FIELDS = {
    "abstract": ["abstractNote"],
    "archive": ["archive"],
    "archive_location": ["archiveLocation"],
    "authority": ["authority"],
    "call-number": ["callNumber", "applicationNumber"],
    "chapter-number": ["session"],
    "citation-key": ["citationKey"],
    "collection-number": ["seriesNumber"],
    "collection-title": ["seriesTitle", "series"],
    "container-title": ["publicationTitle", "reporter", "code"],
    "dimensions": ["artworkSize", "runningTime"],
    "DOI": ["DOI"],
    "edition": ["edition"],
    "event-place": ["eventPlace"],
    "event-title": ["meetingName", "conferenceName"],
    "genre": ["type", "programmingLanguage"],
    "ISBN": ["ISBN"],
    "ISSN": ["ISSN"],
    "issue": ["issue", "priorityNumbers"],
    "journalAbbreviation": ["journalAbbreviation"],
    "container-title-short": ["journalAbbreviation"],
    "language": ["language"],
    "license": ["rights"],
    "medium": ["medium", "system"],
    "note": ["extra"],
    "number": ["number"],
    "number-of-pages": ["numPages"],
    "number-of-volumes": ["numberOfVolumes"],
    "original-publisher": ["originalPublisher"],
    "original-publisher-place": ["originalPlace"],
    "part-number": ["partNumber"],
    "part-title": ["partTitle"],
    "page": ["pages"],
    "PMID": ["PMID"],
    "PMCID": ["PMCID"],
    "publisher": ["publisher"],
    "publisher-place": ["place"],
    "references": ["history", "references"],
    "scale": ["scale"],
    "section": ["section", "committee"],
    "shortTitle": ["shortTitle"],
    "source": ["libraryCatalog"],
    "status": ["status"],
    "title": ["title"],
    "title-short": ["shortTitle"],
    "URL": ["url"],
    "version": ["versionNumber"],
    "volume": ["volume", "codeNumber"],
}

CSL_DATE_FIELDS = {
    "issued": "date",
    "accessed": "accessDate",
    "submitted": "filingDate",
    "original-date": "originalDate",
}

# CSL name variable -> Zotero creator type
CSL_NAME_FIELDS = {
    "author": "author",
    "chair": "chair",
    "collection-editor": "seriesEditor",
    "composer": "composer",
    "container-author": "bookAuthor",
    "contributor": "contributor",
    "director": "director",
    "editor": "editor",
    "executive-producer": "executiveProducer",
    "guest": "guest",
    "host": "host",
    "interviewer": "interviewer",
    "narrator": "narrator",
    "organizer": "organizer",
    "original-author": "originalCreator",
    "performer": "castMember",
    "producer": "producer",
    "recipient": "recipient",
    "reviewed-author": "reviewedAuthor",
    "script-writer": "scriptwriter",
    "series-creator": "seriesCreator",
    "translator": "translator",
}

# Item type -> {base field: the field that the type uses in its place}
BASE_FIELD_REMAP = {
    "artwork": {"medium": "artworkMedium"},
    "audioRecording": {"medium": "audioRecordingFormat", "publisher": "label"},
    "bill": {
        "number": "billNumber",
        "volume": "codeVolume",
        "pages": "codePages",
        "authority": "legislativeBody",
    },
    "blogPost": {"publicationTitle": "blogTitle", "type": "websiteType"},
    "book": {"medium": "format"},
    "bookSection": {"publicationTitle": "bookTitle", "medium": "format"},
    "case": {
        "title": "caseName",
        "authority": "court",
        "date": "dateDecided",
        "number": "docketNumber",
        "volume": "reporterVolume",
        "pages": "firstPage",
    },
    "computerProgram": {"publisher": "company"},
    "conferencePaper": {"publicationTitle": "proceedingsTitle"},
    "dataset": {
        "number": "identifier",
        "publisher": "repository",
        "place": "repositoryLocation",
        "medium": "format",
    },
    "dictionaryEntry": {"publicationTitle": "dictionaryTitle"},
    "email": {"title": "subject"},
    "encyclopediaArticle": {"publicationTitle": "encyclopediaTitle"},
    "film": {
        "publisher": "distributor",
        "type": "genre",
        "medium": "videoRecordingFormat",
    },
    "forumPost": {"publicationTitle": "forumTitle", "type": "postType"},
    "hearing": {"number": "documentNumber", "authority": "legislativeBody"},
    "interview": {"medium": "interviewMedium"},
    "letter": {"type": "letterType"},
    "manuscript": {"type": "manuscriptType", "publisher": "institution"},
    "map": {"type": "mapType"},
    "patent": {
        "authority": "issuingAuthority",
        "number": "patentNumber",
        "date": "issueDate",
        "originalDate": "priorityDate",
        "status": "legalStatus",
    },
    "podcast": {"number": "episodeNumber", "medium": "audioFileType"},
    "preprint": {"type": "genre", "publisher": "repository", "number": "archiveID"},
    "presentation": {"type": "presentationType", "publicationTitle": "sessionTitle"},
    "radioBroadcast": {
        "publicationTitle": "programTitle",
        "number": "episodeNumber",
        "medium": "audioRecordingFormat",
        "publisher": "network",
    },
    "report": {
        "number": "reportNumber",
        "type": "reportType",
        "publisher": "institution",
    },
    "standard": {"authority": "organization"},
    "statute": {
        "title": "nameOfAct",
        "number": "publicLawNumber",
        "date": "dateEnacted",
    },
    "thesis": {"type": "thesisType", "publisher": "university"},
    "tvBroadcast": {
        "publicationTitle": "programTitle",
        "number": "episodeNumber",
        "medium": "videoRecordingFormat",
        "publisher": "network",
    },
    "videoRecording": {"medium": "videoRecordingFormat", "publisher": "studio"},
    "webpage": {"publicationTitle": "websiteTitle", "type": "websiteType"},
}

# Labels for fields that Extra carries when the item type lacks them. Zotero
# reads these back as the field (the "Citation Key: ..." convention).
EXTRA_LABELS = {
    "DOI": "DOI",
    "citationKey": "Citation Key",
    "ISBN": "ISBN",
    "ISSN": "ISSN",
    "PMID": "PMID",
    "PMCID": "PMCID",
}

BIBTEX_TYPES = {
    "article": "journalArticle",
    "book": "book",
    "mvbook": "book",
    "booklet": "book",
    "manual": "book",
    "proceedings": "book",
    "collection": "book",
    "inbook": "bookSection",
    "incollection": "bookSection",
    "inproceedings": "conferencePaper",
    "conference": "conferencePaper",
    "phdthesis": "thesis",
    "mastersthesis": "thesis",
    "thesis": "thesis",
    "techreport": "report",
    "report": "report",
    "unpublished": "manuscript",
    "online": "webpage",
    "electronic": "webpage",
    "www": "webpage",
    "patent": "patent",
    "software": "computerProgram",
    "dataset": "dataset",
    "misc": "document",
}

# BibTeX field -> Zotero base field
BIBTEX_FIELDS = {
    "title": "title",
    "journal": "publicationTitle",
    "journaltitle": "publicationTitle",
    "booktitle": "publicationTitle",
    "volume": "volume",
    "pages": "pages",
    "publisher": "publisher",
    "school": "publisher",
    "institution": "publisher",
    "organization": "publisher",
    "address": "place",
    "location": "place",
    "edition": "edition",
    "series": "series",
    "doi": "DOI",
    "isbn": "ISBN",
    "issn": "ISSN",
    "url": "url",
    "abstract": "abstractNote",
    "language": "language",
    "note": "extra",
    "shorttitle": "shortTitle",
    "urldate": "accessDate",
}

MONTHS = {
    name: number
    for number, names in enumerate(
        [
            ("jan", "january"),
            ("feb", "february"),
            ("mar", "march"),
            ("apr", "april"),
            ("may",),
            ("jun", "june"),
            ("jul", "july"),
            ("aug", "august"),
            ("sep", "sept", "september"),
            ("oct", "october"),
            ("nov", "november"),
            ("dec", "december"),
        ],
        start=1,
    )
    for name in names
}


class MetadataLookupError(Exception):
    """Raised when an identifier has no metadata, or the lookup fails."""


class DOILookupError(MetadataLookupError):
    """Raised when doi.org has no metadata for a DOI, or the lookup fails."""


class PDFDownloadError(Exception):
    """Raised when a PDF cannot be downloaded, or the download is not a PDF."""


def _text(value: Any) -> str:
    """Return a CSL value as a string. Lists (e.g. ISSN) are joined."""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value if v)
    return str(value).strip()


def _csl_license(value: Any) -> str:
    """Return a CSL license as a string.

    Crossref sends a list of license objects, not a string. Use their URLs.
    """
    if isinstance(value, list):
        urls = [v.get("URL") if isinstance(v, dict) else v for v in value]
        return ", ".join(dict.fromkeys(str(u) for u in urls if u))
    return _text(value)


JATS_HEADING = re.compile(r"^\s*<jats:title>\s*Abstract\s*</jats:title>", re.IGNORECASE)
JATS_BLOCK_END = re.compile(r"</jats:(?:p|title)>")
JATS_TAG = re.compile(r"</?jats:[^>]*>")


def _jats_to_text(value: str) -> str:
    """Convert a JATS abstract, as Crossref sends it, to plain text.

    Each paragraph and section title becomes one line. A leading "Abstract"
    title is removed.
    """
    if "<jats:" not in value:
        return value
    text = JATS_HEADING.sub("", " ".join(value.split()))
    text = JATS_TAG.sub("", JATS_BLOCK_END.sub("\n", text))
    lines = (html.unescape(line).strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def _csl_text(var: str, value: Any) -> str:
    """Return the text of a CSL variable, for a Zotero field."""
    if var == "license":
        return _csl_license(value)
    if var == "abstract":
        return _jats_to_text(_text(value))
    return _text(value)


def _csl_date(value: Any) -> str:
    """Format a CSL date object as YYYY, YYYY-MM or YYYY-MM-DD."""
    if not isinstance(value, dict):
        return _text(value)
    parts = value.get("date-parts")
    if parts and parts[0] and parts[0][0]:
        return "-".join(
            f"{int(p):02d}" if i else str(int(p)) for i, p in enumerate(parts[0])
        )
    return _text(value.get("literal") or value.get("raw") or "")


def _csl_name(name: dict[str, Any], creator_type: str) -> dict[str, str] | None:
    """Convert a CSL name to a Zotero creator, or None if it is empty."""
    family = " ".join(
        p for p in (name.get("non-dropping-particle"), name.get("family")) if p
    )
    given = name.get("given", "")
    if family:
        return {"creatorType": creator_type, "firstName": given, "lastName": family}
    literal = name.get("literal") or given
    if literal:
        return {"creatorType": creator_type, "name": literal}
    return None


def csl_to_zotero(csl: dict[str, Any]) -> dict[str, Any]:
    """Convert one CSL JSON record to a Zotero item that uses base field names.

    Pass the result to :func:`fit_to_schema` before it is sent to Zotero.
    """
    item_type = CSL_TYPES.get(csl.get("type", ""), "document")
    item: dict[str, Any] = {"itemType": item_type}
    for var, candidates in CSL_TEXT_FIELDS.items():
        value = csl.get(var)
        if value in (None, "", []):
            continue
        text = _csl_text(var, value)
        if not text:
            continue
        # The candidates are alternatives for different item types. Keep them
        # all; fit_to_schema keeps the first that the type accepts.
        item.setdefault("_candidates", {})[var] = (candidates, text)
    for var, field in CSL_DATE_FIELDS.items():
        if csl.get(var):
            date = _csl_date(csl[var])
            if date:
                item[field] = date
    creators = []
    for var, creator_type in CSL_NAME_FIELDS.items():
        for name in csl.get(var) or []:
            creator = _csl_name(name, creator_type)
            if creator:
                creators.append(creator)
    if creators:
        item["creators"] = creators
    return item


def _clean(value: str) -> str:
    """Decode LaTeX to Unicode, drop grouping braces and collapse whitespace."""
    text = latex_to_unicode(value).replace("{", "").replace("}", "")
    return " ".join(text.split())


def _split_names(value: str) -> list[str]:
    """Split a BibTeX name list on "and", except inside braces."""
    names, depth, start = [], 0, 0
    for match in re.finditer(r"[{}]|\s+and\s+", value, flags=re.IGNORECASE):
        part = match.group()
        if part == "{":
            depth += 1
        elif part == "}":
            depth -= 1
        elif depth == 0:
            names.append(value[start : match.start()])
            start = match.end()
    names.append(value[start:])
    return [n.strip() for n in names if n.strip()]


def _is_braced(value: str) -> bool:
    """Return True if one brace pair encloses the whole of ``value``."""
    if not value.startswith("{"):
        return False
    depth = 0
    for index, char in enumerate(value):
        depth += {"{": 1, "}": -1}.get(char, 0)
        if depth == 0:
            return index == len(value) - 1
    return False


def _bibtex_names(value: str, creator_type: str) -> list[dict[str, str]]:
    """Convert a raw BibTeX name list ("A and B") to Zotero creators."""
    creators = []
    for raw in _split_names(value):
        # A name in one outer brace pair is a corporate name. Keep it whole.
        if _is_braced(raw):
            creators.append({"creatorType": creator_type, "name": _clean(raw)})
            continue
        try:
            parts = splitname(raw, strict_mode=False)
        except bibtexparser.customization.InvalidName:
            creators.append({"creatorType": creator_type, "name": _clean(raw)})
            continue
        last = " ".join(parts["von"] + parts["last"])
        if parts["jr"]:
            last = f"{last}, {' '.join(parts['jr'])}"
        first = " ".join(parts["first"])
        if first:
            creators.append(
                {
                    "creatorType": creator_type,
                    "firstName": _clean(first),
                    "lastName": _clean(last),
                }
            )
        else:
            creators.append({"creatorType": creator_type, "name": _clean(last)})
    return creators


def _bibtex_date(entry: dict[str, str]) -> str:
    """Build a date from the date field, or from year and month."""
    if entry.get("date"):
        return entry["date"]
    year = entry.get("year", "").strip()
    month = entry.get("month", "").strip().lower().rstrip(".")
    number = MONTHS.get(month) or (int(month) if month.isdigit() else None)
    if year and number and 1 <= number <= 12:  # noqa: PLR2004
        return f"{year}-{number:02d}"
    return year


def bibtex_to_zotero(entry: dict[str, str]) -> dict[str, Any]:  # noqa: PLR0912
    """Convert one parsed BibTeX entry to a Zotero item that uses base field names.

    Pass the result to :func:`fit_to_schema` before it is sent to Zotero.
    """
    entry_type = entry.get("ENTRYTYPE", "misc").lower()
    item_type = BIBTEX_TYPES.get(entry_type, "document")
    item: dict[str, Any] = {"itemType": item_type}
    for bib_field, base in BIBTEX_FIELDS.items():
        value = entry.get(bib_field)
        if value and base not in item:
            item[base] = _clean(value)
    # "number" is an issue for an article, and a report or patent number otherwise
    if entry.get("number"):
        key = "issue" if item_type == "journalArticle" else "number"
        item[key] = _clean(entry["number"])
    if item.get("pages"):
        item["pages"] = re.sub(r"\s*-+\s*", "-", item["pages"])
    if entry_type == "phdthesis":
        item["type"] = "PhD thesis"
    elif entry_type == "mastersthesis":
        item["type"] = "Master's thesis"
    elif entry.get("type"):
        item["type"] = _clean(entry["type"])
    date = _bibtex_date(entry)
    if date:
        item["date"] = _clean(date)
    if entry.get("ID"):
        item["citationKey"] = entry["ID"]
    if entry.get("eprint") and entry.get("archiveprefix", "").lower() == "arxiv":
        item["extra"] = "\n".join(
            filter(None, [item.get("extra"), f"arXiv: {entry['eprint']}"])
        )
    creators = []
    for bib_field, creator_type in (
        ("author", "author"),
        ("editor", "editor"),
        ("translator", "translator"),
    ):
        if entry.get(bib_field):
            creators.extend(_bibtex_names(entry[bib_field], creator_type))
    if creators:
        item["creators"] = creators
    keywords = entry.get("keywords", "")
    tags = [_clean(k) for k in re.split(r"[,;]", keywords) if k.strip()]
    if tags:
        item["tags"] = [{"tag": t} for t in tags]
    return item


def parse_bibtex(text: str) -> list[dict[str, str]]:
    """Parse BibTeX source into a list of entries, with month macros expanded."""
    parser = bibtexparser.bparser.BibTexParser(
        common_strings=True, ignore_nonstandard_types=False
    )
    return parser.parse(text).entries


def fit_to_schema(
    item: dict[str, Any],
    fields: set[str],
    creator_types: list[str],
) -> tuple[dict[str, Any], list[str]]:
    """Fit an item from :func:`csl_to_zotero` or :func:`bibtex_to_zotero` to its type.

    Renames base fields to the fields that the item type uses, keeps the
    first CSL candidate that the type accepts, and moves an identifier that
    the type has no field for into Extra. Other fields that the type does
    not accept are dropped. Creators with a type that the item type does not
    accept become its primary creator type (the first in ``creator_types``).

    Args:
        item: the converted item.
        fields: the fields that the item type accepts.
        creator_types: the item type's creator types, primary first.

    Returns:
        The item, ready for create_items, and the names of dropped fields.

    """
    item_type = item["itemType"]
    remap = BASE_FIELD_REMAP.get(item_type, {})
    out: dict[str, Any] = {"itemType": item_type}
    # Free text for Extra first, then the "Label: value" lines
    extra_text: list[str] = []
    extra_lines: list[str] = []
    dropped: list[str] = []

    def place(name: str, candidates: list[str], value: str) -> None:
        if candidates == ["extra"]:
            extra_text.append(value)
            return
        for base in candidates:
            field = remap.get(base, base)
            if field in fields:
                out.setdefault(field, value)
                return
        label = EXTRA_LABELS.get(candidates[0])
        if label:
            extra_lines.append(f"{label}: {value}")
        else:
            dropped.append(name)

    for var, (candidates, value) in item.get("_candidates", {}).items():
        place(var, candidates, value)
    for key, value in item.items():
        if key not in {"itemType", "creators", "tags", "_candidates"}:
            place(key, [key], value)
    extra = [*extra_text, *dict.fromkeys(extra_lines)]
    if extra and "extra" in fields:
        out["extra"] = "\n".join(extra)
    creators = []
    for creator in item.get("creators", []):
        if creator["creatorType"] in creator_types:
            creators.append(creator)
        elif creator_types:
            creators.append({**creator, "creatorType": creator_types[0]})
    if creators:
        out["creators"] = creators
    if item.get("tags"):
        out["tags"] = item["tags"]
    return out, dropped


def fetch_doi_csl(doi: str) -> dict[str, Any]:
    """Fetch CSL JSON metadata for a DOI from doi.org.

    doi.org passes the request to the DOI's registration agency (Crossref,
    DataCite, mEDRA), and each returns CSL JSON.

    Raises:
        DOILookupError: the DOI is unknown, or the lookup failed.

    """
    norm = normalise_doi(doi)
    if not norm.startswith("10."):
        msg = f"Not a DOI: {doi!r}"
        raise DOILookupError(msg)
    headers = {
        "Accept": "application/vnd.citationstyles.csl+json",
        "User-Agent": f"pyzotero/{__version__} (https://github.com/urschrei/pyzotero)",
    }
    try:
        with httpx2.Client(timeout=DOI_TIMEOUT, follow_redirects=True) as client:
            response = client.get(f"https://doi.org/{norm}", headers=headers)
    except httpx2.HTTPError as e:
        msg = f"DOI lookup for {doi} failed: {e}"
        raise DOILookupError(msg) from e
    if response.status_code == httpx2.codes.NOT_FOUND:
        msg = f"DOI not found: {doi}"
        raise DOILookupError(msg)
    if response.status_code != httpx2.codes.OK:
        msg = f"DOI lookup for {doi} failed: HTTP {response.status_code}"
        raise DOILookupError(msg)
    try:
        return response.json()
    except ValueError as e:
        msg = f"doi.org returned no CSL JSON for {doi}"
        raise DOILookupError(msg) from e


def _isbn_check_digit_10(digits: str) -> str:
    total = sum((10 - i) * int(d) for i, d in enumerate(digits[:9]))
    check = (11 - total % 11) % 11
    return "X" if check == 10 else str(check)  # noqa: PLR2004


def _isbn_check_digit_13(digits: str) -> str:
    total = sum((3 if i % 2 else 1) * int(d) for i, d in enumerate(digits[:12]))
    return str((10 - total % 10) % 10)


def normalise_isbn(text: str) -> str | None:
    """Return an ISBN as 13 digits, or None if ``text`` is not a valid ISBN.

    Accepts ISBN-10 and ISBN-13, with or without hyphens, spaces or an
    "ISBN" prefix, and checks the check digit.
    """
    raw = re.sub(r"^isbn(?:-1[03])?:?", "", text.strip(), flags=re.IGNORECASE)
    digits = re.sub(r"[\s\-]", "", raw).upper()
    if re.fullmatch(r"\d{9}[\dX]", digits):
        if _isbn_check_digit_10(digits) != digits[9]:
            return None
        body = "978" + digits[:9]
        return body + _isbn_check_digit_13(body)
    if re.fullmatch(r"97[89]\d{10}", digits):
        if _isbn_check_digit_13(digits) != digits[12]:
            return None
        return digits
    return None


def isbn_set(text: str) -> set[str]:
    """Return the valid ISBNs in a Zotero ISBN field, as 13 digits.

    The field can hold several ISBNs, separated by spaces or commas.
    """
    found = (normalise_isbn(m) for m in re.findall(r"[\dXx][\dXx\-]{8,16}", text))
    return {isbn for isbn in found if isbn}


def normalise_arxiv_id(text: str) -> str | None:
    """Return an arXiv identifier without its version, or None if it is not one."""
    raw = ARXIV_PREFIX_RE.sub("", text.strip())
    raw = re.sub(r"(?:\.pdf)?/?$", "", raw)
    raw = re.sub(r"v\d+$", "", raw)
    return raw if ARXIV_ID_RE.match(raw) else None


def classify_identifier(text: str) -> tuple[str, str]:
    """Return ("doi" | "arxiv" | "isbn", the normalised identifier).

    Raises:
        MetadataLookupError: ``text`` is none of these.

    """
    doi = normalise_doi(text)
    if doi.startswith("10.") and "/" in doi:
        return "doi", doi
    arxiv = normalise_arxiv_id(text)
    if arxiv:
        return "arxiv", arxiv
    isbn = normalise_isbn(text)
    if isbn:
        return "isbn", isbn
    msg = f"Not a DOI, arXiv ID or ISBN: {text!r}"
    raise MetadataLookupError(msg)


def _get_json(url: str, params: dict[str, str], what: str) -> Any:
    """GET a JSON document, or raise MetadataLookupError."""
    headers = {
        "User-Agent": f"pyzotero/{__version__} (https://github.com/urschrei/pyzotero)"
    }
    try:
        with httpx2.Client(timeout=DOI_TIMEOUT, follow_redirects=True) as client:
            response = client.get(url, params=params, headers=headers)
    except httpx2.HTTPError as e:
        msg = f"{what} failed: {e}"
        raise MetadataLookupError(msg) from e
    if response.status_code != httpx2.codes.OK:
        msg = f"{what} failed: HTTP {response.status_code}"
        raise MetadataLookupError(msg)
    try:
        return response.json()
    except ValueError as e:
        msg = f"{what} returned no JSON"
        raise MetadataLookupError(msg) from e


def _person(name: str, creator_type: str = "author") -> dict[str, str]:
    """Split a display name into a Zotero creator: "Last, First" or "First Last"."""
    if "," in name:
        last, first = (part.strip() for part in name.split(",", 1))
    else:
        first, _, last = name.strip().rpartition(" ")
    if not first:
        return {"creatorType": creator_type, "name": last}
    return {"creatorType": creator_type, "firstName": first, "lastName": last}


def _open_library_book(isbn: str) -> dict[str, Any] | None:
    """Return a book item from Open Library, or None if it has no record."""
    data = _get_json(
        OPEN_LIBRARY_URL,
        {"bibkeys": f"ISBN:{isbn}", "format": "json", "jscmd": "data"},
        "Open Library lookup",
    ).get(f"ISBN:{isbn}")
    if not data or not data.get("title"):
        return None
    title = data["title"]
    if data.get("subtitle"):
        title = f"{title}: {data['subtitle']}"
    item: dict[str, Any] = {
        "itemType": "book",
        "title": title,
        "ISBN": isbn,
        "libraryCatalog": "Open Library",
        "creators": [
            _person(a["name"]) for a in data.get("authors", []) if a.get("name")
        ],
    }
    for key, field in (("publishers", "publisher"), ("publish_places", "place")):
        if data.get(key):
            item[field] = data[key][0].get("name", "")
    if data.get("publish_date"):
        item["date"] = data["publish_date"]
    if data.get("number_of_pages"):
        item["numPages"] = str(data["number_of_pages"])
    return item


def _google_books_book(isbn: str) -> dict[str, Any] | None:
    """Return a book item from Google Books, or None if it has no record."""
    found = _get_json(GOOGLE_BOOKS_URL, {"q": f"isbn:{isbn}"}, "Google Books lookup")
    if not found.get("items"):
        return None
    info = found["items"][0].get("volumeInfo", {})
    if not info.get("title"):
        return None
    title = info["title"]
    if info.get("subtitle"):
        title = f"{title}: {info['subtitle']}"
    item: dict[str, Any] = {
        "itemType": "book",
        "title": title,
        "ISBN": isbn,
        "libraryCatalog": "Google Books",
        "creators": [_person(a) for a in info.get("authors", [])],
    }
    for key, field in (
        ("publisher", "publisher"),
        ("publishedDate", "date"),
        ("language", "language"),
        ("description", "abstractNote"),
    ):
        if info.get(key):
            item[field] = info[key]
    if info.get("pageCount"):
        item["numPages"] = str(info["pageCount"])
    return item


def fetch_isbn(isbn: str) -> dict[str, Any]:
    """Return a book item for an ISBN, from Open Library or else Google Books.

    The item uses Zotero base field names; pass it to :func:`fit_to_schema`.

    Raises:
        MetadataLookupError: neither service has the ISBN, or both lookups
            failed.

    """
    errors = []
    for source in (_open_library_book, _google_books_book):
        try:
            item = source(isbn)
        except MetadataLookupError as e:
            errors.append(str(e))
            continue
        if item:
            return item
    detail = f" ({'; '.join(errors)})" if errors else ""
    msg = f"No metadata found for ISBN {isbn}{detail}"
    raise MetadataLookupError(msg)


def lookup_identifier(text: str) -> tuple[str, str, dict[str, Any]]:
    """Look up a DOI, arXiv ID or ISBN.

    Returns:
        Its kind ("doi", "arxiv" or "isbn"), the normalised identifier, and
        the converted item.

    An arXiv ID goes through the DOI that arXiv registers for every paper
    (10.48550/arXiv.<id>), with DataCite supplying the metadata.

    Raises:
        MetadataLookupError: the identifier is not recognised, or has no
            metadata.

    """
    kind, value = classify_identifier(text)
    if kind == "isbn":
        return kind, value, fetch_isbn(value)
    if kind == "arxiv":
        item = csl_to_zotero(fetch_doi_csl(f"10.48550/arXiv.{value}"))
        item["number"] = f"arXiv:{value}"
        item["url"] = f"https://arxiv.org/abs/{value}"
        return kind, value, item
    return kind, value, csl_to_zotero(fetch_doi_csl(value))


def open_access_pdf_url(doi: str) -> str | None:
    """Return the URL of an open-access PDF for a DOI, or None if none is known.

    An arXiv DOI goes straight to arXiv. Otherwise Semantic Scholar supplies
    the paper's arXiv ID, if it has one, or its open-access PDF location.

    Raises:
        SemanticScholarError: the Semantic Scholar lookup failed, other than
            by not knowing the paper.

    """
    norm = normalise_doi(doi)
    if norm.startswith(ARXIV_DOI_PREFIX):
        return f"https://arxiv.org/pdf/{norm[len(ARXIV_DOI_PREFIX) :]}"
    try:
        paper = get_paper(norm, id_type="doi")
    except PaperNotFoundError:
        return None
    if not paper:
        return None
    if paper.get("arxivId"):
        return f"https://arxiv.org/pdf/{paper['arxivId']}"
    return paper.get("openAccessPdfUrl") or None


def _save_pdf(response: httpx2.Response, url: str, path: Path) -> None:
    """Write a streamed response to ``path`` if it is a PDF within the size limit."""
    if response.status_code != httpx2.codes.OK:
        msg = f"Download from {url} failed: HTTP {response.status_code}"
        raise PDFDownloadError(msg)
    size = 0
    head = b""
    with path.open("wb") as fh:
        for chunk in response.iter_bytes():
            if len(head) < 1024:  # noqa: PLR2004
                head += chunk[:1024]
            size += len(chunk)
            if size > MAX_PDF_BYTES:
                msg = f"{url} is larger than {MAX_PDF_BYTES // 2**20} MB"
                raise PDFDownloadError(msg)
            fh.write(chunk)
    # Some servers send a few bytes of whitespace before the signature
    if not head.lstrip().startswith(b"%PDF-"):
        msg = f"{url} is not a PDF"
        raise PDFDownloadError(msg)


def download_pdf(url: str, path: Path) -> Path:
    """Download a PDF to ``path``.

    Many open-access locations are landing pages rather than files, so the
    download must start with the PDF signature.

    Raises:
        PDFDownloadError: the request failed, the response is not a PDF, or
            it is larger than MAX_PDF_BYTES.

    """
    if not url.startswith(("https://", "http://")):
        msg = f"Not a web URL: {url}"
        raise PDFDownloadError(msg)
    headers = {
        "User-Agent": f"pyzotero/{__version__} (https://github.com/urschrei/pyzotero)"
    }
    try:
        with (
            httpx2.Client(timeout=PDF_TIMEOUT, follow_redirects=True) as client,
            client.stream("GET", url, headers=headers) as response,
        ):
            _save_pdf(response, url, path)
    except httpx2.HTTPError as e:
        path.unlink(missing_ok=True)
        msg = f"Download from {url} failed: {e}"
        raise PDFDownloadError(msg) from e
    except PDFDownloadError:
        path.unlink(missing_ok=True)
        raise
    return path
