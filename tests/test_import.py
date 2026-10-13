"""Tests for converting CSL JSON and BibTeX to Zotero items."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx2
import pytest

from pyzotero import _import
from pyzotero._import import (
    DOILookupError,
    MetadataLookupError,
    PDFDownloadError,
    bibtex_to_zotero,
    classify_identifier,
    csl_to_zotero,
    download_pdf,
    fetch_doi_csl,
    fetch_isbn,
    fit_to_schema,
    isbn_set,
    lookup_identifier,
    open_access_pdf_url,
    parse_bibtex,
)
from pyzotero.semantic_scholar import PaperNotFoundError

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
        ("license_", "expected"),
        [
            ("CC BY 4.0", "CC BY 4.0"),
            # Crossref's form, with one URL for each content version
            (
                [
                    {
                        "start": {"date-parts": [[2018, 2, 13]]},
                        "content-version": "vor",
                        "URL": "http://creativecommons.org/licenses/by/4.0/",
                    },
                    {
                        "content-version": "tdm",
                        "URL": "http://creativecommons.org/licenses/by/4.0/",
                    },
                    {
                        "content-version": "am",
                        "URL": "https://example.org/terms",
                    },
                ],
                "http://creativecommons.org/licenses/by/4.0/, "
                "https://example.org/terms",
            ),
        ],
    )
    def test_license(self, license_, expected):
        csl = {**CROSSREF_CSL, "license": license_}
        item, _ = fit(csl_to_zotero(csl), {"title", "rights"})
        assert item["rights"] == expected

    @pytest.mark.parametrize(
        ("abstract", "expected"),
        [
            ("Plain text, & no markup", "Plain text, & no markup"),
            (
                "<jats:title>Abstract</jats:title>"
                "<jats:p>First &amp; <jats:italic>in</jats:italic>\n  line &lt;5</jats:p>"
                "<jats:sec><jats:title>Methods</jats:title>"
                "<jats:p>Second</jats:p></jats:sec>",
                "First & in line <5\nMethods\nSecond",
            ),
        ],
    )
    def test_jats_abstract(self, abstract, expected):
        csl = {**CROSSREF_CSL, "abstract": abstract}
        item, _ = fit(csl_to_zotero(csl), {"title", "abstractNote"})
        assert item["abstractNote"] == expected

    def test_license_without_urls_is_dropped(self):
        csl = {**CROSSREF_CSL, "license": [{"content-version": "vor"}]}
        item, _ = fit(csl_to_zotero(csl), {"title", "rights"})
        assert "rights" not in item

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


class TestOpenAccessPDF:
    def test_arxiv_doi_needs_no_lookup(self):
        with patch("pyzotero._import.get_paper") as get_paper:
            url = open_access_pdf_url("https://doi.org/10.48550/arXiv.2001.00001")
        assert url == "https://arxiv.org/pdf/2001.00001"
        get_paper.assert_not_called()

    def test_arxiv_id_preferred(self):
        paper = {"arxivId": "1234.5678", "openAccessPdfUrl": "https://pub.example/x"}
        with patch("pyzotero._import.get_paper", return_value=paper) as get_paper:
            assert open_access_pdf_url("10.1/x") == "https://arxiv.org/pdf/1234.5678"
        get_paper.assert_called_once_with("10.1/x", id_type="doi")

    def test_open_access_location(self):
        paper = {"arxivId": None, "openAccessPdfUrl": "https://pub.example/x.pdf"}
        with patch("pyzotero._import.get_paper", return_value=paper):
            assert open_access_pdf_url("10.1/x") == "https://pub.example/x.pdf"

    def test_none_known(self):
        with patch("pyzotero._import.get_paper", side_effect=PaperNotFoundError):
            assert open_access_pdf_url("10.1/x") is None
        with patch("pyzotero._import.get_paper", return_value={"arxivId": None}):
            assert open_access_pdf_url("10.1/x") is None


def _serving(handler):
    """Patch the download client to answer requests with ``handler``."""
    real_client = httpx2.Client

    def client(**kwargs):
        return real_client(transport=httpx2.MockTransport(handler), **kwargs)

    return patch("pyzotero._import.httpx2.Client", side_effect=client)


class TestDownloadPDF:
    def test_saves_pdf(self, tmp_path):
        body = b"%PDF-1.7\n" + b"x" * 100_000
        with _serving(lambda request: httpx2.Response(200, content=body)):
            path = download_pdf("https://example.com/a.pdf", tmp_path / "a.pdf")
        assert path.read_bytes() == body

    def test_follows_redirects(self, tmp_path):
        def handler(request):
            if request.url.path == "/start":
                return httpx2.Response(302, headers={"Location": "/file.pdf"})
            return httpx2.Response(200, content=b"%PDF-1.4 ok")

        with _serving(handler):
            path = download_pdf("https://example.com/start", tmp_path / "a.pdf")
        assert path.read_bytes() == b"%PDF-1.4 ok"

    def test_landing_page_rejected_and_removed(self, tmp_path):
        target = tmp_path / "a.pdf"
        html = b"<!doctype html><html>landing page</html>"
        with (
            _serving(lambda request: httpx2.Response(200, content=html)),
            pytest.raises(PDFDownloadError, match="not a PDF"),
        ):
            download_pdf("https://example.com/a", target)
        assert not target.exists()

    def test_http_error(self, tmp_path):
        with (
            _serving(lambda request: httpx2.Response(403)),
            pytest.raises(PDFDownloadError, match="HTTP 403"),
        ):
            download_pdf("https://example.com/a.pdf", tmp_path / "a.pdf")

    def test_too_large(self, tmp_path):
        body = b"%PDF-1.7\n" + b"x" * 5000
        with (
            patch("pyzotero._import.MAX_PDF_BYTES", 1000),
            _serving(lambda request: httpx2.Response(200, content=body)),
            pytest.raises(PDFDownloadError, match="larger than"),
        ):
            download_pdf("https://example.com/a.pdf", tmp_path / "a.pdf")
        assert not (tmp_path / "a.pdf").exists()

    def test_only_web_urls(self, tmp_path):
        with pytest.raises(PDFDownloadError, match="Not a web URL"):
            download_pdf("file:///etc/passwd", tmp_path / "a.pdf")


class TestIdentifiers:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("10.1038/nature14539", ("doi", "10.1038/nature14539")),
            ("https://doi.org/10.1/X", ("doi", "10.1/x")),
            ("doi:10.1/x", ("doi", "10.1/x")),
            ("2001.00001", ("arxiv", "2001.00001")),
            ("arXiv:2001.00001v3", ("arxiv", "2001.00001")),
            ("https://arxiv.org/abs/hep-th/9901001v2", ("arxiv", "hep-th/9901001")),
            ("https://arxiv.org/pdf/2101.12345.pdf", ("arxiv", "2101.12345")),
            ("math.GT/0309136", ("arxiv", "math.GT/0309136")),
            ("978-0-262-03384-8", ("isbn", "9780262033848")),
            ("ISBN 0-262-03384-4", ("isbn", "9780262033848")),
            ("isbn:080442957X", ("isbn", "9780804429573")),
        ],
    )
    def test_classify(self, text, expected):
        assert classify_identifier(text) == expected

    @pytest.mark.parametrize(
        "text", ["hello", "9780262033849", "0262033845", "12345", "2001.001"]
    )
    def test_unrecognised(self, text):
        with pytest.raises(MetadataLookupError, match="Not a DOI, arXiv ID or ISBN"):
            classify_identifier(text)

    def test_isbn_set_reads_several(self):
        field = "978-0-262-03384-8 0-8044-2957-X, not-an-isbn"
        assert isbn_set(field) == {"9780262033848", "9780804429573"}


OPEN_LIBRARY = {
    "ISBN:9780262033848": {
        "title": "Introduction to Algorithms",
        "subtitle": "Third Edition",
        "authors": [{"name": "Thomas H. Cormen"}, {"name": "Leiserson, Charles E."}],
        "publishers": [{"name": "MIT Press"}],
        "publish_places": [{"name": "Cambridge, Mass"}],
        "publish_date": "2009",
        "number_of_pages": 1292,
    }
}

GOOGLE_BOOKS = {
    "items": [
        {
            "volumeInfo": {
                "title": "Introduction to Algorithms",
                "authors": ["Thomas H. Cormen", "Plato"],
                "publisher": "MIT Press",
                "publishedDate": "2009-07-31",
                "pageCount": 1312,
                "language": "en",
            }
        }
    ]
}


def _json_service(responses):
    """Patch _get_json: each URL maps to a response, or an exception to raise."""

    def get_json(url, params, what):
        response = responses[url]
        if isinstance(response, Exception):
            raise response
        return response

    return patch("pyzotero._import._get_json", side_effect=get_json)


class TestFetchISBN:
    def test_open_library(self):
        with _json_service({_import.OPEN_LIBRARY_URL: OPEN_LIBRARY}):
            item = fetch_isbn("9780262033848")
        assert item["title"] == "Introduction to Algorithms: Third Edition"
        assert item["creators"] == [
            {"creatorType": "author", "firstName": "Thomas H.", "lastName": "Cormen"},
            {
                "creatorType": "author",
                "firstName": "Charles E.",
                "lastName": "Leiserson",
            },
        ]
        assert item["publisher"] == "MIT Press"
        assert item["place"] == "Cambridge, Mass"
        assert item["numPages"] == "1292"
        assert item["libraryCatalog"] == "Open Library"

    def test_falls_back_to_google_books(self):
        services = {
            _import.OPEN_LIBRARY_URL: {},
            _import.GOOGLE_BOOKS_URL: GOOGLE_BOOKS,
        }
        with _json_service(services):
            item = fetch_isbn("9780262033848")
        assert item["libraryCatalog"] == "Google Books"
        assert item["date"] == "2009-07-31"
        assert item["creators"][1] == {"creatorType": "author", "name": "Plato"}

    def test_falls_back_when_open_library_fails(self):
        services = {
            _import.OPEN_LIBRARY_URL: MetadataLookupError("HTTP 503"),
            _import.GOOGLE_BOOKS_URL: GOOGLE_BOOKS,
        }
        with _json_service(services):
            assert fetch_isbn("9780262033848")["libraryCatalog"] == "Google Books"

    def test_not_found(self):
        services = {
            _import.OPEN_LIBRARY_URL: MetadataLookupError("Open Library lookup failed"),
            _import.GOOGLE_BOOKS_URL: {"totalItems": 0},
        }
        with (
            _json_service(services),
            pytest.raises(
                MetadataLookupError, match=r"No metadata found.*Open Library"
            ),
        ):
            fetch_isbn("9780262033848")


class TestLookupIdentifier:
    def test_arxiv_goes_through_its_doi(self):
        csl = {
            "type": "article",
            "title": "A Preprint",
            "publisher": "arXiv",
            "DOI": "10.48550/arXiv.2001.00001",
        }
        with patch("pyzotero._import.fetch_doi_csl", return_value=csl) as fetch:
            kind, value, item = lookup_identifier("arXiv:2001.00001v2")
        fetch.assert_called_once_with("10.48550/arXiv.2001.00001")
        assert (kind, value) == ("arxiv", "2001.00001")
        fitted, _ = fit(
            item,
            {"title", "repository", "archiveID", "url", "DOI", "extra"},
        )
        assert fitted["itemType"] == "preprint"
        assert fitted["archiveID"] == "arXiv:2001.00001"
        assert fitted["repository"] == "arXiv"
        assert fitted["url"] == "https://arxiv.org/abs/2001.00001"

    def test_isbn(self):
        with patch("pyzotero._import.fetch_isbn", return_value={"itemType": "book"}):
            assert lookup_identifier("0-262-03384-4") == (
                "isbn",
                "9780262033848",
                {"itemType": "book"},
            )


class TestGetJSON:
    def test_returns_json_with_params(self):
        def handler(request):
            assert request.url.params["q"] == "isbn:1"
            assert request.headers["User-Agent"].startswith("pyzotero/")
            return httpx2.Response(200, json={"ok": True})

        with _serving(handler):
            assert _import._get_json("https://x.example/", {"q": "isbn:1"}, "Test") == {
                "ok": True
            }

    def test_http_error(self):
        with (
            _serving(lambda request: httpx2.Response(500)),
            pytest.raises(MetadataLookupError, match="Test failed: HTTP 500"),
        ):
            _import._get_json("https://x.example/", {}, "Test")

    def test_not_json(self):
        with (
            _serving(lambda request: httpx2.Response(200, content=b"<html>")),
            pytest.raises(MetadataLookupError, match="returned no JSON"),
        ):
            _import._get_json("https://x.example/", {}, "Test")
