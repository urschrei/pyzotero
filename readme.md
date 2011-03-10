# Description #

Because it's 2011, and I have no intention of using PHP for anything, let alone writing it, this is a first pass at implementing a Python wrapper for the [Zotero API][1]. There's no use case as yet, since I'm not sure what's going to be the ultimate consumer of the returned data. Expect a lot of initial fragility, if not outright breakage. You'll require a user ID and access key, which can be set up [here][2].

# Installation #

* From github: `pip install git+git://github.com/urschrei/pyzotero.git`  
* From a local clone: `pip install /path/to/pyzotero/dir`  
Example: `pip install ~/repos/pyzotero`  
* Alternatively, download the latest version from <https://github.com/urschrei/pyzotero/downloads>, and point pip at the zip file:  
Example: `pip install ~/Downloads/urschrei-pyzotero-v0.3-0-g04ff544.zip`

I assume that running setup.py will also work using `easy_install`, but I haven't tested it.

The [feedparser][3] module is required. It should automatically be installed when installing pyzotero using [pip][4].

# Usage #
## Hello World ##

    from pyzotero import zotero
    zot = zotero.Zotero(user_id, user_key)
    items = zot.items()
    for item in items:
    print 'Author: %s | Title: %s' % (item.author, item.title)
    
## General Usage ##

Additional parameters may be set using the following method:  
    
    zot.add_parameters(parameter=value, … parameter n = value n)
Example:  

    zot.add_parameters(limit = 5)
    
These parameters will be valid *for the next call only*  
Valid parameters:  

* `limit` (integer, 1 – 99, default 50), limits the number of returned results
* `start` (integer, default 0) sets the start point for returned results
* `order` (string, valid Zotero field name)
* `sort` (string: 'asc' or 'desc')

The following methods are currently available:

### To retrieve items:###

 * `items()`, returns Zotero library items
 * `top()`, returns top-level Zotero library items
 * `item(item ID)`, returns a specific item
 * `children()`, returns the child items of a specific item
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

Example of returned data: `[<Item object at 0x11338f0>, … ]`  
Example Item properties: `id`, `title`, `author`, `publisher`  
See ‘Hello World’ example, above  

### To retrieve collections:###

 * `collections()`, returns a user's collections
 * `collections_sub(collection ID)`, returns a sub-collection from a specific collection
 * `group_collections(group ID)`, returns collections for a specific group
 * `group_collection(group ID, collection ID)`, returns a specific collection from a specific group

Example of returned data: `[{'id': 'PRMD6BGB', 'title': "A Midsummer Night's Dream"}, … ]`

### To retrieve groups:###

 * `groups()`, returns Zotero library groups

Example of returned data: `[{'total_items': '468', 'owner': 'urschrei', 'id': 'DFW'}, … ]`

### To retrieve tags: ###

* `tags()`, returns a user's tags
* `item_tags(item ID)`, returns tags from a specific item
* `group_tags(group ID)`, returns tags from a specific group
* `group_item_tags(group ID, item ID)`, returns tags from a specific item from a specific group

Example of returned data: `['Authority in literature', 'Errata', … ]`

# Notes #


* All methods which return items currently return **lists** of **`Item` instances**. An instance's properties can be accessed like so: `Item.property`. If the property doesn't exist, `None` will be returned. **THIS IS NOT A STABLE FEATURE**; all other methods currently return **lists** of **dicts**, and I'll probably revert to that for items, too. Example:

    `zot = zotero.Zotero(user_id, user_key)`  
    `collections = zot.collections()`  
    `for collection in collections:`  
    `       print 'Name: %s | ID: %s' % (collection['title'], collection['id'])`

* If you attempt to call a key which does not exist, a `KeyError` will be raised. Alternatively, you can use `dictname.get('key', None)` which will simply return `None` if a key does not exist.


* **URL parameters will supersede API calls which should return e.g. a single item:** `https://api.zotero.org/users/436/items/ABC?start=50&limit=10` will return 10 items beginning at position 50, even though `ABC` does not exist. Be aware of this, and don't pass URL parameters which do not apply to a given API method. This is a limitation/foible of the Zotero API, and there's nothing I can do about it.

* Running zotero.py from the command line will attempt to import your ID and key from a file named `zotero_keys.txt` in your home directory (see comment in `main()` for details), create a new Zotero object and call some of the methods.

* **ZOTERO LIBRARY ITEMS ARE NOT ASCII-ENCODED**. In Python 2.x, the `print` function will attempt to encode its output as ASCII unless you specifically tell it otherwise. Customising your encoding is usually accomplished using `sitecustomize.py`, but you're going to have to load and fire your own foot-gun.

[1]: http://www.zotero.org/support/dev/server_api "Zotero Server API"
[2]: http://www.zotero.org/settings/keys/new "New Zotero Access Credentials"
[3]: http://feedparser.org/ "Mark Pilgrim's Universal Feed Parser"
[4]: http://pypi.python.org/pypi/pip "Pip Installs Packages"
