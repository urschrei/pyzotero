# Description #

Because it's 2011, and I have no intention of using PHP for anything, let alone writing it, this is a first pass at implementing a Python wrapper for the [Zotero API][1]. There's no use case as yet, since I'm not sure what's going to be the ultimate consumer of the returned data. Expect a lot of initial fragility, if not outright breakage. You'll require a user ID and possibly an access key, which can be set up [here][2].

# Usage #

1. Create a new Zotero object:  
`zot = Zotero(user_id, user_key)`  
2. Call the object's `retrieve_data()` method:  
`item = zot.retrieve_data(api_request, [{URL parameters}], [{additional request parameters}])`  
    * `URL parameters` is an optional dict containing valid Zotero API parameters. Example: `{'limit': 2, 'start': 37}`  
    * `request parameters` is an optional dict containing values such as:  
        * `Item ID`  
        * `Tag` (literal)  
        * `Collection ID`  
        * `Group ID`. Example: `{'item': 'T4AH4RZA'}`  
        * Several key/value pairs can be included in the dict. If an API call requires a particular request parameter and you fail to include it, an error will be raised
        * Valid keys: `'item'`, `'tag'`, `'collection'`, `'group'`
3. You can now iterate through `item`'s entries and retrieve values in any way you wish, e.g.:  
    * `item.entries[0]['title']`  
    * `item.entries[0]['zapi_id']`  
    These values can then be fed back into subsequent calls to `retrieve_data` 
4. If you wish to pass request parameters, but no URL parameters, pass an empty dict: `retrieve_data(api_request, {}, {request parameters})`  
5. The main() function contains an example, passing the 'All Items' method with URL parameters which restrict the result set
6. In addition, there exist the `item_data()`, `gen_item_data()` and `collections_data()` functions: they take the result of `retrieve_data` (a `feedparser` dict), and return a list containing one or more dicts which contain the item data (type, creator, url, ISSN, ID, title &c.), which represents the bulk of the usefulness of Zotero (and thus, of this endeavour). `item_data` can be used to parse the result of any API call which returns **items**. `collections_data()` can be used to parse the result of any API call which returns **collections**. `gen_item_data()` returns identical data to `item_data()`, but in the form of a generator object
7. The dicts returned by the above functions do not consistently contain the same values; depending on the Zotero item data, various fields may be present or missing. You should not depend upon the existence of a returned key/value pair for a given item, but check for its existence before any further processing
8. The `Zotero` object also has a `total_items()` method, which returns a count of all items in the library of the specified user ID

# Notes #

All currently available API calls have been implemented and documented (see below). Calling an API method which requires an optional parameter without specifying one will cause the call to fail with a `400: Bad Request` error. **URL parameters will supersede API calls which should return e.g. a single item:** `https://api.zotero.org/users/436/items/ABC?start=50&limit=10` will return 10 items beginning at position 50, even though `ABC` does not exist. Be aware of this, and don't pass URL parameters which do not apply to a given API method.


# Currently Available API Calls #

### Additional required parameters are (specified inline) ###


* `'all_items'`: returns the set of all items belonging to a specific user
* `'top_level_items'`: returns the set of all top-level items belonging to a specific user
* `'specific_item'` (`item ID`): returns a specific item belonging to a user.
* `'child_items'` (`item ID`): returns the set of all child items under a specific item 
* `'item_tags'` (`item ID`): returns the set of all tags associated with a specific item
* `'user_tags'`: returns the set of all tags belonging to a specific user
* `'items_for_tag'`(`tag`): returns the set of a user's items tagged with a specific tag
* `'collections'`: returns the set of collections belonging to a specific user
* `'collection_items'` (`collection ID`): returns a specific collection belonging to a user
* `'sub_collections'` (`collection ID`): returns a set of subcollections belonging to a collection for a specific user
* `'user_groups'`: returns the set of all groups belonging to a specific user
* `'group_items'` (`group ID`): returns the set of all items belonging to a specific group
* `'top_group_items'` (`group ID`): returns the set of all top-level items belonging to a specific group
* `'group_item'` (`group ID`, `item ID`): returns a specific item belonging to a specific group
* `'group_item_children'` (`group ID`, `item ID`): returns a set of all child items belonging to a specific item belonging to a group
* `'group_item_tags'` (`group ID`, `item ID`): returns a set of all tags associated with a specific item belonging to a group
* `'group_tags'`: (`'group ID'`): returns a set of all tags belonging to a specific group
* `'group_user_items_tag'` (`group ID`, `item ID`): returns a set of items belonging to a group, tagged with a specific tag
* `'group_collections'` (`group ID`): returns a set of collections belonging to a specific group
* `'group_collection'` (`group ID`, `collection ID`): returns a specific collection belonging to a specific group
* `'group_collection_sub'` (`group ID`, `collection ID`): returns a set of subcollections within a specific collection belonging to a specific group
* `'group_collection_items'` (`group ID`, `collection ID`): returns a set of items belonging to a specific collection belonging to a specific group
* `'group_collection_item'` (`group ID`, `item ID`): returns a specific item belonging to a specific collection belonging to a specific group


[1]: http://www.zotero.org/support/dev/server_api "Zotero Server API"
[2]: http://www.zotero.org/settings/keys/new "New Zotero Access Credentials"