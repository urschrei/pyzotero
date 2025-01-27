from pyzotero import zotero
zot = zotero.Zotero(library_id='000000', library_type = 'user', local=True) # local=True for read access to local Zotero
items = zot.top(limit=5)
# we've retrieved the latest five top-level items in our library
# we can print each item's item type and ID
for item in items:
    print('Item: %s | Key: %s' % (item['data']['itemType'], item['data']['key']))