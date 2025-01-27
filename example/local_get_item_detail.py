from pyzotero import zotero
from pprint import pprint

def get_item_detail(item_id):
    """
    Get detailed information about a specific Zotero item
    Args:
        item_id (str): Zotero item ID
    """
    # Initialize Zotero client with local=True
    zot = zotero.Zotero(library_id='000000', library_type='user', local=True)

    try:
        # Get the item
        item = zot.item(item_id)

        # Print basic information
        print("\nItem Details:")
        print("-" * 50)
        print(f"Item ID: {item['key']}")
        print(f"Item Type: {item['data'].get('itemType', 'Not specified')}")
        print(f"Title: {item['data'].get('title', 'No title')}")

        # If it's an attachment, show parent item
        if item['data'].get('parentItem'):
            try:
                parent = zot.item(item['data']['parentItem'])
                print("\nParent Item:")
                print(f"Parent ID: {parent['key']}")
                print(f"Parent Title: {parent['data'].get('title', 'No title')}")
            except Exception as e:
                print(f"Error getting parent item: {e!s}")

        # If it has child items (attachments), show them
        children = zot.children(item_id)
        if children:
            print("\nChild Items:")
            for child in children:
                print(f"- {child['data'].get('title', 'No title')} "
                      f"(ID: {child['key']}, "
                      f"Type: {child['data'].get('itemType', 'Unknown')})")

        # Show collections this item belongs to
        collections = item['data'].get('collections', [])
        if collections:
            print("\nCollections:")
            try:
                for coll_id in collections:
                    coll = zot.collection(coll_id)
                    print(f"- {coll['data'].get('name', 'Unnamed')} (ID: {coll_id})")
            except Exception as e:
                print(f"Error retrieving collections: {e!s}")

        # Show all metadata
        print("\nFull Metadata:")
        print("-" * 50)
        pprint(item['data'])

    except Exception as e:
        print(f"Error getting item details: {e!s}")
        return None
    else:
        return item

if __name__ == "__main__":
    # Example usage with a specific item ID
    item_id = 'K9V7JFXY'  # Replace with your item ID
    item_detail = get_item_detail(item_id)
