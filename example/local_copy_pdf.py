from pyzotero import zotero
from pathlib import Path

def copy_specific_pdf(item_id, output_dir, new_name=None):
    """
    Copy a specific PDF attachment from Zotero library to specified folder using dump()

    Args:
        item_id (str): Zotero item ID
        output_dir (str): Path to output directory
        new_name (str, optional): New filename for the PDF. If None, uses original name

    """
    # Initialize Zotero client with local=True
    zot = zotero.Zotero(library_id='000000', library_type='user', local=True)

    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        # Get the item metadata first
        item = zot.item(item_id)

        try:
            # Get original filename or use default
            default_filename = f"{item_id}.pdf"
            original_filename = item['data'].get('filename', default_filename)

            # Use new_name if provided, otherwise use original filename
            filename = new_name if new_name else original_filename

            # Add .pdf extension if not present
            if not filename.lower().endswith('.pdf'):
                filename += '.pdf'

            # Use dump() with explicit filename
            full_path = zot.dump(
                item_id,
                filename=filename,
                path=str(output_path)
            )

            print(f"\nSuccessfully copied file to: {full_path}")
            print(f"Title: {item['data'].get('title', 'No title')}")

        except Exception as e:
            print(f"Error copying file: {e!s}")
            print(f"Item data: {item['data']}")  # Debug info

    except Exception as e:
        print(f"Error accessing Zotero item: {e!s}")

if __name__ == "__main__":
    # Example usage with specific item ID
    item_id = '8M9FYC2W'
    data_dir = "./example/data/pdfs"

    # Example 1: Copy with new name
    copy_specific_pdf(item_id, data_dir, new_name="my_paper")

    # Example 2: Copy with original filename
    copy_specific_pdf(item_id, data_dir)
