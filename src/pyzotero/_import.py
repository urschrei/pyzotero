"""Convert CSL JSON and BibTeX records to Zotero items, and look up DOIs.

The mappings follow the CSL section of the Zotero schema
(https://github.com/zotero/zotero-schema). A converted item uses Zotero's
base field names until :func:`fit_to_schema` renames each field to the one
its item type uses, and moves what the type does not accept into Extra.
"""

from __future__ import annotations

import re
from typing import Any

import bibtexparser
import httpx2
from bibtexparser.customization import splitname
from bibtexparser.latexenc import latex_to_unicode

from pyzotero import __version__
from pyzotero._helpers import normalise_doi

DOI_TIMEOUT = 30.0

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


class DOILookupError(Exception):
    """Raised when doi.org has no metadata for a DOI, or the lookup fails."""


def _text(value: Any) -> str:
    """Return a CSL value as a string. Lists (e.g. ISSN) are joined."""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value if v)
    return str(value).strip()


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
        # The candidates are alternatives for different item types. Keep them
        # all; fit_to_schema keeps the first that the type accepts.
        item.setdefault("_candidates", {})[var] = (candidates, _text(value))
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
