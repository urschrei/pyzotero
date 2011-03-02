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
        * `Tag ID`  
        * `Collection ID`  
        * `Group ID`. Example: `{'item': 'T4AH4RZA'}`  
        * Several key/value pairs can be included in the dict. If an API call requires a particular request parameter and you fail to include it, an error will be raised.
        * Valid keys: `'item'`, `'tag'`, `'collection'`, `'group'`
3. You can now iterate through `item`'s entries and retrieve values in any way you wish, e.g.:  
    * `item.entries[0]['title']`  
    * `item.entries[0]['zapi_id']`  
    These values can then be fed back into subsequent calls to `retrieve_data` 
4. If you wish to pass request parameters, but no URL parameters, pass an empty dict: `retrieve_data(api_request, {}, {request parameters})`  
5. The main() function contains an example, passing the 'All Items' method with URL parameters which restrict the result set
6. In addition, there exists the `useful_item_data()` function: it takes the result of `retrieve_data` (a `feedparser` dict), and returns a list containing one or more dicts which contain the item data (type, creator, url, ISSN &c.), which represents the bulk of the usefulness of Zotero (and thus, of this endeavour). It can be used to parse the result of any API call which returns **items**. Similar functions for tags and collections are forthcoming.
7. The dicts returned by `useful_item_data()` do not consistently contain the same values; depending on the Zotero item data, various fields may be present or missing. You should not depend upon the existence of a returned key/value pair for a given item, but check for its existence before any further processing.


# Notes #

Not all API methods have been implemented yet (I've implemented the ten I thought would be most useful). Those which are currently available can be found in the `self.api_methods` dict, which is created along with each new Zotero instance, and are descriptively titled, which should make it obvious if any additional request parameters (item ID, group ID &c) are required. Calling an API method which requires an optional parameter without specifying one will cause the call to fail with a `400: Bad Request` error. **URL parameters will supersede API calls which should return e.g. a single item:** `https://api.zotero.org/users/436/items/ABC?start=50&limit=10` will return 10 items beginning at position 50, even though `ABC` does not exist. Be aware of this, and don't pass URL parameters which do not apply to a given API method.

There's no error handling yet.


[1]: http://www.zotero.org/support/dev/server_api "Zotero Server API"
[2]: http://www.zotero.org/settings/keys/new "New Zotero Access Credentials"