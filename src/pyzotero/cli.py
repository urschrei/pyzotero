"""Command-line interface for pyzotero."""

import json
import sys

import click
import httpx

from pyzotero import __version__, zotero
from pyzotero.zotero import chunks


def _get_zotero_client(locale="en-US"):
    """Get a Zotero client configured for local access."""
    return zotero.Zotero(library_id="0", library_type="user", local=True, locale=locale)


@click.group()
@click.version_option(version=__version__, prog_name="pyzotero")
@click.option(
    "--locale",
    default="en-US",
    help="Locale for localized strings (default: en-US)",
)
@click.pass_context
def main(ctx, locale):
    """Search local Zotero library."""
    ctx.ensure_object(dict)
    ctx.obj["locale"] = locale


@main.command()
@click.option(
    "-q",
    "--query",
    help="Search query string",
    default="",
)
@click.option(
    "--fulltext",
    is_flag=True,
    help="Search full-text content including PDFs. Retrieves parent items when attachments match.",
)
@click.option(
    "--itemtype",
    multiple=True,
    help="Filter by item type (can be specified multiple times for OR search)",
)
@click.option(
    "--collection",
    help="Filter by collection key (returns only items in this collection)",
)
@click.option(
    "--limit",
    type=int,
    default=1000000,
    help="Maximum number of results to return (default: 1000000)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output results as JSON",
)
@click.pass_context
def search(ctx, query, fulltext, itemtype, collection, limit, output_json):  # noqa: PLR0912, PLR0915
    """Search local Zotero library.

    By default, searches top-level items in titles and metadata.

    When --fulltext is enabled, searches all items including attachment content
    (PDFs, documents, etc.). If a match is found in an attachment, the parent
    bibliographic item is retrieved and included in results.

    Examples:
        pyzotero search -q "machine learning"

        pyzotero search -q "climate change" --fulltext

        pyzotero search -q "methodology" --itemtype book --itemtype journalArticle

        pyzotero search --collection ABC123 -q "test"

        pyzotero search -q "climate" --json

    """
    try:
        locale = ctx.obj.get("locale", "en-US")
        zot = _get_zotero_client(locale)

        # Build query parameters
        params = {"limit": limit}

        if query:
            params["q"] = query

        if fulltext:
            params["qmode"] = "everything"

        if itemtype:
            # Join multiple item types with || for OR search
            params["itemType"] = " || ".join(itemtype)

        # Execute search
        # When fulltext is enabled, use items() or collection_items() to get both
        # top-level items and attachments. Otherwise use top() or collection_items_top()
        # to only get top-level items.
        if fulltext:
            if collection:
                results = zot.collection_items(collection, **params)
            else:
                results = zot.items(**params)

            # When using fulltext, we need to retrieve parent items for any attachments
            # that matched, since most full-text content comes from PDFs and other attachments
            top_level_items = []
            attachment_items = []

            for item in results:
                data = item.get("data", {})
                if "parentItem" in data:
                    attachment_items.append(item)
                else:
                    top_level_items.append(item)

            # Retrieve parent items for attachments in batches of 50
            parent_items = []
            if attachment_items:
                parent_ids = list(
                    {item["data"]["parentItem"] for item in attachment_items}
                )
                for chunk in chunks(parent_ids, 50):
                    parent_items.extend(zot.get_subset(chunk))

            # Combine top-level items and parent items, removing duplicates by key
            all_items = top_level_items + parent_items
            items_dict = {item["data"]["key"]: item for item in all_items}
            results = list(items_dict.values())
        # Non-fulltext search: use top() or collection_items_top() as before
        elif collection:
            results = zot.collection_items_top(collection, **params)
        else:
            results = zot.top(**params)

        # Handle empty results
        if not results:
            if output_json:
                click.echo(json.dumps([]))
            else:
                click.echo("No results found.")
            return

        # Build output data structure
        output_items = []
        for item in results:
            data = item.get("data", {})

            title = data.get("title", "No title")
            item_type = data.get("itemType", "Unknown")
            date = data.get("date", "No date")
            item_key = data.get("key", "")
            publication = data.get("publicationTitle", "")
            volume = data.get("volume", "")
            issue = data.get("issue", "")
            doi = data.get("DOI", "")
            url = data.get("url", "")

            # Format creators (authors, editors, etc.)
            creators = data.get("creators", [])
            creator_names = []
            for creator in creators:
                if "lastName" in creator:
                    if "firstName" in creator:
                        creator_names.append(
                            f"{creator['firstName']} {creator['lastName']}"
                        )
                    else:
                        creator_names.append(creator["lastName"])
                elif "name" in creator:
                    creator_names.append(creator["name"])

            # Check for PDF attachments
            pdf_attachments = []
            num_children = item.get("meta", {}).get("numChildren", 0)
            if num_children > 0:
                children = zot.children(item_key)
                for child in children:
                    child_data = child.get("data", {})
                    if child_data.get("contentType") == "application/pdf":
                        # Extract file URL from links.enclosure.href
                        file_url = (
                            child.get("links", {}).get("enclosure", {}).get("href", "")
                        )
                        if file_url:
                            pdf_attachments.append(file_url)

            # Build item object for JSON output
            item_obj = {
                "key": item_key,
                "itemType": item_type,
                "title": title,
                "creators": creator_names,
                "date": date,
                "publication": publication,
                "volume": volume,
                "issue": issue,
                "doi": doi,
                "url": url,
                "pdfAttachments": pdf_attachments,
            }
            output_items.append(item_obj)

        # Output results
        if output_json:
            click.echo(
                json.dumps(
                    {"count": len(output_items), "items": output_items}, indent=2
                )
            )
        else:
            click.echo(f"\nFound {len(results)} items:\n")
            for idx, item_obj in enumerate(output_items, 1):
                authors_str = (
                    ", ".join(item_obj["creators"])
                    if item_obj["creators"]
                    else "No authors"
                )

                click.echo(f"{idx}. [{item_obj['itemType']}] {item_obj['title']}")
                click.echo(f"   Authors: {authors_str}")
                click.echo(f"   Date: {item_obj['date']}")
                click.echo(f"   Publication: {item_obj['publication']}")
                click.echo(f"   Volume: {item_obj['volume']}")
                click.echo(f"   Issue: {item_obj['issue']}")
                click.echo(f"   DOI: {item_obj['doi']}")
                click.echo(f"   URL: {item_obj['url']}")
                click.echo(f"   Key: {item_obj['key']}")

                if item_obj["pdfAttachments"]:
                    click.echo("   PDF Attachments:")
                    for pdf_url in item_obj["pdfAttachments"]:
                        click.echo(f"      {pdf_url}")

                click.echo()

    except Exception as e:
        click.echo(f"Error: {e!s}", err=True)
        sys.exit(1)


@main.command()
@click.option(
    "--limit",
    type=int,
    help="Maximum number of collections to return (default: all)",
)
@click.pass_context
def listcollections(ctx, limit):
    """List all collections in the local Zotero library.

    Examples:
        pyzotero listcollections

        pyzotero listcollections --limit 10

    """
    try:
        locale = ctx.obj.get("locale", "en-US")
        zot = _get_zotero_client(locale)

        # Build query parameters
        params = {}
        if limit:
            params["limit"] = limit

        # Get all collections
        collections = zot.collections(**params)

        if not collections:
            click.echo(json.dumps([]))
            return

        # Build a mapping of collection keys to names for parent lookup
        collection_map = {}
        for collection in collections:
            data = collection.get("data", {})
            key = data.get("key", "")
            name = data.get("name", "")
            if key:
                collection_map[key] = name if name else None

        # Build JSON output
        output = []
        for collection in collections:
            data = collection.get("data", {})
            meta = collection.get("meta", {})

            name = data.get("name", "")
            key = data.get("key", "")
            num_items = meta.get("numItems", 0)
            parent_collection = data.get("parentCollection", "")

            collection_obj = {
                "id": key,
                "name": name if name else None,
                "items": num_items,
            }

            # Add parent information if it exists
            if parent_collection:
                parent_name = collection_map.get(parent_collection)
                collection_obj["parent"] = {
                    "id": parent_collection,
                    "name": parent_name,
                }
            else:
                collection_obj["parent"] = None

            output.append(collection_obj)

        # Output as JSON
        click.echo(json.dumps(output, indent=2))

    except Exception as e:
        click.echo(f"Error: {e!s}", err=True)
        sys.exit(1)


@main.command()
@click.pass_context
def itemtypes(ctx):
    """List all valid item types.

    Examples:
        pyzotero itemtypes

    """
    try:
        locale = ctx.obj.get("locale", "en-US")
        zot = _get_zotero_client(locale)

        # Get all item types
        item_types = zot.item_types()

        if not item_types:
            click.echo(json.dumps([]))
            return

        # Output as JSON array
        click.echo(json.dumps(item_types, indent=2))

    except Exception as e:
        click.echo(f"Error: {e!s}", err=True)
        sys.exit(1)


@main.command()
@click.pass_context
def test(ctx):
    """Test connection to local Zotero instance.

    This command checks whether Zotero is running and accepting local connections.

    Examples:
        pyzotero test

    """
    try:
        locale = ctx.obj.get("locale", "en-US")
        zot = _get_zotero_client(locale)

        # Call settings() to test the connection
        # This should return {} if Zotero is running and listening
        result = zot.settings()

        # If we get here, the connection succeeded
        click.echo("✓ Connection successful: Zotero is running and listening locally.")
        if result == {}:
            click.echo("  Received expected empty settings response.")
        else:
            click.echo(f"  Received response: {json.dumps(result)}")

    except httpx.ConnectError:
        click.echo(
            "✗ Connection failed: Could not connect to Zotero.\n\n"
            "Possible causes:\n"
            "  • Zotero might not be running\n"
            "  • Local connections might not be enabled\n\n"
            "To enable local connections:\n"
            "  Zotero > Settings > Advanced > Allow other applications on this computer to communicate with Zotero",
            err=True,
        )
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e!s}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
