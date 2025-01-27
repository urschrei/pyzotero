from pyzotero import zotero

def search_by_title(title_query):
    """
    Search Zotero items by title
    Args:
        title_query (str): The title or part of title to search for
    Returns:
        list: List of matching items
    """
    # Initialize Zotero client with local=True
    zot = zotero.Zotero(library_id='000000', library_type='user', local=True)

    try:
        # Search for items where title contains the query string
        results = zot.items(q=title_query)

        # Print results
        print(f"\nFound {len(results)} items matching '{title_query}':")
        for item in results:
            # Get the item data
            title = item['data'].get('title', 'No title')
            item_type = item['data'].get('itemType', 'Unknown type')
            date = item['data'].get('date', 'No date')
            item_id = item['data'].get('key', 'No ID')

            print("\n##########################")
            print(f"ID: {item_id}")
            print(f"Title: {title}")
            print(f"Type: {item_type}")
            print(f"Date: {date}")
            print("##########################\n")

    except Exception as e:
        print(f"Error searching Zotero: {e!s}")
        return []
    else:
        return results

if __name__ == "__main__":
    # Example usage
    search_query = "uORFs"  # Change this to your search term
    search_by_title(search_query)
