"""Tests for BibTeX responses."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from pyzotero import BibTeX
from pyzotero import zotero as z

from .mock_client import MockClient

ITEMS_URL = "https://api.zotero.org/users/myuserID/items"

PAGE_1 = """
@article{muller2020,
\ttitle = {Über {BibTeX}},
\tauthor = {Müller, Hans},
\tyear = {2020},
}
"""

PAGE_2 = """
@book{smith2021,
\ttitle = {A Book},
\tyear = {2021},
}
"""


def _paged(request, uri, headers):
    start = int(parse_qs(urlparse(uri).query).get("start", ["0"])[0])
    if start == 0:
        headers["Link"] = f'<{ITEMS_URL}?format=bibtex&start=1>; rel="next"'
        return [200, headers, PAGE_1]
    return [200, headers, PAGE_2]


def test_web_api_returns_bibtex():
    mock = MockClient()
    mock.register("GET", ITEMS_URL, body=PAGE_1, content_type="application/x-bibtex")
    zot = z.Zotero("myuserID", "user", "myuserkey", client=mock.client)
    bib = zot.items(format="bibtex")
    assert isinstance(bib, BibTeX)
    assert bib.text == PAGE_1
    assert str(bib) == PAGE_1
    assert len(bib.entries) == 1
    entry = bib.entries[0]
    assert entry["ID"] == "muller2020"
    assert entry["ENTRYTYPE"] == "article"
    assert entry["author"] == "Müller, Hans"
    assert entry["year"] == "2020"


def test_everything_joins_pages():
    mock = MockClient()
    mock.register("GET", ITEMS_URL, body=_paged, content_type="application/x-bibtex")
    zot = z.Zotero("myuserID", "user", "myuserkey", client=mock.client)
    bib = zot.everything(zot.items(format="bibtex"))
    assert isinstance(bib, BibTeX)
    assert [e["ID"] for e in bib.entries] == ["muller2020", "smith2021"]
    assert bib.text == f"{PAGE_1.strip()}\n\n{PAGE_2.strip()}"


def test_join_skips_empty_parts():
    joined = BibTeX.join([BibTeX(PAGE_1), BibTeX("\n"), BibTeX(PAGE_2)])
    assert joined.text == f"{PAGE_1.strip()}\n\n{PAGE_2.strip()}"


def test_empty_response_has_no_entries():
    assert BibTeX("").entries == []


def test_local_api_plain_text_returns_bibtex():
    mock = MockClient()
    zot = z.Zotero("0", "user", local=True, client=mock.client)
    mock.register(
        "GET",
        f"{zot.endpoint}/users/0/items",
        body=PAGE_1.encode("utf-8"),
        content_type="text/plain",
    )
    bib = zot.items(format="bibtex")
    assert isinstance(bib, BibTeX)
    assert bib.text == PAGE_1
    assert bib.entries[0]["author"] == "Müller, Hans"


def test_local_api_other_plain_text_stays_bytes():
    mock = MockClient()
    zot = z.Zotero("0", "user", local=True, client=mock.client)
    mock.register(
        "GET",
        f"{zot.endpoint}/users/0/items",
        body="TY  - JOUR\nER  -\n",
        content_type="text/plain",
    )
    assert zot.items(format="ris") == b"TY  - JOUR\nER  -\n"


def test_parse_normalises_keys_and_expands_months():
    entries = BibTeX("@Article{K1, TITLE = {T}, Month = may, Year = 2020}").entries
    assert entries == [
        {
            "ID": "K1",
            "ENTRYTYPE": "article",
            "title": "T",
            "month": "May",
            "year": "2020",
        }
    ]


def test_parse_keeps_duplicate_keys():
    entries = BibTeX(
        '@string{nat = "Nature"}\n'
        "@misc{K, title = {A}}\n"
        "@misc{K, Title = {B}, journal = nat, month = jun}"
    ).entries
    assert entries == [
        {"ID": "K", "ENTRYTYPE": "misc", "title": "A"},
        {
            "ID": "K",
            "ENTRYTYPE": "misc",
            "title": "B",
            "journal": "Nature",
            "month": "June",
        },
    ]


def test_month_numbers_and_names_become_full_names():
    entries = BibTeX("@misc{A, month = 3}\n@misc{B, month = {october}}").entries
    assert [e["month"] for e in entries] == ["March", "October"]


def test_source_month_macro_replaces_default():
    entries = BibTeX('@string{may = "Mai"}\n@misc{K, month = may}').entries
    assert entries[0]["month"] == "Mai"


def test_parse_resolves_string_macros():
    entries = BibTeX('@string{nat = "Nature"}\n@article{K, journal = nat}').entries
    assert entries[0]["journal"] == "Nature"
