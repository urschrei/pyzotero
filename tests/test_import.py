"""Tests for converting CSL JSON and BibTeX to Zotero items."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx2
import pytest

from pyzotero._import import (
    DOILookupError,
    bibtex_to_zotero,
    csl_to_zotero,
    fetch_doi_csl,
    fit_to_schema,
    parse_bibtex,
)

# The shape of doi.org's CSL JSON for a Crossref journal article
CROSSREF_CSL = {
    "type": "article-journal",
    "title": "Deep learning",
    "author": [
        {"given": "Yann", "family": "LeCun", "sequence": "first", "affiliation": []},
        {"given": "Yoshua", "family": "Bengio", "sequence": "additional"},
        {"literal": "Some Consortium"},
    ],
    "container-title": "Nature",
    "container-title-short": "Nature",
    "volume": "521",
    "issue": "7553",
    "page": "436-444",
    "issued": {"date-parts": [[2015, 5, 27]]},
    "DOI": "10.1038/nature14539",
    "URL": "https://doi.org/10.1038/nature14539",
    "ISSN": ["0028-0836", "1476-4687"],
    "publisher": "Springer Science and Business Media LLC",
    "source": "Crossref",
}

ARTICLE_FIELDS = {
    "title",
    "publicationTitle",
    "journalAbbreviation",
    "volume",
    "issue",
    "pages",
    "date",
    "DOI",
    "url",
    "ISSN",
    "libraryCatalog",
    "extra",
}


def fit(item, fields, creator_types=("author", "contributor", "editor")):
    return fit_to_schema(item, set(fields), list(creator_types))


class TestCSL:
    def test_journal_article(self):
        item, dropped = fit(csl_to_zotero(CROSSREF_CSL), ARTICLE_FIELDS)
        assert item["itemType"] == "journalArticle"
        assert item["title"] == "Deep learning"
        assert item["publicationTitle"] == "Nature"
        assert item["pages"] == "436-444"
        assert item["date"] == "2015-05-27"
        assert item["DOI"] == "10.1038/nature14539"
        assert item["ISSN"] == "0028-0836, 1476-4687"
        assert item["creators"] == [
            {"creatorType": "author", "firstName": "Yann", "lastName": "LeCun"},
            {"creatorType": "author", "firstName": "Yoshua", "lastName": "Bengio"},
            {"creatorType": "author", "name": "Some Consortium"},
        ]
        assert dropped == ["publisher"]

    def test_chapter_uses_book_title(self):
        csl = {**CROSSREF_CSL, "type": "chapter"}
        item, _ = fit(csl_to_zotero(csl), {"title", "bookTitle", "DOI", "extra"})
        assert item["itemType"] == "bookSection"
        assert item["bookTitle"] == "Nature"

    def test_identifier_without_field_goes_to_extra(self):
        csl = {**CROSSREF_CSL, "note": "Some note"}
        item, _ = fit(csl_to_zotero(csl), {"title", "extra"})
        assert item["extra"].splitlines() == [
            "Some note",
            "DOI: 10.1038/nature14539",
            "ISSN: 0028-0836, 1476-4687",
        ]

    @pytest.mark.parametrize(
        ("csl_type", "zotero_type"),
        [
            ("journal-article", "journalArticle"),
            ("proceedings-article", "conferencePaper"),
            ("posted-content", "preprint"),
            ("no-such-type", "document"),
        ],
    )
    def test_crossref_and_unknown_types(self, csl_type, zotero_type):
        assert csl_to_zotero({"type": csl_type})["itemType"] == zotero_type

    @pytest.mark.parametrize(
        ("issued", "expected"),
        [
            ({"date-parts": [[2015]]}, "2015"),
            ({"date-parts": [[2015, 3]]}, "2015-03"),
            ({"raw": "Spring 2015"}, "Spring 2015"),
            ({"literal": "n.d."}, "n.d."),
        ],
    )
    def test_dates(self, issued, expected):
        assert csl_to_zotero({"type": "book", "issued": issued})["date"] == expected

    def test_particle_joins_family_name(self):
        csl = {
            "type": "book",
            "author": [
                {
                    "given": "Ludwig",
                    "family": "Beethoven",
                    "non-dropping-particle": "van",
                }
            ],
        }
        assert csl_to_zotero(csl)["creators"][0]["lastName"] == "van Beethoven"

    def test_invalid_creator_type_becomes_primary(self):
        csl = {"type": "graphic", "author": [{"family": "Klee", "given": "Paul"}]}
        item, _ = fit(csl_to_zotero(csl), {"title"}, ("artist", "contributor"))
        assert item["creators"][0]["creatorType"] == "artist"


BIBTEX = r"""
@article{lecun2015,
  author = {LeCun, Yann and {World Health Organization} and {Barnes and Noble}
            and van der Berg, Jan and M{\"u}ller, Hans},
  title = {Deep {L}earning},
  journal = {Nature},
  year = 2015,
  month = may,
  volume = 521,
  number = 7553,
  pages = {436--444},
  doi = {10.1038/nature14539},
  keywords = {ml, deep learning},
  note = {G\'eza's note},
}
@phdthesis{kovacs2001,
  author = {Kov\'acs, G\'eza},
  title = {A Thesis},
  school = {ETH Z{\"u}rich},
  year = {2001},
}
@misc{arxiv2020,
  title = {A Preprint},
  eprint = {2001.00001},
  archivePrefix = {arXiv},
  year = {2020},
}
"""


class TestBibTeX:
    @pytest.fixture
    def entries(self):
        return {e["ID"]: bibtex_to_zotero(e) for e in parse_bibtex(BIBTEX)}

    def test_article(self, entries):
        item = entries["lecun2015"]
        assert item["itemType"] == "journalArticle"
        assert item["title"] == "Deep Learning"
        assert item["publicationTitle"] == "Nature"
        assert item["issue"] == "7553"
        assert item["pages"] == "436-444"
        assert item["date"] == "2015-05"
        assert item["DOI"] == "10.1038/nature14539"
        assert item["extra"] == "Géza's note"
        assert item["citationKey"] == "lecun2015"
        assert item["tags"] == [{"tag": "ml"}, {"tag": "deep learning"}]

    def test_names(self, entries):
        assert entries["lecun2015"]["creators"] == [
            {"creatorType": "author", "firstName": "Yann", "lastName": "LeCun"},
            {"creatorType": "author", "name": "World Health Organization"},
            {"creatorType": "author", "name": "Barnes and Noble"},
            {"creatorType": "author", "firstName": "Jan", "lastName": "van der Berg"},
            {"creatorType": "author", "firstName": "Hans", "lastName": "Müller"},
        ]

    def test_thesis(self, entries):
        item = entries["kovacs2001"]
        assert item["itemType"] == "thesis"
        assert item["type"] == "PhD thesis"
        fitted, _ = fit(item, {"title", "university", "thesisType", "date", "extra"})
        assert fitted["university"] == "ETH Zürich"
        assert fitted["creators"][0] == {
            "creatorType": "author",
            "firstName": "Géza",
            "lastName": "Kovács",
        }

    def test_citation_key_without_field_goes_to_extra(self, entries):
        fitted, _ = fit(entries["kovacs2001"], {"title", "extra"})
        assert fitted["extra"] == "Citation Key: kovacs2001"

    def test_arxiv_eprint(self, entries):
        assert entries["arxiv2020"]["itemType"] == "document"
        assert entries["arxiv2020"]["extra"] == "arXiv: 2001.00001"


def _mock_client(response):
    client = MagicMock()
    client.__enter__.return_value.get.return_value = response
    return client


class TestFetchDOI:
    def test_returns_csl(self):
        response = httpx2.Response(200, json=CROSSREF_CSL)
        with patch(
            "pyzotero._import.httpx2.Client", return_value=_mock_client(response)
        ) as cls:
            assert fetch_doi_csl("https://doi.org/10.1038/NATURE14539") == CROSSREF_CSL
        get = cls.return_value.__enter__.return_value.get
        assert get.call_args[0][0] == "https://doi.org/10.1038/nature14539"
        assert "citationstyles" in get.call_args[1]["headers"]["Accept"]

    def test_not_a_doi(self):
        with pytest.raises(DOILookupError, match="Not a DOI"):
            fetch_doi_csl("not-a-doi")

    def test_not_found(self):
        response = httpx2.Response(404)
        with (
            patch(
                "pyzotero._import.httpx2.Client", return_value=_mock_client(response)
            ),
            pytest.raises(DOILookupError, match="not found"),
        ):
            fetch_doi_csl("10.1234/missing")

    def test_network_error(self):
        client = MagicMock()
        client.__enter__.return_value.get.side_effect = httpx2.ConnectError("down")
        with (
            patch("pyzotero._import.httpx2.Client", return_value=client),
            pytest.raises(DOILookupError, match="down"),
        ):
            fetch_doi_csl("10.1234/x")
