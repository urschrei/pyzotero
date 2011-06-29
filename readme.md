# Description #

This is a first pass at implementing a Python wrapper for the [Zotero API][1]. You'll require a user ID and access key, which can be set up [here][2].

# Installation #

* From github: `pip install git+git://github.com/urschrei/pyzotero.git`  
* From a local clone: `pip install /path/to/pyzotero/dir`  
Example: `pip install ~/repos/pyzotero`  
* Alternatively, download the latest version from <https://github.com/urschrei/pyzotero/downloads>, and point pip at the zip file:  
Example: `pip install ~/Downloads/urschrei-pyzotero-v0.3-0-g04ff544.zip`

I assume that running setup.py will also work using `easy_install`, but I haven't tested it.

The [feedparser][3] (>= v5.0.1) module is required. It should automatically be installed when installing pyzotero using [pip][4].

## Testing ##

Run `tests.py` in the pyzotero directory, or, using [Nose][5], `nosetests` from this directory. If you wish to see coverage statistics, run `nosetests --with-coverage --cover-package=pyzotero`.

# Usage #
## Hello World ##
``` python
from pyzotero import zotero
zot = zotero.Zotero(user_id, user_key)
items = zot.items()
for item in items:
    print 'Author: %s | Title: %s' % (item['creators'][0]['lastName'], item['title'])
```
## General Usage ##

Additional parameters may be set using the following method:  
    
    zot.add_parameters(parameter=value, … parameter n = value n)
Example:  

    zot.add_parameters(limit = 5)
    
These parameters will be valid *for the next call only*  
Valid parameters:  

* `limit` (integer, 1 – 99, default: 50), limits the number of returned results
* `start` (integer, default: 0) sets the start point for returned results
* `order` (string, valid Zotero field name)
* `sort` (string, 'asc' or 'desc')

Special parameters: `content` and `style`

* `content` (string, 'html', 'bib', default: 'html') if 'bib' is passed, you may also pass:
* `style` (string, containing any valid CSL style in the Zotero Style Repository). Example:  
`zot.add_parameters(content = 'bib', format = 'mla')`  
The return value is a **list** of UTF-8 formatted HTML `div`s, each containing an item:  
`['<div class="csl-entry">(content)</div>', … ]`

The following methods are currently available:

## Read API Methods: ##
### To retrieve items:###

 * `items()`, returns Zotero library items
 * `top()`, returns top-level Zotero library items
 * `item(item ID)`, returns a specific item
 * `children(item ID)`, returns the child items of a specific item
 * `tag_items(item ID)`, returns items for a specific tag
 * `group_items(group ID)`, returns items from a specific group
 * `group_top(group ID)`, returns top-level items from a specific group
 * `group_item(group ID, item ID)`, returns a specific item from a specific group
 * `group_item_children(group ID, item ID)`, returns the child items of a specific item from a specific group
 * `group_items_tag(group ID, tag)`, returns a specific group's items for a specific tag
 * `group_collection_items(group ID, collection ID)`, returns a specific collection's items from a specific group
 * `group_collection_item(group ID, collection ID, item ID)`, returns a specific collection's item from a specific group
 * `group_collection_top(group ID, collection ID)`, returns a specific collection's top-level items from a specific group
 * `collection_items(collection ID)`, returns items from the specified collection

**Example of returned data:**

``` python
[{'DOI': '',
 'ISSN': '1747-1532',
 'abstractNote': '',
 'accessDate': '',
 'archive': '',
 'archiveLocation': '',
 'callNumber': '',
 'creators': [{'creatorType': 'author',
               'firstName': 'T. J.',
               'lastName': 'McIntyre'}],
 'date': '2007',
 'extra': '',
 'issue': '',
 'itemType': 'journalArticle',
 'journalAbbreviation': '',
 'language': '',
 'libraryCatalog': 'Google Scholar',
 'pages': '',
 'publicationTitle': 'Journal of Intellectual Property Law & Practice',
 'rights': '',
 'series': '',
 'seriesText': '',
 'seriesTitle': '',
 'shortTitle': 'Copyright in custom code',
 'tags': [],
 'title': 'Copyright in custom code: Who owns commissioned software?',
 'url': '',
 'volume': ''} … ]
```

See ‘Hello World’ example, above  

### To retrieve collections:###

 * `collections()`, returns a user's collections
 * `collections_sub(collection ID)`, returns a sub-collection from a specific collection
 * `group_collections(group ID)`, returns collections for a specific group
 * `group_collection(group ID, collection ID)`, returns a specific collection from a specific group

**Example of returned data:**

`[{'key': 'PRMD6BGB', 'name': "A Midsummer Night's Dream"}, … ]`

### To retrieve groups:###

 * `groups()`, returns Zotero library groups

**Example of returned data:**

``` python
[{u'description': u'%3Cp%3EBibliographic+resources+and+media+clips+of+German+Cinema+and+related+literature.%3C%2Fp%3E',
  u'fileEditing': u'none',
  'group_id': u'153',
  u'hasImage': 1,
  u'libraryEditing': u'admins',
  u'libraryEnabled': 1,
  u'libraryReading': u'all',
  u'members': {u'0': 436,
               u'1': 6972,
               u'15': 499956,
               u'16': 521307,
               u'17': 619180},
  u'name': u'German Cinema',
  u'owner': 10421,
  u'type': u'PublicOpen',
  u'url': u''} … ]
```

### To retrieve tags: ###

* `tags()`, returns a user's tags
* `item_tags(item ID)`, returns tags from a specific item
* `group_tags(group ID)`, returns tags from a specific group
* `group_item_tags(group ID, item ID)`, returns tags from a specific item from a specific group

**Example of returned data:**

`['Authority in literature', 'Errata', … ]`

## Write API Methods: ##
### Item Methods: ###

Full [Write API][8] methods are WIP. The following methods are currently available:

* `item_types()`, returns a dict of all available item types 
* `item_fields()`, returns a dict of all available item fields
* `item_creator_types(itemtype)`, returns a dict of all valid creator types for the specified item type 
* `item_template(itemtype)`, returns an item creation template dict for the specified item type 

---

* `create_item(items)`, create Zotero library items. Accepts a list of one or more dicts as its only argument. Returns a copy of the created item(s), if successful. The use of `item_template(itemType)` is recommended in order to first obtain a dict with a structure which the API will accept.

**Example:**

``` python
template = zot.item_template('book')
template['creators'][0]['firstName'] = 'Monty'
template['creators'][0]['lastName'] = 'Cantsin'
template['title'] = 'Maris Kundzins: A Life'
resp = zot.create_item([template])
```

If successful, `resp` will have the same structure as items retrieved with an `items()` call, e.g. a list of one or more dicts (see example, above).

* `update_item(item)`, update an item in your library. Accepts a dict containing item data as its only argument.

**Example:**

``` python
i = zot.items()
# see above for example of returned item structure
# modify the latest item which was added to your library
i[0]['title] = 'The Sheltering Sky'
i[0]['creators'][0]['firstName'] = 'Paul'
i[0]['creators'][0]['lastName'] = 'Bowles'
zot.update_item(i[0])
```

* `delete_item()`, delete an item from your library. Accepts a dict containing item data as its only argument. As in the previous example, you must first retrieve the item(s) you wish to delete, and pass it/them to the method one by one. Deletion of multiple items is most easily accomplished using e.g. a `for` loop. Returns `True` if successful.

**Example:**

``` python
i = zot.items()
# only delete the last five items we added
to_delete = i[:6]
for d in to_delete:
    zot.delete_item(d)
```

### Collection Methods: ###

* `create_collection(name)`, create a new collection in the Zotero library. Accepts one argument, a dict containing the key `name` and the value of the new collection name you wish to create. Optionally, the key `parent`, and the value containing the ID of an existing collection may be included. The collection will then be created as a child collection of the passed collection ID. Returns `True` if successful.
* `addto_collection(collection, items)`, add the specified item(s) to the specified collection. Accepts two arguments: a collection key, and a list of one or more item dicts. Collection keys can be obtained by a call to `collections()` (see details above). Returns `True` if successful.
* `deletefrom_collection(collection, item)`, remove the specified item from the specified collection. Accepts two arguments: a collection key, and a dict containing item data. See the `delete_item()` example for multiple-item removal. Returns `True` if successful.
* `update_collection()`, update an existing collection name. Accepts a single argument: a dict containing collection data, previously retrieved using one of the Collections calls (e.g. `collections()`). Returns `True` if successful.

**Example:**

``` python
# get existing collections, which will return a list of dicts
c = zot.collections()
# rename the last collection created in the library
c[0]['name'] = 'Whither Digital Humanities?'
# update collection name on the server
zot.update_collection(c[0])
```

# Notes #

All Read API methods return **lists** of **dicts** or, in the case of tag methods, **lists** of **strings**. 

**URL parameters will supersede API calls which should return e.g. a single item:** `https://api.zotero.org/users/436/items/ABC?start=50&limit=10` will return 10 items beginning at position 50, even though `ABC` does not exist. Be aware of this, and don't pass URL parameters which do not apply to a given API method. This is a limitation/foible of the Zotero API, and there's nothing I can do about it.  

# License #

Pyzotero is licensed under the [GNU GPL Version 3][9] license, in line with Zotero's own license. Details can be found in the file `license.txt`.

[1]: http://www.zotero.org/support/dev/server_api "Zotero Server API"
[2]: http://www.zotero.org/settings/keys/new "New Zotero Access Credentials"
[3]: http://feedparser.org/ "Mark Pilgrim's Universal Feed Parser"
[4]: http://pypi.python.org/pypi/pip "Pip Installs Packages"
[5]: http://somethingaboutorange.com/mrl/projects/nose/1.0.0/index.html "nose is nicer testing for Python"
[6]: https://github.com/urschrei/pyzotero/issues
[8]: http://www.zotero.org/support/dev/server_api/write_api
[9]: http://www.gnu.org/licenses/gpl.html "GNU GPL Version 3"