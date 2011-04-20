# Description #

This is a first pass at implementing a Python wrapper for the [Zotero API][1]. You'll require a user ID and access key, which can be set up [here][2].

# Installation #

* From github: `pip install git+git://github.com/urschrei/pyzotero.git`  
* From a local clone: `pip install /path/to/pyzotero/dir`  
Example: `pip install ~/repos/pyzotero`  
* Alternatively, download the latest version from <https://github.com/urschrei/pyzotero/downloads>, and point pip at the zip file:  
Example: `pip install ~/Downloads/urschrei-pyzotero-v0.3-0-g04ff544.zip`

I assume that running setup.py will also work using `easy_install`, but I haven't tested it.

The [feedparser][3] (>= v5.0.1) and [ElementTree][7] (>= v1.2.7) modules are required. They should automatically be installed when installing pyzotero using [pip][4].

## Testing ##

Run `tests.py` in the pyzotero directory, or, using [Nose][5], `nosetests` from this directory. If you wish to see coverage statistics, run `nosetests --with-coverage --cover-package=pyzotero`.

Additionally, a basic script, `sample.py`, is included.

# Usage #
## Hello World ##
``` python
from pyzotero import zotero
zot = zotero.Zotero(user_id, user_key)
items = zot.items()
for item in items:
    print 'Author: %s | Title: %s' % (item['author'], item['title'])
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

Example of returned data:

`[{'publication': 'Genetic Joyce Studies', 'author': 'Susan Brown', 'url': 'http://www.geneticjoycestudies.org/GJS7/GJS7brown.html', 'type': 'Journal Article', 'title': 'The Mystery of the Fuga per Canonem Solved', 'date': 'Spring 2007', 'accessed': '2010-03-25 20:30:18', 'issue': '7', 'id': '9T3K4EES'}, … ]`  

See ‘Hello World’ example, above  

### To retrieve collections:###

 * `collections()`, returns a user's collections
 * `collections_sub(collection ID)`, returns a sub-collection from a specific collection
 * `group_collections(group ID)`, returns collections for a specific group
 * `group_collection(group ID, collection ID)`, returns a specific collection from a specific group

Example of returned data:

`[{'id': 'PRMD6BGB', 'title': "A Midsummer Night's Dream"}, … ]`

### To retrieve groups:###

 * `groups()`, returns Zotero library groups

Example of returned data:

`[{'total_items': '468', 'owner': 'urschrei', 'id': '153', 'uid':
'http://zotero.org/groups/dfw', 'title': 'DFW'}, … ]`

### To retrieve tags: ###

* `tags()`, returns a user's tags
* `item_tags(item ID)`, returns tags from a specific item
* `group_tags(group ID)`, returns tags from a specific group
* `group_item_tags(group ID, item ID)`, returns tags from a specific item from a specific group

Example of returned data:

`['Authority in literature', 'Errata', … ]`

# Notes #


All methods return **lists** of **dicts** or, in the case of tag methods, **lists** of **strings**. Example:  

``` python  
zot = zotero.Zotero(user_id, user_key)  
collections = zot.collections()  
for collection in collections:  
    print 'Name: %s | ID: %s' % (collection['title'], collection['id'])
```

If you attempt to call/print/access a key which does not exist, a `KeyError` will be raised. Alternatively, you can use e.g. `item.get('author', None)` which will simply return `None` if a key does not exist. Frequently missing keys are a definite possibility, since Zotero library items have very few mandatory fields.

**URL parameters will supersede API calls which should return e.g. a single item:** `https://api.zotero.org/users/436/items/ABC?start=50&limit=10` will return 10 items beginning at position 50, even though `ABC` does not exist. Be aware of this, and don't pass URL parameters which do not apply to a given API method. This is a limitation/foible of the Zotero API, and there's nothing I can do about it.  


[1]: http://www.zotero.org/support/dev/server_api "Zotero Server API"
[2]: http://www.zotero.org/settings/keys/new "New Zotero Access Credentials"
[3]: http://feedparser.org/ "Mark Pilgrim's Universal Feed Parser"
[4]: http://pypi.python.org/pypi/pip "Pip Installs Packages"
[5]: http://somethingaboutorange.com/mrl/projects/nose/1.0.0/index.html "nose is nicer testing for Python"
[6]: https://github.com/urschrei/pyzotero/issues
[7]: http://effbot.org/zone/element-index.htm

