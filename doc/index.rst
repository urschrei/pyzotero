Description
===========
Pyzotero is a Python wrapper for the `Zotero API (v3) <https://www.zotero.org/support/dev/web_api/v3/start>`_.


.. Pyzotero documentation master file, created by
   sphinx-quickstart on Mon Jul  4 19:39:03 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. py:module:: zotero



Getting started (short version)
===============================
1. In a shell / prompt: ``pip install pyzotero`` or ``conda config --add channels conda-forge && conda install pyzotero``
2. You'll need the ID of the personal or group library you want to access:

  * Your **personal library ID** is available `here <https://www.zotero.org/settings/keys>`_, in the section ``Your userID for use in API calls``
  * For **group libraries**, the ID can be found by opening the group's page: ``https://www.zotero.org/groups/groupname``, and hovering over the ``group settings`` link. The ID is the integer after ``/groups/``

3. You'll also need [*]_ to get an **API key** from the Zotero `site <https://www.zotero.org/settings/keys/new>`_
4. Are you accessing your own Zotero library? Set``library_type`` to ``'user'``
5. Are you accessing a shared group library? Set``library_type`` to ``'group'``
6. **Read-only** access to your local Zotero library is available: set ``local=True``


.. _hello-world:

    .. code-block:: python
        :emphasize-lines: 1,2,3

            from pyzotero import zotero
            zot = zotero.Zotero(library_id, library_type, api_key)
            items = zot.top(limit=5)
            # we've retrieved the latest five top-level items in our library
            # we can print each item's item type and ID
            for item in items:
            print('Item Type: %s | Key: %s' % (item['data']['itemType'], item['data']['key']))

Refer to the :ref:`read` and :ref:`write`.


Installation, testing, usage (longer version)
=============================================

============
Installation
============
Using `pip <http://www.pip-installer.org/en/latest/index.html>`_: ``pip install pyzotero``

Using `Anaconda <https://www.anaconda.com/distribution/>`_: ``conda config --add channels conda-forge && conda install pyzotero``

From a local clone, if you wish to install Pyzotero from a specific branch:

    .. code-block:: bash


        git clone git://github.com/urschrei/pyzotero.git
        cd pyzotero
        git checkout main
        pip install .

The Pyzotero source tarball is also available from `PyPI <http://pypi.python.org/pypi/Pyzotero>`_



===============================
Installing development versions
===============================
Pyzotero remains in development as of November 2024. Unstable development versions can be found on the `Github main branch <https://github.com/urschrei/pyzotero/tree/main>`_, and installed directly from a checked-out ``main`` branch on a local clone, as in the example above.


=======
Testing
=======
Testing requires the ``HTTPretty``, and ``Python-Dateutil`` packages.

Run ``pytest .`` from the top-level directory.


======================
Building Documentation
======================
If you wish to build Pyzotero's documentation for offline use, it can be built from the ``doc`` directory of a local git repo by running ``make`` followed by the desired output format(s) (``html``, ``epub``, ``latexpdf`` etc.)

This functionality requires Sphinx.
See the `Sphinx documentation <http://sphinx.pocoo.org/tutorial.html#running-the-build>`_ for full details.


================
Reporting issues
================
If you encounter an error while using Pyzotero, please open an issue on its `Github issues page <https://github.com/urschrei/pyzotero/issues>`_.


=====================
General Usage
=====================

.. important::
    A ``Zotero`` instance is bound to the library or group used to create it. Thus, if you create a ``Zotero`` instance with a ``library_id`` of ``67`` and a ``library_type`` of ``group``, its item methods will only operate upon that group. Similarly, if you create a ``Zotero`` instance with your own ``library_id`` and a ``library_type`` of ``user``, the instance will be bound to your Zotero library.


First, create a new Zotero instance:


    .. py:class:: Zotero(library_id, library_type[, api_key, preserve_json_order, locale, local])

        :param str library_id: a valid Zotero API user ID
        :param str library_type: a valid Zotero API library type: **user** or **group**
        :param str api_key: a valid Zotero API user key
        :param bool preserve_json_order: Load JSON returns with OrderedDict to preserve their order
        :param str locale: Set the `locale <https://www.zotero.org/support/dev/web_api/v3/types_and_fields#zotero_web_api_item_typefield_requests>`_, allowing retrieval of localised item types, field types, and creator types. Defaults to "en-US".
        :param str local: use the local Zotero http server instead of the remote API. Note that the local server currently (November 2024) only allows **read** requests


Example:

    .. code-block:: python
        :emphasize-lines: 4

        from pyzotero import zotero
        zot = zotero.Zotero('123', 'user', 'ABC1234XYZ')
        # we now have a Zotero object, zot, and access to all its methods
        first_ten = zot.items(limit=10)
        # a list containing dicts of the ten most recently modified library items


.. _read:

Errors
=======
Where possible, any ``ZoteroError`` which is raised will preserve the underlying error in its ``__cause__`` and ``__context__`` properties, should you wish to work with these directly.


Read API Methods
====================

.. note::
    All search/request parameters inside square brackets are **optional**. Methods such as :py:meth:`Zotero.top()`, :py:meth:`Zotero.items()` etc. can be called with no additional parameters if you wish.

.. tip::
    The Read API returns 25 results by default (the API documentation claims 50). In the interests of usability, Pyzotero returns 100 items by default, by setting the API ``limit`` parameter to 100, unless it's set by the user. If you wish to retrieve e.g. all top-level items without specifying a ``limit`` parameter, you'll have to wrap your call with :py:meth:`Zotero.everything()`: ``results = zot.everything(zot.top())``.


.. py:method:: Zotero.key_info()

    Returns info about the user and group library permissions associated with the current ``Zotero`` instance, based on the API key. Together with :py:meth:`Zotero.groups()`, this allows all accessible resources to be determined.

    :rtype: dict

====================
Retrieving Items
====================

.. tip::
    In contrast to the v1 API, a great deal of additional metadata is now returned. In most cases, simply accessing items by referring to their ``item['data']`` key will suffice.


The following methods will retrieve either user or group items, depending on the value (``user`` or ``group``) used to create the ``Zotero`` instance:


    .. py:method:: Zotero.items([search/request parameters])

        Returns Zotero library items

        :rtype: list of dicts

    .. py:method:: Zotero.count_items()

        Returns a count of all items in a library / group

        :rtype: int

    .. py:method:: Zotero.top([search/request parameters])

        Returns top-level Zotero library items

        :rtype: list of dicts

    .. py:method:: Zotero.publications([search/request parameters])

        Returns the publications from the "My Publications" collection of a user's library. Only available on ``user`` libraries.

        :rtype: list of dicts

    .. py:method:: Zotero.trash([search/request parameters])

        Returns library items from the library's trash

        :rtype: list of dicts

    .. py:method:: Zotero.deleted([search/request parameters])

        Returns deleted collections, library items, tags, searches and settings (requires "since=" parameter)

        :rtype: list of dicts

    .. py:method:: Zotero.item(itemID[, search/request parameters])

        Returns a specific item

        :param str itemID: a zotero item ID
        :rtype: list of dicts

    .. py:method:: Zotero.children(itemID[, search/request parameters])

        Returns the child items of a specific item

        :param str itemID: a zotero item ID
        :rtype: list of dicts


    .. py:method:: Zotero.collection_items(collectionID[, search/request parameters])

        Returns items from the specified collection. This does not include items in sub-collections

        :param str collectionID: a Zotero collection ID
        :rtype: list of dicts


    .. py:method:: Zotero.collection_items_top(collectionID[, search/request parameters])

        Returns top-level items from the specified collection.

        :param str collectionID: a Zotero collection ID
        :rtype: list of dicts

    .. py:method:: Zotero.get_subset(itemIDs[, search/request parameters])

        Retrieve an arbitrary set of non-adjacent items. Limited to 50 items per call.

        :param list itemIDs: a list of Zotero Item IDs
        :rtype: list of dicts

.. _returned:

Example of returned item data:


    .. code-block:: python


        [{u'data': {u'ISBN': u'0810116820',
                   u'abstractNote': u'',
                   u'accessDate': u'',
                   u'archive': u'',
                   u'archiveLocation': u'',
                   u'callNumber': u'HIB 828.912 BEC:3g N9',
                   u'collections': [u'2UNGXMU9'],
                   u'creators': [{u'creatorType': u'author',
                                  u'firstName': u'Daniel',
                                  u'lastName': u'Katz'}],
                   u'date': u'1999',
                   u'dateAdded': u'2010-01-04T14:50:40Z',
                   u'dateModified': u'2014-08-06T11:28:41Z',
                   u'edition': u'',
                   u'extra': u'',
                   u'itemType': u'book',
                   u'key': u'VDNIEAPH',
                   u'language': u'',
                   u'libraryCatalog': u'library.catalogue.tcd.ie Library Catalog',
                   u'numPages': u'',
                   u'numberOfVolumes': u'',
                   u'place': u'Evanston, Ill',
                   u'publisher': u'Northwestern University Press',
                   u'relations': {u'dc:replaces': u'http://zotero.org/users/436/items/9TXN8QUD'},
                   u'rights': u'',
                   u'series': u'',
                   u'seriesNumber': u'',
                   u'shortTitle': u'Saying I No More',
                   u'tags': [{u'tag': u'Beckett, Samuel', u'type': 1},
                             {u'tag': u'Consciousness in literature', u'type': 1},
                             {u'tag': u'English prose literature', u'type': 1},
                             {u'tag': u'Ireland', u'type': 1},
                             {u'tag': u'Irish authors', u'type': 1},
                             {u'tag': u'Modernism (Literature)', u'type': 1},
                             {u'tag': u'Prose', u'type': 1},
                             {u'tag': u'Self in literature', u'type': 1},
                             {u'tag': u'Subjectivity in literature', u'type': 1}],
                   u'title': u'Saying I No More: Subjectivity and Consciousness in The Prose of Samuel Beckett',
                   u'url': u'',
                   u'version': 792,
                   u'volume': u''},
         u'key': u'VDNIEAPH',
         u'library': {u'id': 436,
                      u'links': {u'alternate': {u'href': u'https://www.zotero.org/urschrei',
                                                u'type': u'text/html'}},
                      u'name': u'urschrei',
                      u'type': u'user'},
         u'links': {u'alternate': {u'href': u'https://www.zotero.org/urschrei/items/VDNIEAPH',
                                   u'type': u'text/html'},
                    u'self': {u'href': u'https://api.zotero.org/users/436/items/VDNIEAPH',
                              u'type': u'application/json'}},
         u'meta': {u'creatorSummary': u'Katz',
                   u'numChildren': 0,
                   u'parsedDate': u'1999-00-00'},
         u'version': 792}]



See :ref:`'Hello World' <hello-world>` example, above

====================
Retrieving Files
====================

    .. py:method:: Zotero.file(itemID[, search/request parameters])

        Returns the raw file content of an item. This can be dumped like so:

        .. code-block:: python

          with open('article.pdf', 'wb') as f:
            f.write(zot.file('BM8MZJBB'))

        :param str itemID: a zotero item ID
        :rtype: binary string

    .. py:method:: Zotero.dump(itemID[, filename, path])

      A convenient wrapper around :py:meth:`Zotero.file()`. Writes an attachment to disk using the optional path and filename.
      If neither are supplied, the file is written to the current working
      directory, and a :py:meth:`Zotero.item()` call is first made to determine the attachment
      filename. No error checking is done regarding the path. If successful, the full path including the file name is returned.

      .. note:: HTML snapshots will be dumped as zip files. These will be named with their API item key, and a .zip extension.

      .. code-block:: python

        # write a file to the current working directory using the stored filename
        zot.dump('BM8MZJBB')
        # write the same file to a different path, with a new name
        zot.dump('BM8MZJBB', 'article_1.pdf', '/home/beckett/pdfs')

      :param str itemID: a zotero item ID
      :param str filename: (optional) an alternate filename
      :param str path: (optional) a valid path for the file
      :rtype: String


File retrieval and dumping should work for most common document, audio and video file formats. If you encounter an error, `please open an issue <https://github.com/urschrei/pyzotero/issues>`_.

=======================
Retrieving Collections
=======================
    .. py:method:: Zotero.collections([search/request parameters])

        Returns a library's collections. **This includes subcollections**.

        :rtype: list of dicts

    .. py:method:: Zotero.collections_top([search/request parameters])

        Returns a library's top-level collections.

        :rtype: list of dicts

    .. py:method:: Zotero.collection(collectionID[, search/request parameters])

        Returns a specific collection

        :param str collectionID: a Zotero library collection ID
        :rtype: dict

    .. py:method:: Zotero.collections_sub(collectionID[, search/request parameters])

        Returns the sub-collections of a specific collection

        :param str collectionID: a Zotero library collection ID
        :rtype: list of dicts

    .. py:method:: Zotero.all_collections([collectionID])

        Returns either all collections and sub-collections in a flat list, or, if a collection ID is specified, that collection and all of its sub-collections. This method can be called at any collection "depth".

        :param str collectionID: a Zotero library collection ID (optional)
        :rtype: list of dicts

Example of returned collection data:

    .. code-block:: python

        [{u'data': {u'key': u'5TSDXJG6',
                    u'name': u'Critical GIS',
                    u'parentCollection': False,
                    u'relations': {},
                    u'version': 778},
          u'key': u'5TSDXJG6',
          u'library': {u'id': 436,
                       u'links': {u'alternate': {u'href': u'https://www.zotero.org/urschrei',
                                                 u'type': u'text/html'}},
                       u'name': u'urschrei',
                       u'type': u'user'},
          u'links': {u'alternate': {u'href': u'https://www.zotero.org/urschrei/collections/5TSDXJG6',
                                    u'type': u'text/html'},
                     u'self': {u'href': u'https://api.zotero.org/users/436/collections/5TSDXJG6',
                               u'type': u'application/json'}},
          u'meta': {u'numCollections': 0, u'numItems': 1},
          u'version': 778}]


==========================
Retrieving groups
==========================
    .. py:method:: Zotero.groups([search/request parameters])

        Retrieve the Zotero group data to which the current library_id and api_key has access

        :rtype: list of dicts

Example of returned group data:

    .. code-block:: python

        [{u'data': {u'description': u'',
                    u'fileEditing': u'admins',
                    u'hasImage': 1,
                    u'id': 169947,
                    u'libraryEditing': u'admins',
                    u'libraryReading': u'members',
                    u'members': [1177919, 1408658],
                    u'name': u'smart_cities',
                    u'owner': 436,
                    u'type': u'Private',
                    u'url': u'',
                    u'version': 0},
          u'id': 169947,
          u'links': {u'alternate': {u'href': u'https://www.zotero.org/groups/169947',
                                    u'type': u'text/html'},
                     u'self': {u'href': u'https://api.zotero.org/groups/169947',
                               u'type': u'application/json'}},
          u'meta': {u'created': u'2013-05-22T11:22:46Z',
                    u'lastModified': u'2013-05-22T11:26:50Z',
                    u'numItems': 817},
          u'version': 0}]


===================
Retrieving Tags
===================

    .. py:method:: Zotero.tags([search/request parameters])

        Returns a library's tags

        :rtype: list of strings

    .. py:method:: Zotero.item_tags(itemID[, search/request parameters])

        Returns tags from a specific item

        :param str itemID: a valid Zotero library Item ID
        :rtype: list of strings

Example of returned tag data:

    .. code-block:: python

        ['Authority in literature', 'Errata']

==============================
Retrieving Version Information
==============================

The `Zotero API <https://www.zotero.org/support/dev/web_api/v3/syncing>`_ recommends requesting version information for all (or all changed) items and collections when implementing syncing.  The following convenience methods (which by default return an unlimited number of responses) simplify this process.

The return values of these methods associate each item / collection with the last version (or greater) at which the item / collection was modified.  By passing the keyword argument ``since=versionNum`` only items / collections which have been modified since ``versionNum`` are included in the response. Thus, an application which previously sucessfully synced with the server at ``versionNum`` can use these methods to determine which items / collections need to be retrieved from the server.

    .. py:method:: Zotero.item_versions([search/request parameters])

        Returns a dict containing version information for items in the library

        :rtype: dict: string -> integer

    .. py:method:: Zotero.collection_versions(itemID[, search/request parameters])

        Returns a dict containing version information for collections in the library

        :rtype: dict: string -> integer

Example of returned version data:

    .. code-block:: python

        {'C9KW275P': 3915, 'IB489TKM': 4025 }


=================
Full–Text Content
=================

These methods allow the retrieval of full–text content for given library items

    .. py:method:: Zotero.new_fulltext(since)

    Returns a dict containing item keys and library versions newer than
    ``since`` (a library version string, e.g. ``"1085"``)

    :rtype: dict: string -> integer

Example of returned data:

    .. code-block:: python

        {
            u'229QED6I': 747,
            u'22TGJFS2': 769,
            u'23SZWREM': 764
        }

    .. py:method:: Zotero.fulltext_item(itemID[, search/request parameters])

    Returns a dict containing full-text data for the given attachment item.
    ``indexedChars`` and ``totalChars`` are used for text documents, while ``indexedPages`` and ``totalPages`` are used for PDFs.

Example of returned data:

    .. code-block:: python

        {
        "content": "This is full-text content.",
        "indexedPages": 50,
        "totalPages": 50
        }

    .. py:method:: Zotero.set_fulltext(itemID, payload)

    Set full-text data for an item

    :rtype: boolean

    ``itemID`` should correspond to an existing attachment item.

    ``payload``: a dict containing three keys:

        ``content``: the full-text content, and either

        For text documents, ``indexedChars`` and ``totalChars`` OR

        For PDFs, ``indexedPages`` and ``totalPages``.

Example payload:

    .. code-block:: python

        {
        "content": "This is full-text content.",
        "indexedPages": 50,
        "totalPages": 50
        }

==============================================
The ``follow()``, and ``everything()`` methods
==============================================

These methods (currently experimental) aim to make Pyzotero a little more RESTful. Following any Read API call which can retrieve **multiple items**, calling ``follow()`` will repeat that call, but for the next *x* number of items, where *x* is either a number set by the user for the original call, or 50 by default. Each subsequent call to ``follow()`` will extend the offset.

.. py:method:: Zotero.follow()

Example:

    .. code-block:: python

        from pyzotero import zotero
        zot = zotero.Zotero(library_id, library_type, api_key)
        # only retrieve a single item
        # this will retrieve the most recently added/modified top-level item
        first_item = zot.top(limit=1)
        # now we can start retrieving subsequent items
        next_item = zot.follow()
        third_item = zot.follow()


.. py:method:: Zotero.everything()

Example:

    .. code-block:: python

        from pyzotero import zotero
        zot = zotero.Zotero(library_id, library_type, api_key)
        # retrieve all top-level items
        toplevel = zot.everything(zot.top())

The ``everything()`` method should work with all Pyzotero Read API calls which can return multiple items, but has not yet been extensively tested. `Feedback is welcomed <https://github.com/urschrei/pyzotero/issues>`_.

Related generator methods
-------------------------

The :py:meth:`Zotero.iterfollow()` and :py:meth:`Zotero.makeiter()` methods are available for users who prefer to work directly with generators:


.. py:method:: Zotero.iterfollow()

    :rtype: a generator over the :py:meth:`follow()` method.

Example:

    .. code-block:: python

        z = zot.top(limit=5)
        lazy = zot.iterfollow()
        lazy.next() # the next() call has returned the next five items

.. py:method:: Zotero.makeiter(API call)

    Returns a generator over a Read API method

    :param function API call: a Pyzotero Read API method capable of returning multiple items
    :rtype: generator

Example:

    .. code-block:: python

        gen = zot.makeiter(zot.top(limit=5))
        gen.next() # this will return the first five items
        gen.next() # this will return the next five items



.. warning:: The ``follow()``, ``everything()`` and ``makeiter()`` methods are only valid for methods which can return multiple library items. For instance, you cannot use ``follow()`` after an ``item()`` call. The generator methods will raise a ``StopIteration`` error when all available items retrievable by your chosen API call have been exhausted.

======================
Retrieving item counts
======================

If you wish to retrieve item counts for subsets of a library, you can use the following methods:

.. py:method:: Zotero.num_items()

    Returns the count of top-level items in the library

    :rtype: int

.. py:method:: Zotero.num_collectionitems(collectionID)

    Returns the count of items in the specified collection

    :rtype: int

================================
Retrieving last modified version
================================

If you wish to retrieve the last modified version of a user or group library, you can use the following method:

.. py:method:: Zotero.last_modified_version()

    Returns the last modified version of the library

    :rtype: int


==============================================
Search / Request Parameters for Read API calls
==============================================

Additional parameters may be set on Read API methods **following any required parameters**, or set using the :py:meth:`Zotero.add_parameters()` method detailed below.


The following two examples produce the same result:

    .. code-block:: python

        # set parameters on the call itself
        z = zot.top(limit=7, start=3)

        # set parameters using explicit method
        zot.add_parameters(limit=7, start=3)
        z = zot.top()

The following parameters are **optional**.

**You may also set a search term here, using the 'itemType', 'q', 'qmode', or 'tag' parameters**.

This area of the Zotero Read API is under development, and may change frequently. See `the API documentation <https://www.zotero.org/support/dev/web_api/v3/basics#read_requests>`_ for the most up-to-date details of search syntax usage and export format details.



    .. py:method:: Zotero.add_parameters([format=None, itemKey=None, itemType=None, q=None, qmode=None, since=None, tag=None, sort=None, direction=None, limit=None, start=None, [content=None[ ,style=None]]])

        :param str format: "atom", "bib", "bibtex", json", "keys", "versions". Pyzotero retrieves and decodes JSON responses by default

        .. attention::

          Setting ``format='bib'`` will remove the ``limit`` parameter if it's been set, as **the API does not allow a limit on bibliography output**; it instead enforces a limit of 150 items, and if the set of items you are trying to generate a bibliography for exceeds 150, an error will be raised.

        :param str itemKey: A comma-separated list of item keys. Valid only for item requests. Up to 50 items can be specified in a single request

        Search parameters:

        :param str itemType: item type search. See the `Search Syntax <https://www.zotero.org/support/dev/web_api/v3/basics#search_syntax>`_ for details
        :param str q: Quick search. Searches titles and individual creator fields by default. Use the ``qmode`` parameter to change the mode. Currently supports phrase searching only
        :param str qmode: Quick search mode. To include full-text content in the search, use ``everything``. Defaults to ``titleCreatorYear``. Searching of other fields will be possible in the future
        :param int since: default ``0``. Return only objects modified after the specified library version
        :param str tag: tag search. See the `Search Syntax <https://www.zotero.org/support/dev/web_api/v3/basics#search_syntax>`_ for details. More than one tag may be passed by passing a list of strings – These are treated as ``AND`` search terms, meaning only items which include all of the specified tags are returned. You can search for items matching any tag in a list by using ``OR``: ``"tag1 OR tag2"``, and all items which exclude a tag: ``"-tag"``.

        The following parameters can be used for search requests:

        :param str sort: The name of the field by which entries are sorted: (``dateAdded``, ``dateModified``, ``title``, ``creator``, ``type``, ``date``, ``publisher``, ``publicationTitle``, ``journalAbbreviation``, ``language``, ``accessDate``, ``libraryCatalog``, ``callNumber``, ``rights``, ``addedBy``, ``numItems``, ``tags``)
        :param str direction: ``asc`` or ``desc``
        :param int limit: 1 – 100 or None
        :param int start: 1 – total number of items in your library or None


        If you wish to retrieve citation or bibliography entries, use the following parameters:

        :param str content: 'bib', 'html', or one of the export formats (see below). If 'bib' is passed, you may **also** pass:
        :param str style: Any valid CSL style in the Zotero style repository
        :param str linkwrap: Set this to "1" to have URLs in bibliography entries (see below) wrapped in ``<a>`` tags.
        :rtype: list of HTML strings or None.


.. note::

    Any parameters you set will be valid **for the next call only**. Any parameters set using ``add_parameters()`` will be overridden by parameters you pass in the call itself.


A note on the ``content`` and ``style`` parameters:

Example:

    .. code-block:: python

        zot.add_parameters(content='bib', style='mla')


If these are set, the return value is a list of UTF-8 formatted HTML ``div`` elements, each containing an item:

``['<div class="csl-entry">(content)</div>']``.

You may also set ``content='citation'`` if you wish to retrieve citations. Similar to ``bib``, the result will be a list of one or more HTML ``span`` elements.


If you select one of the available `export formats <https://www.zotero.org/support/dev/web_api/v3/basics#export_formats>`_ as the ``content`` parameter, pyzotero will in most cases return a list of unicode strings in the format you specified. The exception is the ``csljson`` format, which is parsed into a list of dicts. Please note that you must provide a ``limit`` parameter if you specify one of these export formats. Multiple simultaneous retrieval of particular formats, e.g. ``content="json,coins"`` is not currently supported.

If you set ``format='keys'``, a newline-delimited string containing item keys will be returned

If you set ``format='bibtex'``, a `bibtexparser <https://bibtexparser.readthedocs.io/en/v0.6.2/bibtexparser.html#bibdatabase.BibDatabase.entries>`_ object containing citations will be returned. You can access the citations as a list of dicts using the ``.entries`` property. The bibtexparser object also implements a `dump method <https://bibtexparser.readthedocs.io/en/v0.6.2/bibtexparser.html#bibtexparser.dump>`_, if you'd like to write your citations to a ``.bib`` file.


.. _write:

Write API Methods
=================

==============
Saved Searches
==============
Pyzotero allows you to retrieve, delete, or modify saved searches:

    .. py:method:: Zotero.searches()

        Retrieve all saved searches. Note that this retrieves saved search *metadata*, as opposed to *content*; saved searches cannot currently (January 2019) be run using the API.

        :rtype: list of dicts

    .. py:method:: Zotero.saved_search(name, conditions)

        Create a new saved search. `conditions` is a list of one or more dicts, each of which must contain the following three string keys:
        `condition`, `operator`, `value`. See the `documentation <https://www.zotero.org/support/dev/web_api/v3/write_requests#saved_search_requests>`_ for an example.

        :param str name: the name of the search
        :param list conditions: one or more dicts containing search conditions and operators
        :rtype: dict showing creation success status

    .. py:method:: Zotero.delete_saved_search(search_keys)

        Delete one or more saved searches. `search_keys` is a list of one or more search keys. These can be retrievd using :py:meth:`Zotero.searches()`

        :param list search_keys: list of unique saved search keys
        :rtype: None

    .. py:method:: Zotero.show_operators()

        Show available saved search operators

        :rtype: list

    .. py:method:: Zotero.show_conditions()

        Show available saved search conditions

        :rtype: list

    .. py:method:: Zotero.show_condition_operators(condition)

        Show available operators for a given saved search condition

        :param str condition: a valid saved search condition
        :rtype: list

=================
Item Methods
=================

    .. py:method:: Zotero.item_types()

        Returns a dict containing all available item types
        
        :rtype: dict

    .. py:method:: Zotero.item_fields()

        Returns a dict of all available item fields

        :rtype: dict

    .. py:method:: Zotero.item_creator_types(itemtype)

        Returns a dict of all valid creator types for the specified item type

        :param str itemtype: a valid Zotero item type. A list of available item types can be obtained by the use of :py:meth:`item_types()`
        :rtype: dict

    .. py:method:: Zotero.creator_fields()

        Returns a dict containing all localised creator fields

        :rtype: dict

    .. py:method:: Zotero.item_type_fields(itemtype)

        Returns all valid fields for the specified item type

        :param str itemtype: a valid Zotero item type. A list of available item types can be obtained by the use of :py:meth:`item_types()`
        :rtype: list of dicts

    .. py:method:: Zotero.item_template(itemtype, linkmode)

        Returns an item creation template for the specified item type

        :param str itemtype: a valid Zotero item type. A list of available item types can be obtained by the use of :py:meth:`item_types()`
        :param str linkmode: either None (default) or a valid Zotero linkMode value required when itemtype is attachment. A list of available link modes can be obtained by the use of :py:meth:`item_attachment_link_modes()`
        :rtype: dict

Creating and Updating Items
---------------------------

    .. py:method:: Zotero.create_items(items[, parentid, last_modified])

        Create Zotero library items

        :param list items: one or more dicts containing item data
        :param str parentid: A Parent item ID. This will cause the item(s) to become the child items of the given parent ID
        :param str/int last_modified: If not None will set the value of the If-Unmodified-Since-Version header. 
        :rtype: list of dicts

        Returns a copy of the created item(s), if successful. Use of :py:meth:`item_template` is recommended in order to first obtain a dict with a structure which is known to be valid.

        Before calling this method, the use of :py:meth:`check_items()` is encouraged, in order to confirm that the item to be created contains only valid fields.

        Note that if any items contain a key field matching an existing item on the server it will be updated (any properties not in the dict will be left unmodified).

Example:

    .. code-block:: python

        template = zot.item_template('book')
        template['creators'][0]['firstName'] = 'Monty'
        template['creators'][0]['lastName'] = 'Cantsin'
        template['title'] = 'Maris Kundzins: A Life'
        resp = zot.create_items([template])


If successful, ``resp`` will be a dict containing the creation status of each item:

    .. code-block:: python

        {'failed': {}, 'success': {'0': 'ABC123'}, 'unchanged': {}}

    .. py:method:: Zotero.update_item(item [, last_modified])

        Update an item in your library

        :param dict item: a dict containing item data.  Fields not in item will be left unmodified.
        :param str/int last_modified: If not ``None``, will set the value of the If-Unmodified-Since-Version header.  If unspecified/None then If-Unmodified-Since-Version will be set to the version property of item.
        :rtype: Boolean

        Will return ``True`` if the request was successful, or will raise an error.

Example:

    .. code-block:: python

        i = zot.items()
        # see above for example of returned item structure
        # modify the latest item which was added to your library
        i[0]['data']['title'] = 'The Sheltering Sky'
        i[0]['data']['creators'][0]['firstName'] = 'Paul'
        i[0]['data']['creators'][0]['lastName'] = 'Bowles'
        zot.update_item(i[0])

  .. py:method:: Zotero.update_items(items)

      Update items in your library. The API only accepts 50 items per call, so longer updates are chunked

      :param list items: a list of dicts containing Item data. Fields not in item will be left unmodified.
      :rtype: Boolean

      Will return ``True`` if the request was successful, or will raise an error.

  .. py:method:: Zotero.check_items(items)

      Check whether items to be created on the server contain only valid keys. This method first creates a set of valid keys by calling :py:meth:`item_fields()`, then compares the user-created dicts to it. If any keys in the user-created dicts are unknown, a ``InvalidItemFields`` exception is raised, detailing the invalid fields.

      :param list items: one or more dicts containing item data
      :rtype: List. Each list item is a valid dict containing item data.


Uploading files
---------------

    .. warning:: Attachment methods are in beta.

    .. py:method:: Zotero.attachment_simple(files[, parentid])

        Create one or more file attachment items.

        :param list files: a list containing one or more file paths: ``['/path/to/file/file.pdf', … ]``
        :param string parentid: a library Item ID. If this is specified, attachments will be created as child items of this ID.
        :rtype: Dict. Showing status of each requested upload.

    .. py:method:: Zotero.attachment_both(files[, parentid])

        Create one or more file attachment items, specifying names for uploaded files

        :param list files: a list containing one or more lists or tuples in the following format: ``(file name, file path)``
        :param string parentid: a library Item ID. If this is specified, attachments will be created as child items of this ID.
        :rtype: Dict. Showing status of each requested upload.

    .. py:method:: Zotero.upload_attachments(attachments[, parentid, basedir=None])

        Upload files to their corresponding attachments.  If the attachments lack the ``key`` property they are assumed not to exist and will be created.  The ``parentid`` parameter is **not compatible** with existing attachments.  In order for uploads to succeed, the filename parameter of each attachment must resolve.

        This method is really only required in cases where a sync has been interrupted, leaving your library with attachment items that don't have corresponding files attached. It *may* also work for uploading modified files, though **this is untested**.

        :param list attachments: A list of dicts representing zotero imported files which may or may not already have their key fields filled in.
        :param string parentid: a library Item ID. If this is specified and key fields are not included, attachments will be created as child items of this ID.
        :param string/path basedir: A string or path object to which the filenames specified in attachments will be evaluated relative to.  If unspecified the filenames are evaluated as they are.
        :rtype: Dict. Showing status of each requested upload.

    .. code-block:: python

            # example of the return type
            {
                'success': [attach1, attach2...],
                'failure': [attach3, attach4...],
                'unchanged': [attach4, attach5...]
            }
    
    .. note:: 
        unlike the space-saving responses from the server, the return value here eschews the complex index / key lookup and simply passes back the ``imported_file`` item template populated with keys (if created successfully or passed in) corresponding to each result. This is the return type for all of these methods.

Deleting items
--------------

    .. py:method:: Zotero.delete_item(item[, last_modified])

        Delete one or more items from your library

        :param list item: a list of one or more dicts containing item data. You must first retrieve the item(s) you wish to delete, as ``version`` data is required.
        :param str/int last_modified: If not ``None``, will set the value of the If-Unmodified-Since-Version header. 

Deleting tags
--------------

    .. py:method:: Zotero.delete_tags(tag_a[, tag …])

        Delete one or more tags from your library

        :param string tag: the tag(s) you'd like to delete

        You may also pass a list using ``zot.delete_tags(*[tag_list])``

===========
Adding tags
===========

    .. py:method:: Zotero.add_tags(item, tag[, tag …])

        Add one or more tags to an item, and update it on the server

        :param dict item: a dict containing item data
        :param string tag: the tag(s) you'd like to add to the item
        :rtype: list of dicts

        You may also pass a list using ``zot.add_tags(item, *[tag_list])``

Example:

    .. code-block:: python

        z = zot.top(limit=1)
        # we've now retrieved the most recent top-level item
        updated = zot.add_tags(z[0], 'tag1', 'tag2', 'tag3')
        # updated now contains a representation of the updated server item


====================
Collection Methods
====================

    .. py:method:: Zotero.create_collections(dicts[, last_modified])

        Create a new collection in the Zotero library

        :param list dicts: list of dicts each containing the key ``name``, with each value being a new collection name you wish to create. Each dict may optionally contain a ``parentCollection`` key, the value of which is the ID of an existing collection. If this is set, the collection will be created as a child of that collection.
        :param str/int last_modified: If not None will set the value of the If-Unmodified-Since-Version header. 
        :rtype: list of dicts
        :rtype: Boolean

    .. py:method:: Zotero.create_collection(dicts[, last_modified])

        Alias for :py:meth:`Zotero.create_collections()` to preserve backward compatibility

    .. py:method:: Zotero.addto_collection(collection, item)

        Add the specified item(s) to the specified collection

        :param str collection: a collection key
        :param dict item: an item dict retrieved using an API call
        :rtype: Boolean

        Collection keys can be obtained by a call to :py:meth:`collections()` (see details above).

    .. py:method:: Zotero.deletefrom_collection(collection, item)

        Remove the specified item from the specified collection

        :param str collection: a collection key
        :param dict item: a dict containing item data
        :rtype: Boolean

        See the :py:meth:`delete_item()` example for multiple-item removal.

    .. py:method:: Zotero.update_collection(collection , last_modified])

        Update existing collection metadata (name etc.)

        :param dict collection: a dict containing collection data, previously retrieved using one of the Collections calls (e.g. :py:meth:`collections()`)
        :rtype: Boolean

    .. py:method:: Zotero.update_collections(collection_items)

        Update multiple existing collection metadata. The API only accepts 50 collections per call, so longer updates are chunked

        :param list collection_items: a list of dicts containing Collection data. Fields not in collection_item will be left unmodified.
        :rtype: Boolean

        Will return ``True`` if the request was successful, or will raise an error.

    .. py:method:: Zotero.collection_tags(collectionID[, search/request parameters])

        Retrieve all tags for a given collection

        :param str collectionID: a collection ID
        :rtype: list of strings

Examples:

    .. code-block:: python

            # get existing collections, which will return a list of dicts
            c = zot.collections()
            # rename the last collection created in the library
            c[0]['name'] = 'Whither Digital Humanities?'
            # update collection name on the server
            zot.update_collection(c[0])


    .. py:method:: Zotero.delete_collection(collection[, last_modified])

        Delete a collection from the Zotero library

        :param dict collection: a dict containing collection data, previously retrieved using one of the Collections calls (e.g. :py:meth:`collections()`). Alternatively, you may pass a **list** of collection dicts.
        :param str/int last_modified: If not None will set the value of the If-Unmodified-Since-Version header.
        :rtype: Boolean



Notes
=====
Most Read API methods return **lists** of **dicts** or, in the case of tag methods, **lists** of **strings**. Most Write API methods return either ``True`` if successful, or raise an error. See ``zotero_errors.py`` for a full listing of these.

.. warning:: URL parameters will supersede API calls which should return e.g. a single item: ``https://api.zotero.org/users/436/items/ABC?start=50&limit=10`` will return 10 items beginning at position 50, even though ``ABC`` does not exist. Be aware of this, and don't pass URL parameters which do not apply to a given API method.

License
=======
Pyzotero is licensed under the `Blue Oak Model Licence <https://opensource.org/license/blue-oak-model-license>`_  license.


Cat Picture
===========
This is The Grinch.

.. figure:: cat.png

    *Orangecat*

.. [*] This isn't strictly true: you only need an API key for personal libraries and non-public group libraries.
