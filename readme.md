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

1. Create a new Zotero object:  
`from pyzotero import zotero`  or `import pyzotero.zotero as z` &c  
`zot = zotero.Zotero(user_id, user_key)`  
2. The following object methods are available:
    * `items_data()`: returns a list of dicts containing each **item's** data (author, title, publisher &c)
    * `gen_items_data()`: returns a generator object of dicts containing each **item's** data (author, title, publisher &c)
    * `collections_data()`: returns a list of dicts containing each **collection's** data (ID, title, number of subcollections)
    * `groups_data()`: returns a list of dicts containing each **group's** data (owner, title, total number of items)
    * `bib_items()`: returns a list containing HTML-formatted bibliography entries for each **item**. When calling this method, you may specify a `'style'` key in `params`, the value of which can be any valid Zotero Style Repository entry. Example: `'style': 'mla'`
    * `tags_data()`: returns a list containing **tags**
3. These methods should be called with the following arguments:  
`zot.items_data(api_request, {URL parameters}, {additional request parameters})`
    * `URL parameters` is an optional dict containing valid Zotero API parameters.
        * Example: `{'limit': 2, 'start': 37}`
        * Valid keys: `'limit'` (integer, 1 – 99, default: 50), `'start'` (integer), `'order'` (string), `'sort'` (string: `'asc'` or `'desc'`)
    * `request parameters` is an optional dict containing values such as:  
        * `Item ID`. Example: `{'item': 'T4AH4RZA'}`
        * `Tag`. Example: `{'tag': 'James Joyce'}`
        * `Collection ID`. Example `{'collection': 'PRMD6BGB'}`
        * `Group ID`. Example: `{'group': 'DFW'}`
        * Several key/value pairs can be included in the dict 
        * If an API call requires a particular request parameter and you fail to include it, an error will be raised
        * Valid keys: `'item'`, `'tag'`, `'collection'`, `'group'`
4. If you wish to pass request parameters, but no URL parameters, pass them as a named argument:  
`zot.items_data(api_request, request_params = {request parameters})`
5. Alternatively, you can call `retrieve_data()` with the same arguments as above. This will return a 'raw' `feedparser` object, which you can iterate over and retrieve values from in any way you wish, e.g.:
    * item = `zot.retrieve_data('top_level_items', url params, request params)`
    * `print item.entries[0]['title']`
    * `print item.entries[0]['zapi_id']`
    * These values can then be fed back into subsequent calls to `retrieve_data()`


# Notes #

All currently available API calls have been implemented and documented (see below). Calling an API method which requires an optional parameter without specifying one will raise a `ParamNotPassed` error. **URL parameters will supersede API calls which should return e.g. a single item:** `https://api.zotero.org/users/436/items/ABC?start=50&limit=10` will return 10 items beginning at position 50, even though `ABC` does not exist. Be aware of this, and don't pass URL parameters which do not apply to a given API method.  
Running zotero.py from the command line will attempt to import your ID and key from a file named `zotero_keys.txt` in your home directory (see comment in `main()` for details), create a new Zotero object and call some of the methods.


# Currently Available API Calls #

### Additional required parameters are (specified inline) ###

#### For `items_data()`:

* `'all_items'`: returns the set of all items belonging to a specific user
* `'top_level_items'`: returns the set of all top-level items belonging to a specific user
* `'specific_item'` (`item ID`): returns a specific item belonging to a user.
* `'child_items'` (`item ID`): returns the set of all child items under a specific item
* `'items_for_tag'`(`tag`): returns the set of a user's items tagged with a specific tag
* `'group_items'` (`group ID`): returns the set of all items belonging to a specific group
* `'collection_items'` (`collection ID`): returns a set of items belonging to a specific collection belonging to a user
* `'top_group_items'` (`group ID`): returns the set of all top-level items belonging to a specific group
* `'group_item'` (`group ID`, `item ID`): returns a specific item belonging to a specific group
* `'group_user_items_tag'` (`group ID`, `item ID`): returns a set of items belonging to a specific group, tagged with a specific tag
* `'group_collection_items'` (`group ID`, `collection ID`): returns a set of items belonging to a specific collection belonging to a specific group
* `'group_collection_item'` (`group ID`, `collection ID`, `item ID`): returns a specific item belonging to a specific collection belonging to a specific group
* `'group_item_children'` (`group ID`, `item ID`): returns a set of all child items belonging to a specific item belonging to a group


#### For `collections_data()`: ####

* `'user_collections'`: returns the set of collections belonging to a specific user
* `'sub_collections'` (`collection ID`): returns a set of subcollections belonging to a collection for a specific user
* `'group_collections'` (`group ID`): returns a set of collections belonging to a specific group
* `'group_collection'` (`group ID`, `collection ID`): returns a specific collection belonging to a specific group
* `'group_collection_sub'` (`group ID`, `collection ID`): returns a set of subcollections within a specific collection belonging to a specific group


#### For `groups_data()`: ####

* `'user_groups'`: returns the set of all groups belonging to a specific user


#### For `tags_data()`: ####

* `'user_tags'` returns the set of all tags belonging to a specific user
* `'item_tags'` (`item ID`): returns the set of all tags associated with a specific item 
* `'group_item_tags'` (`group ID`, `item ID`): returns a set of all tags for a specific item belonging to a specific group
* `'group_tags'` (`'group ID'`): returns a set of all tags belonging to a specific group



[1]: http://www.zotero.org/support/dev/server_api "Zotero Server API"
[2]: http://www.zotero.org/settings/keys/new "New Zotero Access Credentials"
[3]: http://feedparser.org/ "Mark Pilgrim's Universal Feed Parser"
[4]: http://pypi.python.org/pypi/pip "Pip Installs Packages"
