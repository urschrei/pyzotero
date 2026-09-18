from pyzotero import zotero

def get_item_notes(zot, item_id):
    """Get notes for a specific item

    Args:
        zot: Zotero instance
        item_id: ID of the Zotero item

    Returns:
        List of notes (as dicts) for the item

    """
    children = zot.children(item_id)
    notes = [child for child in children if child['data']['itemType'] == 'note']
    return notes

# Example usage
if __name__ == "__main__":
    # Initialize Zotero
    zot = zotero.Zotero(library_id='000000', library_type='user', local=True)

    # Get notes by item id, this item must have notes
    item_id = 'H62SJYVX'
    notes = get_item_notes(zot, item_id)
    print(notes)

