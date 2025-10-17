"""Command-line interface for pyzotero."""

import json
import sys

import click

from pyzotero import zotero


def _get_zotero_client(locale="en-US"):
    """Get a Zotero client configured for local access."""
    return zotero.Zotero(library_id="0", library_type="user", local=True, locale=locale)


@click.group()
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
    help="Enable full-text search (qmode='everything')",
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

        # Execute search using collection_items_top() if collection specified, otherwise top()
        if collection:
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
            click.echo(json.dumps(output_items, indent=2))
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


if __name__ == "__main__":
    main()
