#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the Pyzotero module

Copyright Stephan Hügel, 2011

This file is part of Pyzotero.

Pyzotero is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Pyzotero is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Pyzotero. If not, see <http://www.gnu.org/licenses/>.
"""

import unittest
from httpretty import HTTPretty, httprettified
from pyzotero.pyzotero import zotero as z
from datetime import datetime
import pytz


class ZoteroTests(unittest.TestCase):
    """ Tests for pyzotero
    """
    def setUp(self):
        """ Set stuff up
        """
        # https://www.zotero.org/support/dev/web_api/v3/basics#example_get_requests_and_responses
        self.new_items_doc = """[
    {
        "key": "NM66T6EF",
        "version": 1,
        "library": {
            "type": "user",
            "id": 475425,
            "name": "Z public library",
            "links": {
                "alternate": {
                    "href": "https://www.zotero.org/z_public_library",
                    "type": "text/html"
                }
            }
        },
        "links": {
            "self": {
                "href": "https://api.zotero.org/users/475425/items/NM66T6EF",
                "type": "application/json"
            },
            "alternate": {
                "href": "https://www.zotero.org/z_public_library/items/NM66T6EF",
                "type": "text/html"
            }
        },
        "meta": {
            "numChildren": 2
        },
        "data": {
            "key": "NM66T6EF",
            "version": 1,
            "itemType": "webpage",
            "title": "HowStuffWorks \"How Earthquakes Work\"",
            "creators": [

            ],
            "abstractNote": "",
            "websiteTitle": "",
            "websiteType": "",
            "date": "",
            "shortTitle": "",
            "url": "http://science.howstuffworks.com/nature/natural-disasters/earthquake.htm",
            "accessDate": "2011-02-02T22:26:36Z",
            "language": "",
            "rights": "",
            "extra": "",
            "dateAdded": "2011-02-02T22:26:36Z",
            "dateModified": "2011-02-02T22:26:36Z",
            "tags": [

            ],
            "collections": [
                "9KH9TNSJ"
            ],
            "relations": {

            }
        }
    },
    {
        "key": "PQKBRC33",
        "version": 1,
        "library": {
            "type": "user",
            "id": 475425,
            "name": "Z public library",
            "links": {
                "alternate": {
                    "href": "https://www.zotero.org/z_public_library",
                    "type": "text/html"
                }
            }
        },
        "links": {
            "self": {
                "href": "https://api.zotero.org/users/475425/items/PQKBRC33",
                "type": "application/json"
            },
            "alternate": {
                "href": "https://www.zotero.org/z_public_library/items/PQKBRC33",
                "type": "text/html"
            }
        },
        "meta": {
            "creatorSummary": "R. Creighton Buck",
            "parsedDate": "1980-05-01",
            "numChildren": 2
        },
        "data": {
            "key": "PQKBRC33",
            "version": 1,
            "itemType": "journalArticle",
            "title": "Sherlock Holmes in Babylon",
            "creators": [
                {
                    "creatorType": "author",
                    "firstName": "",
                    "lastName": "R. Creighton Buck"
                }
            ],
            "abstractNote": "",
            "publicationTitle": "The American Mathematical Monthly",
            "volume": "87",
            "issue": "5",
            "pages": "335-345",
            "date": "May 01, 1980",
            "series": "",
            "seriesTitle": "",
            "seriesText": "",
            "journalAbbreviation": "",
            "language": "",
            "DOI": "10.2307/2321200",
            "ISSN": "00029890",
            "shortTitle": "",
            "url": "http://www.jstor.org/stable/2321200",
            "accessDate": "2011-02-02T22:25:04Z",
            "archive": "",
            "archiveLocation": "",
            "libraryCatalog": "JSTOR",
            "callNumber": "",
            "rights": "",
            "extra": "ArticleType: research-article / Full publication date: May, 1980 / Copyright © 1980 Mathematical Association of America",
            "dateAdded": "2011-02-02T22:25:04Z",
            "dateModified": "2011-02-02T22:25:04Z",
            "tags": [

            ],
            "collections": [
                "9KH9TNSJ"
            ],
            "relations": {

            }
        }
    },
    {
        "key": "Z8N84QAJ",
        "version": 1,
        "library": {
            "type": "user",
            "id": 475425,
            "name": "Z public library",
            "links": {
                "alternate": {
                    "href": "https://www.zotero.org/z_public_library",
                    "type": "text/html"
                }
            }
        },
        "links": {
            "self": {
                "href": "https://api.zotero.org/users/475425/items/Z8N84QAJ",
                "type": "application/json"
            },
            "alternate": {
                "href": "https://www.zotero.org/z_public_library/items/Z8N84QAJ",
                "type": "text/html"
            }
        },
        "meta": {
            "creatorSummary": "Doyle",
            "parsedDate": "1992-00-00",
            "numChildren": 0
        },
        "data": {
            "key": "Z8N84QAJ",
            "version": 1,
            "itemType": "book",
            "title": "The Annotated Sherlock Holmes: The Four Novels and Fifty-Six Short Stories Complete",
            "creators": [
                {
                    "creatorType": "author",
                    "firstName": "Arthur Conan",
                    "lastName": "Doyle"
                },
                {
                    "creatorType": "contributor",
                    "firstName": "William Stuart",
                    "lastName": "Baring-Gould"
                }
            ],
            "abstractNote": "",
            "series": "",
            "seriesNumber": "",
            "volume": "",
            "numberOfVolumes": "",
            "edition": "",
            "place": "New York",
            "publisher": "Wings Books",
            "date": "1992",
            "numPages": "2",
            "language": "",
            "ISBN": "",
            "shortTitle": "The Annotated Sherlock Holmes",
            "url": "",
            "accessDate": "",
            "archive": "",
            "archiveLocation": "",
            "libraryCatalog": "magik.gmu.edu Library Catalog",
            "callNumber": "PR4620.A5 B3 1992",
            "rights": "",
            "extra": "",
            "dateAdded": "2011-02-02T22:23:59Z",
            "dateModified": "2011-02-02T22:23:59Z",
            "tags": [
                {
                    "tag": "Detective and mystery stories, English",
                    "type": 1
                },
                {
                    "tag": "Fiction",
                    "type": 1
                },
                {
                    "tag": "Holmes, Sherlock (Fictitious character)",
                    "type": 1
                }
            ],
            "collections": [
                "9KH9TNSJ"
            ],
            "relations": {

            }
        }
    },
    {
        "key": "PG5ZCTJT",
        "version": 1,
        "library": {
            "type": "user",
            "id": 475425,
            "name": "Z public library",
            "links": {
                "alternate": {
                    "href": "https://www.zotero.org/z_public_library",
                    "type": "text/html"
                }
            }
        },
        "links": {
            "self": {
                "href": "https://api.zotero.org/users/475425/items/PG5ZCTJT",
                "type": "application/json"
            },
            "alternate": {
                "href": "https://www.zotero.org/z_public_library/items/PG5ZCTJT",
                "type": "text/html"
            }
        },
        "meta": {
            "creatorSummary": "Blum et al.",
            "parsedDate": "2004-00-00",
            "numChildren": 0
        },
        "data": {
            "key": "PG5ZCTJT",
            "version": 1,
            "itemType": "film",
            "title": "The Adventures of Sherlock Holmes",
            "creators": [
                {
                    "creatorType": "contributor",
                    "firstName": "Edwin",
                    "lastName": "Blum"
                },
                {
                    "creatorType": "contributor",
                    "firstName": "William A",
                    "lastName": "Drake"
                },
                {
                    "creatorType": "contributor",
                    "firstName": "Alfred",
                    "lastName": "Werker"
                },
                {
                    "creatorType": "contributor",
                    "firstName": "Basil",
                    "lastName": "Rathbone"
                },
                {
                    "creatorType": "contributor",
                    "firstName": "Nigel",
                    "lastName": "Bruce"
                },
                {
                    "creatorType": "contributor",
                    "firstName": "George",
                    "lastName": "Zucco"
                },
                {
                    "creatorType": "contributor",
                    "firstName": "Ida",
                    "lastName": "Lupino"
                },
                {
                    "creatorType": "contributor",
                    "firstName": "Alan",
                    "lastName": "Marshal"
                },
                {
                    "creatorType": "contributor",
                    "firstName": "William",
                    "lastName": "Gillette"
                },
                {
                    "creatorType": "contributor",
                    "firstName": "Arthur Conan",
                    "lastName": "Doyle"
                },
                {
                    "creatorType": "contributor",
                    "firstName": "Richard",
                    "lastName": "Valley"
                },
                {
                    "creatorType": "contributor",
                    "name": "Twentieth Century-Fox Film Corporation"
                },
                {
                    "creatorType": "contributor",
                    "name": "King World Productions"
                },
                {
                    "creatorType": "contributor",
                    "name": "MPI Home Video (Firm)"
                }
            ],
            "abstractNote": "",
            "distributor": "MPI Home Video",
            "date": "2004",
            "genre": "",
            "videoRecordingFormat": "",
            "runningTime": "",
            "language": "",
            "shortTitle": "",
            "url": "",
            "accessDate": "",
            "archive": "",
            "archiveLocation": "",
            "libraryCatalog": "magik.gmu.edu Library Catalog",
            "callNumber": "PN1997",
            "rights": "",
            "extra": "",
            "dateAdded": "2011-02-02T22:23:55Z",
            "dateModified": "2011-02-02T22:23:55Z",
            "tags": [
                {
                    "tag": "Detective and mystery films",
                    "type": 1
                },
                {
                    "tag": "Feature films",
                    "type": 1
                },
                {
                    "tag": "Holmes, Sherlock (Fictitious character)",
                    "type": 1
                },
                {
                    "tag": "Moriarty, Professor (Fictitious character)",
                    "type": 1
                },
                {
                    "tag": "Murder",
                    "type": 1
                }
            ],
            "collections": [
                "9KH9TNSJ"
            ],
            "relations": {

            }
        }
    },
    {
        "key": "B2VNV5Q7",
        "version": 1,
        "library": {
            "type": "user",
            "id": 475425,
            "name": "Z public library",
            "links": {
                "alternate": {
                    "href": "https://www.zotero.org/z_public_library",
                    "type": "text/html"
                }
            }
        },
        "links": {
            "self": {
                "href": "https://api.zotero.org/users/475425/items/B2VNV5Q7",
                "type": "application/json"
            },
            "alternate": {
                "href": "https://www.zotero.org/z_public_library/items/B2VNV5Q7",
                "type": "text/html"
            }
        },
        "meta": {
            "creatorSummary": "Higham",
            "parsedDate": "1976-00-00",
            "numChildren": 0
        },
        "data": {
            "key": "B2VNV5Q7",
            "version": 1,
            "itemType": "book",
            "title": "The Adventures of Conan Doyle: The Life of the Creator of Sherlock Holmes",
            "creators": [
                {
                    "creatorType": "author",
                    "firstName": "Charles",
                    "lastName": "Higham"
                }
            ],
            "abstractNote": "",
            "series": "",
            "seriesNumber": "",
            "volume": "",
            "numberOfVolumes": "",
            "edition": "1st ed",
            "place": "New York",
            "publisher": "Norton",
            "date": "1976",
            "numPages": "368",
            "language": "",
            "ISBN": "0393075079",
            "shortTitle": "The Adventures of Conan Doyle",
            "url": "",
            "accessDate": "",
            "archive": "",
            "archiveLocation": "",
            "libraryCatalog": "magik.gmu.edu Library Catalog",
            "callNumber": "PR4623",
            "rights": "",
            "extra": "",
            "dateAdded": "2011-02-02T22:23:38Z",
            "dateModified": "2011-02-02T22:23:38Z",
            "tags": [
                {
                    "tag": "Biography",
                    "type": 1
                },
                {
                    "tag": "Doyle, Arthur Conan",
                    "type": 1
                }
            ],
            "collections": [
                "9KH9TNSJ"
            ],
            "relations": {

            }
        }
    },
    {
        "key": "6XDC27WD",
        "version": 1,
        "library": {
            "type": "user",
            "id": 475425,
            "name": "Z public library",
            "links": {
                "alternate": {
                    "href": "https://www.zotero.org/z_public_library",
                    "type": "text/html"
                }
            }
        },
        "links": {
            "self": {
                "href": "https://api.zotero.org/users/475425/items/6XDC27WD",
                "type": "application/json"
            },
            "alternate": {
                "href": "https://www.zotero.org/z_public_library/items/6XDC27WD",
                "type": "text/html"
            }
        },
        "meta": {
            "creatorSummary": "Earnshaw",
            "parsedDate": "2001-00-00",
            "numChildren": 0
        },
        "data": {
            "key": "6XDC27WD",
            "version": 1,
            "itemType": "book",
            "title": "An Actor, and a Rare One: Peter Cushing as Sherlock Holmes",
            "creators": [
                {
                    "creatorType": "author",
                    "firstName": "Tony",
                    "lastName": "Earnshaw"
                }
            ],
            "abstractNote": "",
            "series": "",
            "seriesNumber": "",
            "volume": "",
            "numberOfVolumes": "",
            "edition": "",
            "place": "Lanham, Md",
            "publisher": "Scarecrow Press",
            "date": "2001",
            "numPages": "146",
            "language": "",
            "ISBN": "0810838745",
            "shortTitle": "An Actor, and a Rare One",
            "url": "",
            "accessDate": "",
            "archive": "",
            "archiveLocation": "",
            "libraryCatalog": "magik.gmu.edu Library Catalog",
            "callNumber": "791.43/028/092",
            "rights": "",
            "extra": "",
            "dateAdded": "2011-02-02T22:23:34Z",
            "dateModified": "2011-02-02T22:23:34Z",
            "tags": [
                {
                    "tag": "Cushing, Peter",
                    "type": 1
                },
                {
                    "tag": "Sherlock Holmes films",
                    "type": 1
                }
            ],
            "collections": [
                "9KH9TNSJ"
            ],
            "relations": {

            }
        }
    },
    {
        "key": "ICK5M93W",
        "version": 1,
        "library": {
            "type": "user",
            "id": 475425,
            "name": "Z public library",
            "links": {
                "alternate": {
                    "href": "https://www.zotero.org/z_public_library",
                    "type": "text/html"
                }
            }
        },
        "links": {
            "self": {
                "href": "https://api.zotero.org/users/475425/items/ICK5M93W",
                "type": "application/json"
            },
            "alternate": {
                "href": "https://www.zotero.org/z_public_library/items/ICK5M93W",
                "type": "text/html"
            }
        },
        "meta": {
            "creatorSummary": "Knight",
            "parsedDate": "1980-00-00",
            "numChildren": 0
        },
        "data": {
            "key": "ICK5M93W",
            "version": 1,
            "itemType": "book",
            "title": "Form and Ideology in Crime Fiction",
            "creators": [
                {
                    "creatorType": "author",
                    "firstName": "Stephen",
                    "lastName": "Knight"
                }
            ],
            "abstractNote": "",
            "series": "",
            "seriesNumber": "",
            "volume": "",
            "numberOfVolumes": "",
            "edition": "",
            "place": "Bloomington",
            "publisher": "Indiana University Press",
            "date": "1980",
            "numPages": "202",
            "language": "",
            "ISBN": "0253143837",
            "shortTitle": "",
            "url": "",
            "accessDate": "",
            "archive": "",
            "archiveLocation": "",
            "libraryCatalog": "magik.gmu.edu Library Catalog",
            "callNumber": "PS374.D4",
            "rights": "",
            "extra": "",
            "dateAdded": "2011-02-02T22:22:23Z",
            "dateModified": "2011-02-02T22:22:23Z",
            "tags": [
                {
                    "tag": "Crime in literature",
                    "type": 1
                },
                {
                    "tag": "Detective and mystery stories, American",
                    "type": 1
                },
                {
                    "tag": "Detective and mystery stories, English",
                    "type": 1
                },
                {
                    "tag": "History and criticism",
                    "type": 1
                }
            ],
            "collections": [
                "9KH9TNSJ"
            ],
            "relations": {

            }
        }
    },
    {
        "key": "Z6TE2UMT",
        "version": 1,
        "library": {
            "type": "user",
            "id": 475425,
            "name": "Z public library",
            "links": {
                "alternate": {
                    "href": "https://www.zotero.org/z_public_library",
                    "type": "text/html"
                }
            }
        },
        "links": {
            "self": {
                "href": "https://api.zotero.org/users/475425/items/Z6TE2UMT",
                "type": "application/json"
            },
            "alternate": {
                "href": "https://www.zotero.org/z_public_library/items/Z6TE2UMT",
                "type": "text/html"
            }
        },
        "meta": {
            "numChildren": 1
        },
        "data": {
            "key": "Z6TE2UMT",
            "version": 1,
            "itemType": "webpage",
            "title": "CRCnetBASE - Hematopoietic Stem Cell Transplantation, Stem Cells, and Gene Therapy",
            "creators": [

            ],
            "abstractNote": "",
            "websiteTitle": "",
            "websiteType": "",
            "date": "",
            "shortTitle": "",
            "url": "http://www.crcnetbase.com/doi/abs/10.1201/9781420005509.ch22?prevSearch=%2528%255Bfulltext%253A%2Bcell%255D%2BAND%2B%255Btitle%253A%2Bcell%255D%2529%2BAND%2B%255BpubType%253A%2B109%255D&searchHistoryKey=",
            "accessDate": "2011-02-02T15:21:13Z",
            "language": "",
            "rights": "",
            "extra": "",
            "dateAdded": "2011-02-02T15:21:13Z",
            "dateModified": "2011-02-02T15:21:13Z",
            "tags": [

            ],
            "collections": [
                "BX9965IJ",
                "9KH9TNSJ"
            ],
            "relations": {

            }
        }
    },
    {
        "key": "6MCAN2NC",
        "version": 1,
        "library": {
            "type": "user",
            "id": 475425,
            "name": "Z public library",
            "links": {
                "alternate": {
                    "href": "https://www.zotero.org/z_public_library",
                    "type": "text/html"
                }
            }
        },
        "links": {
            "self": {
                "href": "https://api.zotero.org/users/475425/items/6MCAN2NC",
                "type": "application/json"
            },
            "alternate": {
                "href": "https://www.zotero.org/z_public_library/items/6MCAN2NC",
                "type": "text/html"
            }
        },
        "meta": {
            "creatorSummary": "Fanatico",
            "parsedDate": "2008-12-14",
            "numChildren": 1
        },
        "data": {
            "key": "6MCAN2NC",
            "version": 1,
            "itemType": "artwork",
            "title": "Sherlock Holmes",
            "creators": [
                {
                    "creatorType": "artist",
                    "firstName": "Cine",
                    "lastName": "Fanatico"
                }
            ],
            "abstractNote": "Sherlock Holmes\n\n<a href=\"http://www.mycine.com.ar/\">www.mycine.com.ar/</a>",
            "artworkMedium": "",
            "artworkSize": "",
            "date": "2008-12-14",
            "language": "",
            "shortTitle": "",
            "archive": "",
            "archiveLocation": "",
            "libraryCatalog": "Flickr",
            "callNumber": "",
            "url": "http://www.flickr.com/photos/29745871@N08/3108627911/",
            "accessDate": "2011-02-02T03:24:37Z",
            "rights": "",
            "extra": "",
            "dateAdded": "2011-02-02T03:24:37Z",
            "dateModified": "2011-02-02T03:24:37Z",
            "tags": [
                {
                    "tag": "judelaw",
                    "type": 1
                },
                {
                    "tag": "robertdowneyjr",
                    "type": 1
                },
                {
                    "tag": "sherlockholmes",
                    "type": 1
                }
            ],
            "collections": [
                "QM6T3KHX",
                "TVPC4XK4",
                "9KH9TNSJ"
            ],
            "relations": {

            }
        }
    },
    {
        "key": "GIFZST3I",
        "version": 1,
        "library": {
            "type": "user",
            "id": 475425,
            "name": "Z public library",
            "links": {
                "alternate": {
                    "href": "https://www.zotero.org/z_public_library",
                    "type": "text/html"
                }
            }
        },
        "links": {
            "self": {
                "href": "https://api.zotero.org/users/475425/items/GIFZST3I",
                "type": "application/json"
            },
            "alternate": {
                "href": "https://www.zotero.org/z_public_library/items/GIFZST3I",
                "type": "text/html"
            }
        },
        "meta": {
            "creatorSummary": "Goodman and Jiménez",
            "parsedDate": "1993-00-08",
            "numChildren": 0
        },
        "data": {
            "key": "GIFZST3I",
            "version": 1,
            "itemType": "book",
            "title": "Cell recognition during neuronal development",
            "creators": [
                {
                    "creatorType": "author",
                    "firstName": "C.",
                    "lastName": "Goodman"
                },
                {
                    "creatorType": "author",
                    "firstName": "F.",
                    "lastName": "Jiménez"
                }
            ],
            "abstractNote": "",
            "series": "",
            "seriesNumber": "",
            "volume": "",
            "numberOfVolumes": "",
            "edition": "",
            "place": "",
            "publisher": "Instituto Juan March",
            "date": "08/1993",
            "numPages": "",
            "language": "",
            "ISBN": "978-84-7919-517-5",
            "shortTitle": "",
            "url": "",
            "accessDate": "",
            "archive": "",
            "archiveLocation": "",
            "libraryCatalog": "Agencia del ISBN",
            "callNumber": "",
            "rights": "",
            "extra": "",
            "dateAdded": "2011-01-28T21:45:45Z",
            "dateModified": "2011-01-28T21:45:45Z",
            "tags": [

            ],
            "collections": [
                "BX9965IJ",
                "9KH9TNSJ"
            ],
            "relations": {
                "owl:sameAs": "http://zotero.org/groups/36222/items/U3GSEBPW"
            }
        }
    },
    {
        "key": "CINTCPTB",
        "version": 1,
        "library": {
            "type": "user",
            "id": 475425,
            "name": "Z public library",
            "links": {
                "alternate": {
                    "href": "https://www.zotero.org/z_public_library",
                    "type": "text/html"
                }
            }
        },
        "links": {
            "self": {
                "href": "https://api.zotero.org/users/475425/items/CINTCPTB",
                "type": "application/json"
            },
            "alternate": {
                "href": "https://www.zotero.org/z_public_library/items/CINTCPTB",
                "type": "text/html"
            }
        },
        "meta": {
            "creatorSummary": "Liu",
            "numChildren": 0
        },
        "data": {
            "key": "CINTCPTB",
            "version": 1,
            "itemType": "book",
            "title": "2011: A Jump Start for JIPB",
            "creators": [
                {
                    "creatorType": "author",
                    "firstName": "Chun-Ming",
                    "lastName": "Liu"
                }
            ],
            "abstractNote": "",
            "series": "",
            "seriesNumber": "",
            "volume": "",
            "numberOfVolumes": "",
            "edition": "",
            "place": "",
            "publisher": "",
            "date": "",
            "numPages": "2",
            "language": "",
            "ISBN": "",
            "shortTitle": "2011",
            "url": "",
            "accessDate": "",
            "archive": "",
            "archiveLocation": "",
            "libraryCatalog": "agricola.nal.usda.gov Library Catalog",
            "callNumber": "",
            "rights": "",
            "extra": "",
            "dateAdded": "2011-01-28T21:41:41Z",
            "dateModified": "2011-01-28T21:41:41Z",
            "tags": [
                {
                    "tag": "Internet resource",
                    "type": 1
                }
            ],
            "collections": [
                "BX9965IJ",
                "9KH9TNSJ"
            ],
            "relations": {
                "owl:sameAs": "http://zotero.org/groups/36222/items/927JGK4M"
            }
        }
    },
    {
        "key": "R39UWNFK",
        "version": 1,
        "library": {
            "type": "user",
            "id": 475425,
            "name": "Z public library",
            "links": {
                "alternate": {
                    "href": "https://www.zotero.org/z_public_library",
                    "type": "text/html"
                }
            }
        },
        "links": {
            "self": {
                "href": "https://api.zotero.org/users/475425/items/R39UWNFK",
                "type": "application/json"
            },
            "alternate": {
                "href": "https://www.zotero.org/z_public_library/items/R39UWNFK",
                "type": "text/html"
            }
        },
        "meta": {
            "creatorSummary": "Leveille et al.",
            "numChildren": 1
        },
        "data": {
            "key": "R39UWNFK",
            "version": 1,
            "itemType": "conferencePaper",
            "title": "Diagnostic of vacuum subsonic and supersonic plasma flows with enthalpy probe, schlieren and high speed camera methods",
            "creators": [
                {
                    "creatorType": "author",
                    "firstName": "V.",
                    "lastName": "Leveille"
                },
                {
                    "creatorType": "author",
                    "firstName": "M.I.",
                    "lastName": "Boulos"
                },
                {
                    "creatorType": "author",
                    "firstName": "D.",
                    "lastName": "Gravelle"
                }
            ],
            "abstractNote": "",
            "date": "",
            "proceedingsTitle": "IEEE Conference Record - Abstracts. 2002 IEEE International Conference on Plasma Science (Cat. No.02CH37340)",
            "conferenceName": "IEEE 29th International Conference on Plasma Sciences",
            "place": "Banff, Alta., Canada",
            "publisher": "",
            "volume": "",
            "pages": "286",
            "series": "",
            "language": "",
            "DOI": "10.1109/PLASMA.2002.1030588",
            "ISBN": "",
            "shortTitle": "",
            "url": "http://ieeexplore.ieee.org/Xplore/login.jsp?url=http%3A%2F%2Fieeexplore.ieee.org%2Fstamp%2Fstamp.jsp%3Ftp%3D%26arnumber%3D1030588&authDecision=-203",
            "accessDate": "2011-01-18T23:28:27Z",
            "archive": "",
            "archiveLocation": "",
            "libraryCatalog": "CrossRef",
            "callNumber": "",
            "rights": "",
            "extra": "",
            "dateAdded": "2011-01-18T23:28:27Z",
            "dateModified": "2011-01-18T23:28:27Z",
            "tags": [

            ],
            "collections": [
                "BX9965IJ",
                "9KH9TNSJ"
            ],
            "relations": {
                "owl:sameAs": [
                    "http://zotero.org/groups/36222/items/T3T7S2PD",
                    "http://zotero.org/groups/37668/items/TZFDTTH8"
                ]
            }
        }
    },
    {
        "key": "85MTWF4F",
        "version": 1,
        "library": {
            "type": "user",
            "id": 475425,
            "name": "Z public library",
            "links": {
                "alternate": {
                    "href": "https://www.zotero.org/z_public_library",
                    "type": "text/html"
                }
            }
        },
        "links": {
            "self": {
                "href": "https://api.zotero.org/users/475425/items/85MTWF4F",
                "type": "application/json"
            },
            "alternate": {
                "href": "https://www.zotero.org/z_public_library/items/85MTWF4F",
                "type": "text/html"
            }
        },
        "meta": {
            "creatorSummary": "Chung et al.",
            "parsedDate": "2007-00-06",
            "numChildren": 0
        },
        "data": {
            "key": "85MTWF4F",
            "version": 1,
            "itemType": "conferencePaper",
            "title": "Effects of Initial Plasma Properties on Plasma Recovery in Plasma Source Ion Implantation",
            "creators": [
                {
                    "creatorType": "author",
                    "firstName": "K. J.",
                    "lastName": "Chung"
                },
                {
                    "creatorType": "author",
                    "firstName": "S. W.",
                    "lastName": "Jung"
                },
                {
                    "creatorType": "author",
                    "firstName": "J. M.",
                    "lastName": "Choe"
                },
                {
                    "creatorType": "author",
                    "firstName": "G. H.",
                    "lastName": "Kim"
                },
                {
                    "creatorType": "author",
                    "firstName": "Y. S.",
                    "lastName": "Hwang"
                }
            ],
            "abstractNote": "",
            "date": "06/2007",
            "proceedingsTitle": "2007 IEEE Pulsed Power Plasma Science Conference",
            "conferenceName": "2007 IEEE Pulsed Power Plasma Science Conference",
            "place": "Albuquerque, NM, USA",
            "publisher": "",
            "volume": "",
            "pages": "569-569",
            "series": "",
            "language": "",
            "DOI": "10.1109/PPPS.2007.4345875",
            "ISBN": "",
            "shortTitle": "",
            "url": "http://ieeexplore.ieee.org/lpdocs/epic03/wrapper.htm?arnumber=4345875",
            "accessDate": "2011-01-18T23:28:14Z",
            "archive": "",
            "archiveLocation": "",
            "libraryCatalog": "CrossRef",
            "callNumber": "",
            "rights": "",
            "extra": "",
            "dateAdded": "2011-01-18T23:28:14Z",
            "dateModified": "2011-01-18T23:28:14Z",
            "tags": [

            ],
            "collections": [
                "BX9965IJ",
                "9KH9TNSJ"
            ],
            "relations": {
                "owl:sameAs": "http://zotero.org/groups/36222/items/DUPUCG6A"
            }
        }
    },
    {
        "key": "3EWF3P9V",
        "version": 1,
        "library": {
            "type": "user",
            "id": 475425,
            "name": "Z public library",
            "links": {
                "alternate": {
                    "href": "https://www.zotero.org/z_public_library",
                    "type": "text/html"
                }
            }
        },
        "links": {
            "self": {
                "href": "https://api.zotero.org/users/475425/items/3EWF3P9V",
                "type": "application/json"
            },
            "alternate": {
                "href": "https://www.zotero.org/z_public_library/items/3EWF3P9V",
                "type": "text/html"
            }
        },
        "meta": {
            "creatorSummary": "Asero and Antonicelli",
            "parsedDate": "2011-00-00",
            "numChildren": 1
        },
        "data": {
            "key": "3EWF3P9V",
            "version": 1,
            "itemType": "journalArticle",
            "title": "Does sensitization to foods in adults occur always in the gut?",
            "creators": [
                {
                    "creatorType": "author",
                    "firstName": "Riccardo",
                    "lastName": "Asero"
                },
                {
                    "creatorType": "author",
                    "firstName": "Leonardo",
                    "lastName": "Antonicelli"
                }
            ],
            "abstractNote": "It is widely accepted that, under normal conditions, the contact between allergens and the immune system via the gut results in immune tolerance. Thus, it is rather surprising that normal adults may become sensitized to foods that they have consumed a number of times without any consequence. However, the medical literature is crowded with reports suggesting that sensitization to food allergens may occur outside the intestinal tract in many instances. The present article reviews and discusses current data suggesting, either directly or indirectly, a possible initiation of food allergy in the respiratory tract or in the skin in the light of recent findings about mechanisms of tolerance and sensitization.",
            "publicationTitle": "International archives of allergy and immunology",
            "volume": "154",
            "issue": "1",
            "pages": "6-14",
            "date": "2011",
            "series": "",
            "seriesTitle": "",
            "seriesText": "",
            "journalAbbreviation": "Int Arch Allergy Immunol",
            "language": "",
            "DOI": "",
            "ISSN": "14230097",
            "shortTitle": "",
            "url": "",
            "accessDate": "",
            "archive": "",
            "archiveLocation": "",
            "libraryCatalog": "BioInfoBank",
            "callNumber": "",
            "rights": "",
            "extra": "PMID: 20664272",
            "dateAdded": "2011-01-18T20:41:02Z",
            "dateModified": "2011-01-18T20:41:02Z",
            "tags": [
                {
                    "tag": "Adult",
                    "type": 1
                },
                {
                    "tag": "Allergens",
                    "type": 1
                },
                {
                    "tag": "Food Hypersensitivity",
                    "type": 1
                },
                {
                    "tag": "Gastrointestinal Tract",
                    "type": 1
                },
                {
                    "tag": "Humans",
                    "type": 1
                },
                {
                    "tag": "Immune Tolerance",
                    "type": 1
                },
                {
                    "tag": "Plants, Edible",
                    "type": 1
                },
                {
                    "tag": "Skin",
                    "type": 1
                }
            ],
            "collections": [
                "BX9965IJ",
                "9KH9TNSJ"
            ],
            "relations": {
                "owl:sameAs": "http://zotero.org/groups/36222/items/A28897IC"
            }
        }
    },
    {
        "key": "2SS8NXZI",
        "version": 1,
        "library": {
            "type": "user",
            "id": 475425,
            "name": "Z public library",
            "links": {
                "alternate": {
                    "href": "https://www.zotero.org/z_public_library",
                    "type": "text/html"
                }
            }
        },
        "links": {
            "self": {
                "href": "https://api.zotero.org/users/475425/items/2SS8NXZI",
                "type": "application/json"
            },
            "alternate": {
                "href": "https://www.zotero.org/z_public_library/items/2SS8NXZI",
                "type": "text/html"
            }
        },
        "meta": {
            "creatorSummary": "DeLyria",
            "parsedDate": "2010-00-00",
            "numChildren": 1
        },
        "data": {
            "key": "2SS8NXZI",
            "version": 1,
            "itemType": "manuscript",
            "title": "Acute Phase T Cell Help in Neutrophil-Mediated Clearance of Helicobacter Pylori",
            "creators": [
                {
                    "creatorType": "author",
                    "firstName": "Elizabeth S",
                    "lastName": "DeLyria"
                }
            ],
            "abstractNote": "",
            "manuscriptType": "",
            "place": "Cleveland, Ohio",
            "date": "2010",
            "numPages": "118",
            "language": "",
            "shortTitle": "",
            "url": "",
            "accessDate": "",
            "archive": "",
            "archiveLocation": "",
            "libraryCatalog": "catalog.case.edu Library Catalog",
            "callNumber": "Pathol",
            "rights": "",
            "extra": "",
            "dateAdded": "2011-01-14T18:46:27Z",
            "dateModified": "2011-01-14T18:46:27Z",
            "tags": [
                {
                    "tag": "Helicobacter pylori",
                    "type": 1
                },
                {
                    "tag": "T-Lymphocytes",
                    "type": 1
                }
            ],
            "collections": [
                "BX9965IJ",
                "9KH9TNSJ"
            ],
            "relations": {
                "owl:sameAs": "http://zotero.org/groups/36222/items/DTC7V4F3"
            }
        }
    },
    {
        "key": "AGTZDBRQ",
        "version": 1,
        "library": {
            "type": "user",
            "id": 475425,
            "name": "Z public library",
            "links": {
                "alternate": {
                    "href": "https://www.zotero.org/z_public_library",
                    "type": "text/html"
                }
            }
        },
        "links": {
            "self": {
                "href": "https://api.zotero.org/users/475425/items/AGTZDBRQ",
                "type": "application/json"
            },
            "alternate": {
                "href": "https://www.zotero.org/z_public_library/items/AGTZDBRQ",
                "type": "text/html"
            }
        },
        "meta": {
            "creatorSummary": "Andrieu et al.",
            "parsedDate": "1995-00-00",
            "numChildren": 0
        },
        "data": {
            "key": "AGTZDBRQ",
            "version": 1,
            "itemType": "book",
            "title": "Cell Activation and Apoptosis in HIV Infection: Implications for Pathogenesis and Therapy",
            "creators": [
                {
                    "creatorType": "contributor",
                    "firstName": "Jean-Marie",
                    "lastName": "Andrieu"
                },
                {
                    "creatorType": "contributor",
                    "firstName": "Wei",
                    "lastName": "Lu"
                },
                {
                    "creatorType": "contributor",
                    "name": "International Symposium on Cellular Approaches to the Control of HIV Disease"
                }
            ],
            "abstractNote": "",
            "series": "Advances in experimental medicine and biology",
            "seriesNumber": "v. 374",
            "volume": "",
            "numberOfVolumes": "",
            "edition": "",
            "place": "New York",
            "publisher": "Plenum Press",
            "date": "1995",
            "numPages": "245",
            "language": "",
            "ISBN": "0306450631",
            "shortTitle": "Cell Activation and Apoptosis in HIV Infection",
            "url": "",
            "accessDate": "",
            "archive": "",
            "archiveLocation": "",
            "libraryCatalog": "cat.cisti-icist.nrc-cnrc.gc.ca Library Catalog",
            "callNumber": "R850.A1 A24 v. 374",
            "rights": "",
            "extra": "",
            "dateAdded": "2011-01-14T18:45:08Z",
            "dateModified": "2011-01-14T18:45:08Z",
            "tags": [
                {
                    "tag": "Apoptosis",
                    "type": 1
                },
                {
                    "tag": "Congresses",
                    "type": 1
                },
                {
                    "tag": "HIV infections",
                    "type": 1
                },
                {
                    "tag": "Lymphocyte transformation",
                    "type": 1
                },
                {
                    "tag": "Pathophysiology",
                    "type": 1
                },
                {
                    "tag": "T-Lymphocytes",
                    "type": 1
                },
                {
                    "tag": "immunology",
                    "type": 1
                },
                {
                    "tag": "therapy",
                    "type": 1
                }
            ],
            "collections": [
                "BX9965IJ",
                "9KH9TNSJ"
            ],
            "relations": {
                "owl:sameAs": "http://zotero.org/groups/36222/items/7QWZUET3"
            }
        }
    },
    {
        "key": "9AIAUW49",
        "version": 1,
        "library": {
            "type": "user",
            "id": 475425,
            "name": "Z public library",
            "links": {
                "alternate": {
                    "href": "https://www.zotero.org/z_public_library",
                    "type": "text/html"
                }
            }
        },
        "links": {
            "self": {
                "href": "https://api.zotero.org/users/475425/items/9AIAUW49",
                "type": "application/json"
            },
            "alternate": {
                "href": "https://www.zotero.org/z_public_library/items/9AIAUW49",
                "type": "text/html"
            }
        },
        "meta": {
            "creatorSummary": "Zolman",
            "parsedDate": "1993-00-00",
            "numChildren": 0
        },
        "data": {
            "key": "9AIAUW49",
            "version": 1,
            "itemType": "book",
            "title": "Biostatistics: Experimental Design and Statistical Inference",
            "creators": [
                {
                    "creatorType": "author",
                    "firstName": "James F",
                    "lastName": "Zolman"
                }
            ],
            "abstractNote": "",
            "series": "",
            "seriesNumber": "",
            "volume": "",
            "numberOfVolumes": "",
            "edition": "",
            "place": "New York",
            "publisher": "Oxford University Press",
            "date": "1993",
            "numPages": "343",
            "language": "",
            "ISBN": "0195078101",
            "shortTitle": "Biostatistics",
            "url": "",
            "accessDate": "",
            "archive": "",
            "archiveLocation": "",
            "libraryCatalog": "cat.cisti-icist.nrc-cnrc.gc.ca Library Catalog",
            "callNumber": "QH323.5 Z86",
            "rights": "",
            "extra": "",
            "dateAdded": "2011-01-13T03:38:12Z",
            "dateModified": "2011-01-13T03:38:12Z",
            "tags": [
                {
                    "tag": "Biometry",
                    "type": 1
                },
                {
                    "tag": "Experimental design",
                    "type": 1
                }
            ],
            "collections": [
                "BX9965IJ",
                "9KH9TNSJ"
            ],
            "relations": {
                "owl:sameAs": "http://zotero.org/groups/36222/items/FK9IWEBD"
            }
        }
    },
    {
        "key": "X42A7DEE",
        "version": 1,
        "library": {
            "type": "user",
            "id": 475425,
            "name": "Z public library",
            "links": {
                "alternate": {
                    "href": "https://www.zotero.org/z_public_library",
                    "type": "text/html"
                }
            }
        },
        "links": {
            "self": {
                "href": "https://api.zotero.org/users/475425/items/X42A7DEE",
                "type": "application/json"
            },
            "alternate": {
                "href": "https://www.zotero.org/z_public_library/items/X42A7DEE",
                "type": "text/html"
            }
        },
        "meta": {
            "creatorSummary": "Institute of Physics (Great Britain)",
            "parsedDate": "1993-00-00",
            "numChildren": 0
        },
        "data": {
            "key": "X42A7DEE",
            "version": 1,
            "itemType": "book",
            "title": "Electron Microscopy and Analysis 1993: Proceedings of the Institute of Physics Electron Microscopy and Analysis Group Conference, University of Liverpool, 14-17 September1993",
            "creators": [
                {
                    "creatorType": "author",
                    "name": "Institute of Physics (Great Britain)"
                },
                {
                    "creatorType": "contributor",
                    "firstName": "A. J",
                    "lastName": "Craven"
                },
                {
                    "creatorType": "contributor",
                    "name": "Institute of Physics (Great Britain)"
                },
                {
                    "creatorType": "contributor",
                    "name": "Institute of Physics (Great Britain)"
                },
                {
                    "creatorType": "contributor",
                    "name": "Institute of Materials (Great Britain)"
                },
                {
                    "creatorType": "contributor",
                    "name": "Royal Microscopical Society (Great Britain)"
                },
                {
                    "creatorType": "contributor",
                    "name": "University of Liverpool"
                }
            ],
            "abstractNote": "",
            "series": "Institute of Physics conference series",
            "seriesNumber": "no. 138",
            "volume": "",
            "numberOfVolumes": "",
            "edition": "",
            "place": "Bristol, UK",
            "publisher": "Institute of Physics Pub",
            "date": "1993",
            "numPages": "546",
            "language": "",
            "ISBN": "0750303212",
            "shortTitle": "Electron Microscopy and Analysis 1993",
            "url": "",
            "accessDate": "",
            "archive": "",
            "archiveLocation": "",
            "libraryCatalog": "cat.cisti-icist.nrc-cnrc.gc.ca Library Catalog",
            "callNumber": "QC1 I584 v. 138",
            "rights": "",
            "extra": "",
            "dateAdded": "2011-01-13T03:37:29Z",
            "dateModified": "2011-01-13T03:37:29Z",
            "tags": [
                {
                    "tag": "Analysis",
                    "type": 1
                },
                {
                    "tag": "Congresses",
                    "type": 1
                },
                {
                    "tag": "Electron microscopy",
                    "type": 1
                },
                {
                    "tag": "Materials",
                    "type": 1
                },
                {
                    "tag": "Microscopy",
                    "type": 1
                }
            ],
            "collections": [
                "BX9965IJ",
                "9KH9TNSJ"
            ],
            "relations": {
                "owl:sameAs": "http://zotero.org/groups/36222/items/E6IGUT5Z"
            }
        }
    },
    {
        "key": "33TK9NH9",
        "version": 1,
        "library": {
            "type": "user",
            "id": 475425,
            "name": "Z public library",
            "links": {
                "alternate": {
                    "href": "https://www.zotero.org/z_public_library",
                    "type": "text/html"
                }
            }
        },
        "links": {
            "self": {
                "href": "https://api.zotero.org/users/475425/items/33TK9NH9",
                "type": "application/json"
            },
            "alternate": {
                "href": "https://www.zotero.org/z_public_library/items/33TK9NH9",
                "type": "text/html"
            }
        },
        "meta": {
            "creatorSummary": "Lima et al.",
            "parsedDate": "2011-01-07",
            "numChildren": 1
        },
        "data": {
            "key": "33TK9NH9",
            "version": 1,
            "itemType": "journalArticle",
            "title": "Biscrolling Nanotube Sheets and Functional Guests into Yarns",
            "creators": [
                {
                    "creatorType": "author",
                    "firstName": "Márcio D.",
                    "lastName": "Lima"
                },
                {
                    "creatorType": "author",
                    "firstName": "Shaoli",
                    "lastName": "Fang"
                },
                {
                    "creatorType": "author",
                    "firstName": "Xavier",
                    "lastName": "Lepró"
                },
                {
                    "creatorType": "author",
                    "firstName": "Chihye",
                    "lastName": "Lewis"
                },
                {
                    "creatorType": "author",
                    "firstName": "Raquel",
                    "lastName": "Ovalle-Robles"
                },
                {
                    "creatorType": "author",
                    "firstName": "Javier",
                    "lastName": "Carretero-González"
                },
                {
                    "creatorType": "author",
                    "firstName": "Elizabeth",
                    "lastName": "Castillo-Martínez"
                },
                {
                    "creatorType": "author",
                    "firstName": "Mikhail E.",
                    "lastName": "Kozlov"
                },
                {
                    "creatorType": "author",
                    "firstName": "Jiyoung",
                    "lastName": "Oh"
                },
                {
                    "creatorType": "author",
                    "firstName": "Neema",
                    "lastName": "Rawat"
                },
                {
                    "creatorType": "author",
                    "firstName": "Carter S.",
                    "lastName": "Haines"
                },
                {
                    "creatorType": "author",
                    "firstName": "Mohammad H.",
                    "lastName": "Haque"
                },
                {
                    "creatorType": "author",
                    "firstName": "Vaishnavi",
                    "lastName": "Aare"
                },
                {
                    "creatorType": "author",
                    "firstName": "Stephanie",
                    "lastName": "Stoughton"
                },
                {
                    "creatorType": "author",
                    "firstName": "Anvar A.",
                    "lastName": "Zakhidov"
                },
                {
                    "creatorType": "author",
                    "firstName": "Ray H.",
                    "lastName": "Baughman"
                }
            ],
            "abstractNote": "Multifunctional applications of textiles have been limited by the inability to spin important materials into yarns. Generically applicable methods are demonstrated for producing weavable yarns comprising up to 95 weight percent of otherwise unspinnable particulate or nanofiber powders that remain highly functional. Scrolled 50-nanometer-thick carbon nanotube sheets confine these powders in the galleries of irregular scroll sacks whose observed complex structures are related to twist-dependent extension of Archimedean spirals, Fermat spirals, or spiral pairs into scrolls. The strength and electronic connectivity of a small weight fraction of scrolled carbon nanotube sheet enables yarn weaving, sewing, knotting, braiding, and charge collection. This technology is used to make yarns of superconductors, lithium-ion battery materials, graphene ribbons, catalytic nanofibers for fuel cells, and titanium dioxide for photocatalysis.",
            "publicationTitle": "Science",
            "volume": "331",
            "issue": "6013",
            "pages": "51 -55",
            "date": "January 07 , 2011",
            "series": "",
            "seriesTitle": "",
            "seriesText": "",
            "journalAbbreviation": "",
            "language": "",
            "DOI": "10.1126/science.1195912",
            "ISSN": "",
            "shortTitle": "",
            "url": "http://www.sciencemag.org/content/331/6013/51.abstract",
            "accessDate": "2011-01-13T02:50:48Z",
            "archive": "",
            "archiveLocation": "",
            "libraryCatalog": "Highwire 2.0",
            "callNumber": "",
            "rights": "",
            "extra": "",
            "dateAdded": "2011-01-13T02:50:48Z",
            "dateModified": "2011-01-13T02:50:48Z",
            "tags": [

            ],
            "collections": [
                "BX9965IJ",
                "9KH9TNSJ"
            ],
            "relations": {
                "owl:sameAs": "http://zotero.org/groups/36222/items/DNDBRG8U"
            }
        }
    },
    {
        "key": "U52JBZ4X",
        "version": 1,
        "library": {
            "type": "user",
            "id": 475425,
            "name": "Z public library",
            "links": {
                "alternate": {
                    "href": "https://www.zotero.org/z_public_library",
                    "type": "text/html"
                }
            }
        },
        "links": {
            "self": {
                "href": "https://api.zotero.org/users/475425/items/U52JBZ4X",
                "type": "application/json"
            },
            "alternate": {
                "href": "https://www.zotero.org/z_public_library/items/U52JBZ4X",
                "type": "text/html"
            }
        },
        "meta": {
            "parsedDate": "2004-12-01",
            "numChildren": 0
        },
        "data": {
            "key": "U52JBZ4X",
            "version": 1,
            "itemType": "journalArticle",
            "title": "Front Matter",
            "creators": [

            ],
            "abstractNote": "",
            "publicationTitle": "Crustaceana",
            "volume": "77",
            "issue": "11",
            "pages": "",
            "date": "December 01, 2004",
            "series": "",
            "seriesTitle": "",
            "seriesText": "",
            "journalAbbreviation": "",
            "language": "",
            "DOI": "",
            "ISSN": "0011216X",
            "shortTitle": "",
            "url": "http://www.jstor.org/stable/20107443",
            "accessDate": "2011-01-13T02:32:38Z",
            "archive": "",
            "archiveLocation": "",
            "libraryCatalog": "JSTOR",
            "callNumber": "",
            "rights": "",
            "extra": "ArticleType: misc / Full publication date: Dec., 2004 / Copyright © 2004 BRILL",
            "dateAdded": "2011-01-13T02:32:38Z",
            "dateModified": "2011-01-13T02:32:38Z",
            "tags": [

            ],
            "collections": [
                "BX9965IJ",
                "9KH9TNSJ"
            ],
            "relations": {
                "owl:sameAs": "http://zotero.org/groups/36222/items/CSDUTFSZ"
            }
        }
    }
]"""
        self.items_doc = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom" xmlns:zapi="http://zotero.org/ns/api">
          <title>Zotero / urschrei / Items</title>
          <id>http://zotero.org/users/436/items?limit=3&amp;content=json</id>
          <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/items?limit=1&amp;content=json"/>
          <link rel="first" type="application/atom+xml" href="https://api.zotero.org/users/436/items?limit=1&amp;content=json"/>
          <link rel="next" type="application/atom+xml" href="https://api.zotero.org/users/436/items?limit=1&amp;content=json&amp;start=3"/>
          <link rel="last" type="application/atom+xml" href="https://api.zotero.org/users/436/items?limit=1&amp;content=json&amp;start=1086"/>
          <link rel="alternate" type="text/html" href="http://zotero.org/users/436/items?limit=1"/>
          <zapi:totalResults>1087</zapi:totalResults>
          <zapi:apiVersion>1</zapi:apiVersion>
          <updated>2011-05-28T11:07:58Z</updated>
          <entry>
            <title>Copyright in custom code: Who owns commissioned software?</title>
            <author>
              <name>urschrei</name>
              <uri>http://zotero.org/urschrei</uri>
            </author>
            <id>http://zotero.org/urschrei/items/T4AH4RZA</id>
            <published>2011-02-14T00:27:03Z</published>
            <updated>2011-02-14T00:27:03Z</updated>
            <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/items/T4AH4RZA?content=json"/>
            <link rel="alternate" type="text/html" href="http://zotero.org/urschrei/items/T4AH4RZA"/>
            <zapi:key>T4AH4RZA</zapi:key>
            <zapi:itemType>journalArticle</zapi:itemType>
            <zapi:creatorSummary>McIntyre</zapi:creatorSummary>
            <zapi:numChildren>1</zapi:numChildren>
            <zapi:numTags>0</zapi:numTags>
            <content type="application/json" zapi:etag="7252daf2495feb8ec89c61f391bcba24">{"itemType":"journalArticle","title":"Copyright in custom code: Who owns commissioned software?","creators":[{"creatorType":"author","firstName":"T. J.","lastName":"McIntyre"}],"abstractNote":"","publicationTitle":"Journal of Intellectual Property Law \u0026 Practice","volume":"","issue":"","pages":"","date":"2007","series":"","seriesTitle":"","seriesText":"","journalAbbreviation":"","language":"","DOI":"","ISSN":"1747-1532","shortTitle":"Copyright in custom code","url":"","accessDate":"","archive":"","archiveLocation":"","libraryCatalog":"Google Scholar","callNumber":"","rights":"","extra":"","tags":[]}</content>
          </entry>
        </feed>"""
        self.citation_doc = """<?xml version="1.0" encoding="UTF-8"?>
            <entry xmlns="http://www.w3.org/2005/Atom" xmlns:zapi="http://zotero.org/ns/api">
            <title>The power broker : Robert Moses and the fall of New York</title>
            <author><name>urschrei</name><uri>http://zotero.org/urschrei</uri></author>
            <id>http://zotero.org/urschrei/items/GW8V2CK7</id>
            <published>2014-02-12T16:16:22Z</published>
            <updated>2014-03-06T20:25:20Z</updated>
            <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/items/GW8V2CK7?content=citation"/>
            <link rel="alternate" type="text/html" href="http://zotero.org/urschrei/items/GW8V2CK7"/>
            <zapi:key>GW8V2CK7</zapi:key>
            <zapi:version>764</zapi:version>
            <zapi:itemType>document</zapi:itemType>
            <zapi:creatorSummary>Robert \xc3\x84. Caro</zapi:creatorSummary>
            <zapi:year>1974</zapi:year>
            <zapi:numChildren>0</zapi:numChildren>
            <zapi:numTags>0</zapi:numTags>
            <content zapi:type="citation" type="xhtml">
                <span xmlns="http://www.w3.org/1999/xhtml">(Robert \xc3\x84. Caro 1974)</span>
            </content>
            </entry>"""
        self.biblio_doc = """<?xml version="1.0" encoding="UTF-8"?>
            <entry xmlns="http://www.w3.org/2005/Atom" xmlns:zapi="http://zotero.org/ns/api">
                <title>The power broker : Robert Moses and the fall of New York</title>
                <author>
                <name>urschrei</name>
                <uri>http://zotero.org/urschrei</uri>
                </author>
                <id>http://zotero.org/urschrei/items/GW8V2CK7</id>
                <published>2014-02-12T16:16:22Z</published>
                <updated>2014-02-12T16:16:22Z</updated>
                <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/items/GW8V2CK7?content=bib"/>
                <link rel="alternate" type="text/html" href="http://zotero.org/urschrei/items/GW8V2CK7"/>
                <zapi:key>GW8V2CK7</zapi:key>
                <zapi:version>739</zapi:version>
                <zapi:itemType>document</zapi:itemType>
                <zapi:creatorSummary>Robert A. Caro</zapi:creatorSummary>
                <zapi:year>1974</zapi:year>
                <zapi:numChildren>0</zapi:numChildren>
                <zapi:numTags>0</zapi:numTags>
                <content zapi:type="bib" type="xhtml">
                <div xmlns="http://www.w3.org/1999/xhtml" class="csl-bib-body" style="line-height: 1.35; padding-left: 2em; text-indent:-2em;">
            <div class="csl-entry">Robert Ä. Caro. 1974. “The Power Broker : Robert Moses and the Fall of New York.”</div>
            </div>
              </content>
            </entry>"""
        self.attachments_doc = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom" xmlns:zapi="http://zotero.org/ns/api">
          <title>Zotero / urschrei / Items</title>
          <id>http://zotero.org/users/436/items?limit=1&amp;content=json</id>
          <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/items?limit=1&amp;content=json"/>
          <link rel="first" type="application/atom+xml" href="https://api.zotero.org/users/436/items?limit=1&amp;content=json"/>
          <link rel="next" type="application/atom+xml" href="https://api.zotero.org/users/436/items?limit=1&amp;content=json&amp;start=1"/>
          <link rel="last" type="application/atom+xml" href="https://api.zotero.org/users/436/items?limit=1&amp;content=json&amp;start=1128"/>
          <link rel="alternate" type="text/html" href="http://zotero.org/users/436/items?limit=1"/>
          <zapi:totalResults>1129</zapi:totalResults>
          <zapi:apiVersion>1</zapi:apiVersion>
          <updated>2012-01-11T19:54:47Z</updated>
          <entry>
            <title>1641 Depositions</title>
            <author>
              <name>urschrei</name>
              <uri>http://zotero.org/urschrei</uri>
            </author>
            <id>http://zotero.org/urschrei/items/TM8QRS36</id>
            <published>2012-01-11T19:54:47Z</published>
            <updated>2012-01-11T19:54:47Z</updated>
            <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/items/TM8QRS36?content=json"/>
            <link rel="up" type="application/atom+xml" href="https://api.zotero.org/users/436/items/47RUN6RI?content=json"/>
            <link rel="alternate" type="text/html" href="http://zotero.org/urschrei/items/TM8QRS36"/>
            <zapi:key>TM8QRS36</zapi:key>
            <zapi:itemType>attachment</zapi:itemType>
            <zapi:numTags>0</zapi:numTags>
            <content zapi:type="json" zapi:etag="1686f563f9b4cb1db3a745a920bf0afa">{"itemType":"attachment","title":"1641 Depositions","accessDate":"2012-01-11 19:54:47","url":"http://1641.tcd.ie/project-conservation.php","note":"","linkMode":1,"mimeType":"text/html","charset":"utf-8","tags":[]}</content>
          </entry>
        </feed>"""
        self.collections_doc = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom" xmlns:zapi="http://zotero.org/ns/api">
          <title>Zotero / urschrei / Collections</title>
          <id>http://zotero.org/users/436/collections?limit=1&amp;content=json</id>
          <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/collections?limit=1&amp;content=json"/>
          <link rel="first" type="application/atom+xml" href="https://api.zotero.org/users/436/collections?limit=1&amp;content=json"/>
          <link rel="next" type="application/atom+xml" href="https://api.zotero.org/users/436/collections?limit=1&amp;content=json&amp;start=1"/>
          <link rel="last" type="application/atom+xml" href="https://api.zotero.org/users/436/collections?limit=1&amp;content=json&amp;start=37"/>
          <link rel="alternate" type="text/html" href="http://zotero.org/users/436/collections?limit=1"/>
          <zapi:totalResults>38</zapi:totalResults>
          <zapi:apiVersion>1</zapi:apiVersion>
          <updated>2011-03-16T15:00:09Z</updated>
          <entry>
            <title>Badiou</title>
            <author>
              <name>urschrei</name>
              <uri>http://zotero.org/urschrei</uri>
            </author>
            <id>http://zotero.org/urschrei/collections/HTUHVPE5</id>
            <published>2011-03-16T14:48:18Z</published>
            <updated>2011-03-16T15:00:09Z</updated>
            <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/collections/HTUHVPE5"/>
            <link rel="alternate" type="text/html" href="http://zotero.org/urschrei/collections/HTUHVPE5"/>
            <zapi:key>HTUHVPE5</zapi:key>
            <zapi:numCollections>0</zapi:numCollections>
            <zapi:numItems>27</zapi:numItems>
            <content type="application/json" zapi:etag="7252daf2495feb8ec89c61f391bcba24">{"name":"A Midsummer Night's Dream","parent":false}</content>
          </entry>
        </feed>"""
        self.tags_doc = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom" xmlns:zapi="http://zotero.org/ns/api">
          <title>Zotero / urschrei / Tags</title>
          <id>http://zotero.org/users/436/tags?limit=1&amp;content=json</id>
          <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/tags?limit=1&amp;content=json"/>
          <link rel="first" type="application/atom+xml" href="https://api.zotero.org/users/436/tags?limit=1&amp;content=json"/>
          <link rel="next" type="application/atom+xml" href="https://api.zotero.org/users/436/tags?limit=1&amp;content=json&amp;start=1"/>
          <link rel="last" type="application/atom+xml" href="https://api.zotero.org/users/436/tags?limit=1&amp;content=json&amp;start=319"/>
          <link rel="alternate" type="text/html" href="http://zotero.org/users/436/tags?limit=1"/>
          <zapi:totalResults>320</zapi:totalResults>
          <zapi:apiVersion>1</zapi:apiVersion>
          <updated>2010-03-27T13:56:08Z</updated>
          <entry xmlns:zxfer="http://zotero.org/ns/transfer">
            <title>Authority in literature</title>
            <author>
              <name>urschrei</name>
              <uri>http://zotero.org/urschrei</uri>
            </author>
            <id>http://zotero.org/urschrei/tags/Authority+in+literature</id>
            <published>2010-03-26T18:23:14Z</published>
            <updated>2010-03-27T13:56:08Z</updated>
            <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/tags/Authority+in+literature"/>
            <link rel="alternate" type="text/html" href="http://zotero.org/urschrei/tags/Authority+in+literature"/>
            <zapi:numItems>1</zapi:numItems>
          </entry>
        </feed>"""
        self.groups_doc = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom" xmlns:zapi="http://zotero.org/ns/api">
          <title>urschrei&#x2019;s Groups</title>
          <id>http://zotero.org/users/436/groups?limit=1&amp;content=json</id>
          <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/groups?limit=1&amp;content=json"/>
          <link rel="first" type="application/atom+xml" href="https://api.zotero.org/users/436/groups?limit=1&amp;content=json"/>
          <link rel="next" type="application/atom+xml" href="https://api.zotero.org/users/436/groups?limit=1&amp;content=json&amp;start=1"/>
          <link rel="last" type="application/atom+xml" href="https://api.zotero.org/users/436/groups?limit=1&amp;content=json&amp;start=1"/>
          <link rel="alternate" type="text/html" href="http://zotero.org/users/436/groups?limit=1"/>
          <zapi:totalResults>2</zapi:totalResults>
          <zapi:apiVersion>1</zapi:apiVersion>
          <updated>2010-07-04T21:56:22Z</updated>
          <entry xmlns:zxfer="http://zotero.org/ns/transfer">
            <title>DFW</title>
            <author>
              <name>urschrei</name>
              <uri>http://zotero.org/urschrei</uri>
            </author>
            <id>http://zotero.org/groups/dfw</id>
            <published>2010-01-20T12:31:26Z</published>
            <updated>2010-07-04T21:56:22Z</updated>
            <link rel="self" type="application/atom+xml" href="https://api.zotero.org/groups/10248?content=json"/>
            <link rel="alternate" type="text/html" href="http://zotero.org/groups/dfw"/>
            <zapi:numItems>468</zapi:numItems>
            <content type="application/json">{"name":"DFW","owner":436,"type":"PublicOpen","description":"%3Cp%3EA+grouped+collection+of+the+David+Foster+Wallace+bibliography%2C+adapted%2Fedited%2Fupdated+from+what%27s+available+elsewhere.%3C%2Fp%3E","url":"","hasImage":1,"libraryEnabled":1,"libraryEditing":"admins","libraryReading":"all","fileEditing":"none","members":{"2":539271}}</content>
          </entry>
        </feed>"""
        self.bib_doc = """<?xml version="1.0"?>
         <feed xmlns="http://www.w3.org/2005/Atom" xmlns:zapi="http://zotero.org/ns/api">
           <title>Zotero / urschrei / Top-Level Items</title>
           <id>http://zotero.org/users/436/items/top?limit=1&amp;content=bib</id>
           <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/items/top?limit=1&amp;content=bib"/>
           <link rel="first" type="application/atom+xml" href="https://api.zotero.org/users/436/items/top?limit=1&amp;content=bib"/>
           <link rel="next" type="application/atom+xml" href="https://api.zotero.org/users/436/items/top?limit=1&amp;content=bib&amp;start=1"/>
           <link rel="last" type="application/atom+xml" href="https://api.zotero.org/users/436/items/top?limit=1&amp;content=bib&amp;start=949"/>
           <link rel="alternate" type="text/html" href="http://zotero.org/users/436/items/top?limit=1"/>
           <zapi:totalResults>950</zapi:totalResults>
           <zapi:apiVersion>1</zapi:apiVersion>
           <updated>2011-02-14T00:27:03Z</updated>
           <entry>
             <title>Copyright in custom code: Who owns commissioned software?</title>
             <author>
               <name>urschrei</name>
               <uri>http://zotero.org/urschrei</uri>
             </author>
             <id>http://zotero.org/urschrei/items/T4AH4RZA</id>
             <published>2011-02-14T00:27:03Z</published>
             <updated>2011-02-14T00:27:03Z</updated>
             <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/items/T4AH4RZA?content=bib"/>
             <link rel="alternate" type="text/html" href="http://zotero.org/urschrei/items/T4AH4RZA"/>
             <zapi:key>T4AH4RZA</zapi:key>
             <zapi:itemType>journalArticle</zapi:itemType>
             <zapi:creatorSummary>McIntyre</zapi:creatorSummary>
             <zapi:numChildren>1</zapi:numChildren>
             <zapi:numTags>0</zapi:numTags>
             <content type="xhtml" zapi:etag="7252daf2495feb8ec89c61f391bcba24">
               <div xmlns="http://www.w3.org/1999/xhtml" class="csl-bib-body" style="line-height: 1.35; padding-left: 2em; text-indent:-2em;">
           <div class="csl-entry">McIntyre, T. J. &#x201C;Copyright in custom code: Who owns commissioned software?&#x201D; <i>Journal of Intellectual Property Law &amp; Practice</i> (2007).</div>
         </div>
             </content>
           </entry>
         </feed>"""
        self.created_response = """<?xml version="1.0"?>
        <entry xmlns="http://www.w3.org/2005/Atom" xmlns:zapi="http://zotero.org/ns/api">
          <title>Hell, I don't Know</title>
          <author>
            <name>urschrei</name>
            <uri>http://zotero.org/urschrei</uri>
          </author>
          <id>http://zotero.org/urschrei/items/NVGIBE59</id>
          <published>2011-12-14T19:24:20Z</published>
          <updated>2011-12-17T19:19:37Z</updated>
          <link rel="self" type="application/atom+xml" href="https://api.zotero.org/users/436/items/NVGIBE59?content=json"/>
          <link rel="alternate" type="text/html" href="http://zotero.org/urschrei/items/NVGIBE59"/>
          <zapi:key>NVGIBE59</zapi:key>
          <zapi:itemType>journalArticle</zapi:itemType>
          <zapi:creatorSummary>Salo</zapi:creatorSummary>
          <zapi:year/>
          <zapi:numChildren>1</zapi:numChildren>
          <zapi:numTags>0</zapi:numTags>
          <content type="application/json" zapi:etag="1ed002db69174ae2ae0e3b90499df15e">{"itemType":"journalArticle","title":"Hell, I don't Know","creators":[{"creatorType":"author","firstName":"Dorotea","lastName":"Salo"}],"abstractNote":"","publicationTitle":"","volume":"","issue":"","pages":"","date":"","series":"","seriesTitle":"","seriesText":"","journalAbbreviation":"","language":"","DOI":"","ISSN":"","shortTitle":"","url":"","accessDate":"","archive":"","archiveLocation":"","libraryCatalog":"","callNumber":"","rights":"","extra":"","tags":[]}</content>
        </entry>"""
        self.item_templt = """{
          "itemType" : "book",
          "title" : "",
          "creators" : [
            {
              "creatorType" : "author",
              "firstName" : "",
              "lastName" : ""
            }
          ],
          "url" : "",
          "tags" : [],
          "notes" : [],
          "etag" : ""
        }"""
        self.item_types = """[
        {
            "itemType":"artwork",
            "localized":"Artwork"
        },
        {
            "itemType":"audioRecording",
            "localized":"Audio Recording"
        },
        {
            "itemType":"bill",
            "localized":"Bill"
        },
        {
            "itemType":"blogPost",
            "localized":"Blog Post"
        },
        {
            "itemType":"book",
            "localized":"Book"
        },
        {
            "itemType":"bookSection",
            "localized":"Book Section"
        },
        {
            "itemType":"case",
            "localized":"Case"
        },
        {
            "itemType":"computerProgram",
            "localized":"Computer Program"
        },
        {
            "itemType":"conferencePaper",
            "localized":"Conference Paper"
        },
        {
            "itemType":"dictionaryEntry",
            "localized":"Dictionary Entry"
        },
        {
            "itemType":"document",
            "localized":"Document"
        },
        {
            "itemType":"email",
            "localized":"E-mail"
        },
        {
            "itemType":"encyclopediaArticle",
            "localized":"Encyclopedia Article"
        },
        {
            "itemType":"film",
            "localized":"Film"
        },
        {
            "itemType":"forumPost",
            "localized":"Forum Post"
        },
        {
            "itemType":"hearing",
            "localized":"Hearing"
        },
        {
            "itemType":"instantMessage",
            "localized":"Instant Message"
        },
        {
            "itemType":"interview",
            "localized":"Interview"
        },
        {
            "itemType":"journalArticle",
            "localized":"Journal Article"
        },
        {
            "itemType":"letter",
            "localized":"Letter"
        },
        {
            "itemType":"magazineArticle",
            "localized":"Magazine Article"
        },
        {
            "itemType":"manuscript",
            "localized":"Manuscript"
        },
        {
            "itemType":"map",
            "localized":"Map"
        },
        {
            "itemType":"newspaperArticle",
            "localized":"Newspaper Article"
        },
        {
            "itemType":"note",
            "localized":"Note"
        },
        {
            "itemType":"patent",
            "localized":"Patent"
        },
        {
            "itemType":"podcast",
            "localized":"Podcast"
        },
        {
            "itemType":"presentation",
            "localized":"Presentation"
        },
        {
            "itemType":"radioBroadcast",
            "localized":"Radio Broadcast"
        },
        {
            "itemType":"report",
            "localized":"Report"
        },
        {
            "itemType":"statute",
            "localized":"Statute"
        },
        {
            "itemType":"tvBroadcast",
            "localized":"TV Broadcast"
        },
        {
            "itemType":"thesis",
            "localized":"Thesis"
        },
        {
            "itemType":"videoRecording",
            "localized":"Video Recording"
        },
        {
            "itemType":"webpage",
            "localized":"Web Page"
        }
        ]"""
        self.keys_response = """ABCDE\nFGHIJ\nKLMNO\n"""
        # Add the item file to the mock response by default
        HTTPretty.enable()
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items?content=json&key=myuserkey',
            body=self.items_doc)

    @httprettified
    def testFailWithoutCredentials(self):
        """ Instance creation should fail, because we're leaving out a
            credential
        """
        with self.assertRaises(z.ze.MissingCredentials):
            zf = z.Zotero('myuserID')

    @httprettified
    def testRequestBuilder(self):
        """ Should add the user key, then url-encode all other added parameters
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        zot.add_parameters(limit=0, start=7)
        self.assertEqual('content=json&start=7&limit=0&key=myuserkey', zot.url_params)

    @httprettified
    def testBuildQuery(self):
        """ Check that spaces etc. are being correctly URL-encoded and added
            to the URL parameters
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        zot.add_parameters(start=10)
        query_string = '/users/{u}/tags/hi there/items'
        query = zot._build_query(query_string)
        self.assertEqual(
            '/users/myuserID/tags/hi%20there/items?content=json&start=10&key=myuserkey',
            query)

    @httprettified
    def testParseItemAtomDoc(self):
        """ Should successfully return a list of item dicts, key should match
            input doc's zapi:key value, and author should have been correctly
            parsed out of the XHTML payload
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items?content=json&key=myuserkey',
            body=self.items_doc)
        items_data = zot.items()
        self.assertEqual(u'T4AH4RZA', items_data[0]['key'])
        self.assertEqual(u'7252daf2495feb8ec89c61f391bcba24', items_data[0]['etag'])
        self.assertEqual(u'McIntyre', items_data[0]['creators'][0]['lastName'])
        self.assertEqual(u'journalArticle', items_data[0]['itemType'])
        test_dt = datetime.strptime(
            u'Mon, 14 Feb 2011 00:27:03 UTC',
            "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=pytz.timezone('GMT'))
        incoming_dt = datetime.strptime(
            items_data[0]['updated'],
            "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=pytz.timezone('GMT'))
        self.assertEqual(test_dt, incoming_dt)

    @httprettified
    def testParseAttachmentsAtomDoc(self):
        """ Ensure that attachments are being correctly parsed """
        zot = z.Zotero('myuserid', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserid/items?content=json&key=myuserkey',
            body=self.attachments_doc)
        attachments_data = zot.items()
        self.assertEqual(u'1641 Depositions', attachments_data[0]['title'])

    @httprettified
    def testParseKeysResponse(self):
        """ Check that parsing plain keys returned by format = keys works """
        zot = z.Zotero('myuserid', 'user', 'myuserkey')
        zot.url_params = 'format=keys'
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserid/items?format=keys',
            body=self.keys_response)
        response = zot.items()
        self.assertEqual('ABCDE\nFGHIJ\nKLMNO\n', response)

    @httprettified
    def testParseChildItems(self):
        """ Try and parse child items """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items/ABC123/children?content=json&key=myuserkey',
            body=self.items_doc)
        items_data = zot.children('ABC123')
        self.assertEqual(u'T4AH4RZA', items_data[0]['key'])

    @httprettified
    def testEncodings(self):
        """ Should be able to print unicode strings to stdout, and convert
            them to UTF-8 before printing them
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items?content=json&key=myuserkey',
            body=self.items_doc)
        items_data = zot.items()
        try:
            print(items_data[0]['title'])
        except UnicodeError:
            self.fail('Your Python install appears unable to print unicode')
        try:
            print(items_data[0]['title'].encode('utf-8'))
        except UnicodeError:
            self.fail(
                'Your Python install appears to dislike encoding unicode strings as UTF-8')

    @httprettified
    def testCitUTF8(self):
        """ ensure that unicode citations are correctly processed by Pyzotero
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items/GW8V2CK7?content=citation&style=chicago-author-date&key=myuserkey',
            body=self.citation_doc)
        cit = zot.item('GW8V2CK7', content='citation', style='chicago-author-date')
        self.assertEqual(cit[0], u'<span>(Robert Ä. Caro 1974)</span>')

    @httprettified
    def testParseItemAtomBibDoc(self):
        """ Should match a DIV with class = csl-entry
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        zot.url_params = 'content=bib'
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items?content=json&key=myuserkey',
            body=self.bib_doc)
        items_data = zot.items()
        dec = items_data[0]
        self.assertTrue(dec.startswith("""<div class="csl-entry">"""))

    @httprettified
    def testParseCollectionsAtomDoc(self):
        """ Should successfully return a list of collection dicts, key should
            match input doc's zapi:key value, and 'title' value should match
            input doc's title value
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/collections?content=json&key=myuserkey',
            body=self.collections_doc)
        collections_data = zot.collections()
        self.assertEqual(u'HTUHVPE5', collections_data[0]['key'])
        self.assertEqual(
            "A Midsummer Night's Dream",
            collections_data[0]['name'])

    @httprettified
    def testParseTagsAtomDoc(self):
        """ Should successfully return a list of tags
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/tags?content=json&key=myuserkey',
            body=self.tags_doc)
        # /users/myuserID/tags?content=json&key=myuserkey
        tags_data = zot.tags()
        self.assertEqual('Authority in literature', tags_data[0])

    @httprettified
    def testParseGroupsAtomDoc(self):
        """ Should successfully return a list of group dicts, ID should match
            input doc's zapi:key value, and 'total_items' value should match
            input doc's zapi:numItems value
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/groups?content=json&key=myuserkey',
            body=self.groups_doc)
        groups_data = zot.groups()
        self.assertEqual('DFW', groups_data[0]['name'])
        self.assertEqual('10248', groups_data[0]['group_id'])

    def testParamsReset(self):
        """ Should successfully reset URL parameters after a query string
            is built
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        zot.add_parameters(start=5, limit=10)
        zot._build_query('/whatever')
        zot.add_parameters(start=2)
        self.assertEqual('content=json&start=2&key=myuserkey', zot.url_params)

    @httprettified
    def testParamsBlankAfterCall(self):
        """ self.url_params should be blank after an API call
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items?content=json&key=myuserkey',
            body=self.items_doc)
        _ = zot.items()
        self.assertEqual(None, zot.url_params)

    @httprettified
    def testResponseForbidden(self):
        """ Ensure that an error is properly raised for 403
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items?content=json&key=myuserkey',
            body=self.items_doc,
            status=403)
        with self.assertRaises(z.ze.UserNotAuthorised):
            zot.items()

    @httprettified
    def testResponseUnsupported(self):
        """ Ensure that an error is properly raised for 400
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items?content=json&key=myuserkey',
            body=self.items_doc,
            status=400)
        with self.assertRaises(z.ze.UnsupportedParams):
            zot.items()

    @httprettified
    def testResponseNotFound(self):
        """ Ensure that an error is properly raised for 404
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items?content=json&key=myuserkey',
            body=self.items_doc,
            status=404)
        with self.assertRaises(z.ze.ResourceNotFound):
            zot.items()

    @httprettified
    def testResponseMiscError(self):
        """ Ensure that an error is properly raised for unspecified errors
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items?content=json&key=myuserkey',
            body=self.items_doc,
            status=500)
        with self.assertRaises(z.ze.HTTPError):
            zot.items()

    @httprettified
    def testGetItems(self):
        """ Ensure that we can retrieve a list of all items """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/itemTypes',
            body=self.item_types)
        t = zot.item_types()
        self.assertEqual(t[0]['itemType'], 'artwork')
        self.assertEqual(t[-1]['itemType'], 'webpage')

    @httprettified
    def testGetTemplate(self):
        """ Ensure that item templates are retrieved and converted into dicts
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/items/new?itemType=book',
            body=self.item_templt)
        t = zot.item_template('book')
        self.assertEqual('book', t['itemType'])

    def testCreateCollectionError(self):
        """ Ensure that collection creation fails with the wrong dict
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        t = {'foo': 'bar'}
        with self.assertRaises(z.ze.ParamNotPassed):
            t = zot.create_collection(t)

    @httprettified
    def testCreateItem(self):
        """ Ensure that items can be created
        """
        # first, retrieve an item template
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/items/new?itemType=book',
            body=self.item_templt)
        t = zot.item_template('book')
        # Update the item type
        t['itemType'] = 'journalArticle'
        # Add keys which should be removed before the data is sent
        t['key'] = 'KEYABC123'
        t['etag'] = 'TAGABC123'
        t['group_id'] = 'GROUPABC123'
        t['updated'] = '14 March, 2011'
        tn = dict(t)
        tn['key'] = 'KEYABC124'
        ls = []
        ls.append(t)
        ls.append(tn)
        # register a 403 response
        HTTPretty.register_uri(
            HTTPretty.POST,
            'https://api.zotero.org/users/myuserID/items?key=myuserkey',
            body=self.items_doc,
            status=403)
        with self.assertRaises(z.ze.UserNotAuthorised) as e:
            _ = zot.create_items(ls)
        exc = str(e.exception)
        # this test is a kludge; we're checking the POST data in the 403 response
        self.assertIn("journalArticle", exc)
        self.assertNotIn("KEYABC123", exc)
        self.assertNotIn("TAGABC123", exc)
        self.assertNotIn("GROUPABC123", exc)

    @httprettified
    def testUpdateItem(self):
        """ Test that we can update an item
            This test is a kludge; it only tests that the mechanism for
            internal key removal is OK, and that we haven't made any silly
            list/dict comprehension or genexpr errors
        """
        import json
        # first, retrieve an item
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://api.zotero.org/users/myuserID/items?content=json&key=myuserkey',
            body=self.items_doc)
        items_data = zot.items()
        items_data[0]['title'] = 'flibble'
        json.dumps(*zot._cleanup(items_data[0]))

    def testEtagsParsing(self):
        """ Tests item and item update response etag parsing
        """
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        self.assertEqual(z.etags(self.created_response), ['1ed002db69174ae2ae0e3b90499df15e'])
        self.assertEqual(
            z.etags(self.items_doc),
            ['7252daf2495feb8ec89c61f391bcba24'])

    def testTooManyItems(self):
        """ Should fail because we're passing too many items
        """
        itms = [i for i in xrange(51)]
        zot = z.Zotero('myuserID', 'user', 'myuserkey')
        with self.assertRaises(z.ze.TooManyItems):
            zot.create_items(itms)

    # @httprettified
    # def testRateLimit(self):
    #     """ Test 429 response handling (e.g. wait, wait a bit longer etc.)
    #     """
    #     zot = z.Zotero('myuserID', 'user', 'myuserkey')
    #     HTTPretty.register_uri(
    #         HTTPretty.GET,
    #         'https://api.zotero.org/users/myuserID/items?content=json&key=myuserkey',
    #         responses=[
    #             HTTPretty.Response(body=self.items_doc, status=429),
    #             HTTPretty.Response(body=self.items_doc, status=429),
    #             HTTPretty.Response(body=self.items_doc, status=200)])
    #     zot.items()
    #     with self.assertEqual(z.backoff.delay, 8):
    #         zot.items()

    def tearDown(self):
        """ Tear stuff down
        """
        HTTPretty.disable()


if __name__ == "__main__":
    unittest.main()
