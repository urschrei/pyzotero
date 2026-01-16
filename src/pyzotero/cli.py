"""Command-line interface for pyzotero."""

import json
import sys

import click  # ty:ignore[unresolved-import]
import httpx

from pyzotero import __version__, zotero
from pyzotero.semantic_scholar import (
    PaperNotFoundError,
    RateLimitError,
    SemanticScholarError,
    filter_by_citations,
    get_citations,
    get_recommendations,
    get_references,
    search_papers,
)
from pyzotero.zotero import chunks


def _get_zotero_client(locale="en-US"):
    """Get a Zotero client configured for local access."""
    return zotero.Zotero(library_id="0", library_type="user", local=True, locale=locale)


def _normalize_doi(doi):
    """Normalise a DOI for case-insensitive matching.

    Strips common prefixes (https://doi.org/, http://doi.org/, doi:) and converts to lowercase.
    DOIs are case-insensitive per the DOI specification.
    """
    if not doi:
        return ""

    # Strip whitespace
    doi = doi.strip()

    # Strip common prefixes
    prefixes = ["https://doi.org/", "http://doi.org/", "doi:"]
    for prefix in prefixes:
        if doi.lower().startswith(prefix.lower()):
            doi = doi[len(prefix) :]
            break

    # Convert to lowercase for case-insensitive matching
    return doi.lower().strip()


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


@main.command()
@click.argument("dois", nargs=-1)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output results as JSON",
)
@click.pass_context
def alldoi(ctx, dois, output_json):  # noqa: PLR0912
    """Look up DOIs in the local Zotero library and return their Zotero IDs.

    Accepts one or more DOIs as arguments and checks if they exist in the library.
    DOI matching is case-insensitive and handles common prefixes (https://doi.org/, doi:).

    If no DOIs are provided, shows "No items found" (text) or {} (JSON).

    Examples:
        pyzotero alldoi 10.1234/example

        pyzotero alldoi 10.1234/abc https://doi.org/10.5678/def doi:10.9012/ghi

        pyzotero alldoi 10.1234/example --json

    """
    try:
        locale = ctx.obj.get("locale", "en-US")
        zot = _get_zotero_client(locale)

        # Build a mapping of normalized DOIs to (original_doi, zotero_key)
        click.echo("Building DOI index from library...", err=True)
        doi_map = {}

        # Get all items using everything() which handles pagination automatically
        all_items = zot.everything(zot.items())

        # Process all items
        for item in all_items:
            data = item.get("data", {})
            item_doi = data.get("DOI", "")

            if item_doi:
                normalized_doi = _normalize_doi(item_doi)
                item_key = data.get("key", "")

                if normalized_doi and item_key:
                    # Store the original DOI from Zotero and the item key
                    doi_map[normalized_doi] = (item_doi, item_key)

        click.echo(f"Indexed {len(doi_map)} items with DOIs", err=True)

        # If no DOIs provided, return empty result
        if not dois:
            if output_json:
                click.echo(json.dumps({}))
            else:
                click.echo("No items found")
            return

        # Look up each input DOI
        found = []
        not_found = []

        for input_doi in dois:
            normalized_input = _normalize_doi(input_doi)

            if normalized_input in doi_map:
                original_doi, zotero_key = doi_map[normalized_input]
                found.append({"doi": original_doi, "key": zotero_key})
            else:
                not_found.append(input_doi)

        # Output results
        if output_json:
            result = {"found": found, "not_found": not_found}
            click.echo(json.dumps(result, indent=2))
        else:
            if found:
                click.echo(f"\nFound {len(found)} items:\n")
                for item in found:
                    click.echo(f"  {item['doi']} → {item['key']}")
            else:
                click.echo("No items found")

            if not_found:
                click.echo(f"\nNot found ({len(not_found)}):")
                for doi in not_found:
                    click.echo(f"  {doi}")

    except Exception as e:
        click.echo(f"Error: {e!s}", err=True)
        sys.exit(1)


def _build_doi_index(zot):
    """Build a mapping of normalised DOIs to Zotero item keys.

    Returns:
        Dict mapping normalised DOIs to item keys

    """
    doi_map = {}
    all_items = zot.everything(zot.items())

    for item in all_items:
        data = item.get("data", {})
        item_doi = data.get("DOI", "")

        if item_doi:
            normalised_doi = _normalize_doi(item_doi)
            item_key = data.get("key", "")

            if normalised_doi and item_key:
                doi_map[normalised_doi] = item_key

    return doi_map


def _format_s2_paper(paper, in_library=None):
    """Format a Semantic Scholar paper for output.

    Args:
        paper: Normalised paper dict from semantic_scholar module
        in_library: Boolean indicating if paper is in local Zotero

    Returns:
        Formatted dict for output

    """
    result = {
        "paperId": paper.get("paperId"),
        "doi": paper.get("doi"),
        "title": paper.get("title"),
        "authors": [a.get("name") for a in (paper.get("authors") or [])],
        "year": paper.get("year"),
        "venue": paper.get("venue"),
        "citationCount": paper.get("citationCount"),
        "referenceCount": paper.get("referenceCount"),
        "isOpenAccess": paper.get("isOpenAccess"),
        "openAccessPdfUrl": paper.get("openAccessPdfUrl"),
    }

    if in_library is not None:
        result["inLibrary"] = in_library

    return result


def _annotate_with_library(papers, doi_map):
    """Annotate papers with in_library status based on DOI matching.

    Args:
        papers: List of normalised paper dicts
        doi_map: Dict mapping normalised DOIs to Zotero item keys

    Returns:
        List of formatted paper dicts with inLibrary field

    """
    results = []
    for paper in papers:
        doi = paper.get("doi")
        in_library = False
        if doi:
            normalised = _normalize_doi(doi)
            in_library = normalised in doi_map
        results.append(_format_s2_paper(paper, in_library))
    return results


@main.command()
@click.option(
    "--doi",
    required=True,
    help="DOI of the paper to find related papers for",
)
@click.option(
    "--limit",
    type=int,
    default=20,
    help="Maximum number of results to return (default: 20, max: 500)",
)
@click.option(
    "--min-citations",
    type=int,
    default=0,
    help="Minimum citation count filter (default: 0)",
)
@click.option(
    "--check-library/--no-check-library",
    default=True,
    help="Check if papers exist in local Zotero (default: True)",
)
@click.pass_context
def related(ctx, doi, limit, min_citations, check_library):
    """Find papers related to a given paper using Semantic Scholar.

    Uses SPECTER2 embeddings to find semantically similar papers.

    Examples:
        pyzotero related --doi "10.1038/nature12373"

        pyzotero related --doi "10.1038/nature12373" --limit 50

        pyzotero related --doi "10.1038/nature12373" --min-citations 100

    """
    try:
        # Get recommendations from Semantic Scholar
        click.echo(f"Fetching related papers for DOI: {doi}...", err=True)
        result = get_recommendations(doi, id_type="doi", limit=limit)
        papers = result.get("papers", [])

        # Apply citation filter
        if min_citations > 0:
            papers = filter_by_citations(papers, min_citations)

        if not papers:
            click.echo(json.dumps({"count": 0, "papers": []}))
            return

        # Optionally annotate with library status
        if check_library:
            click.echo("Checking local Zotero library...", err=True)
            locale = ctx.obj.get("locale", "en-US")
            zot = _get_zotero_client(locale)
            doi_map = _build_doi_index(zot)
            output_papers = _annotate_with_library(papers, doi_map)
        else:
            output_papers = [_format_s2_paper(p) for p in papers]

        click.echo(
            json.dumps({"count": len(output_papers), "papers": output_papers}, indent=2)
        )

    except PaperNotFoundError:
        click.echo("Error: Paper not found in Semantic Scholar.", err=True)
        sys.exit(1)
    except RateLimitError:
        click.echo("Error: Rate limit exceeded. Please wait and try again.", err=True)
        sys.exit(1)
    except SemanticScholarError as e:
        click.echo(f"Error: {e!s}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e!s}", err=True)
        sys.exit(1)


@main.command()
@click.option(
    "--doi",
    required=True,
    help="DOI of the paper to find citations for",
)
@click.option(
    "--limit",
    type=int,
    default=100,
    help="Maximum number of results to return (default: 100, max: 1000)",
)
@click.option(
    "--min-citations",
    type=int,
    default=0,
    help="Minimum citation count filter (default: 0)",
)
@click.option(
    "--check-library/--no-check-library",
    default=True,
    help="Check if papers exist in local Zotero (default: True)",
)
@click.pass_context
def citations(ctx, doi, limit, min_citations, check_library):
    """Find papers that cite a given paper using Semantic Scholar.

    Examples:
        pyzotero citations --doi "10.1038/nature12373"

        pyzotero citations --doi "10.1038/nature12373" --limit 50

        pyzotero citations --doi "10.1038/nature12373" --min-citations 50

    """
    try:
        # Get citations from Semantic Scholar
        click.echo(f"Fetching citations for DOI: {doi}...", err=True)
        result = get_citations(doi, id_type="doi", limit=limit)
        papers = result.get("papers", [])

        # Apply citation filter
        if min_citations > 0:
            papers = filter_by_citations(papers, min_citations)

        if not papers:
            click.echo(json.dumps({"count": 0, "papers": []}))
            return

        # Optionally annotate with library status
        if check_library:
            click.echo("Checking local Zotero library...", err=True)
            locale = ctx.obj.get("locale", "en-US")
            zot = _get_zotero_client(locale)
            doi_map = _build_doi_index(zot)
            output_papers = _annotate_with_library(papers, doi_map)
        else:
            output_papers = [_format_s2_paper(p) for p in papers]

        click.echo(
            json.dumps({"count": len(output_papers), "papers": output_papers}, indent=2)
        )

    except PaperNotFoundError:
        click.echo("Error: Paper not found in Semantic Scholar.", err=True)
        sys.exit(1)
    except RateLimitError:
        click.echo("Error: Rate limit exceeded. Please wait and try again.", err=True)
        sys.exit(1)
    except SemanticScholarError as e:
        click.echo(f"Error: {e!s}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e!s}", err=True)
        sys.exit(1)


@main.command()
@click.option(
    "--doi",
    required=True,
    help="DOI of the paper to find references for",
)
@click.option(
    "--limit",
    type=int,
    default=100,
    help="Maximum number of results to return (default: 100, max: 1000)",
)
@click.option(
    "--min-citations",
    type=int,
    default=0,
    help="Minimum citation count filter (default: 0)",
)
@click.option(
    "--check-library/--no-check-library",
    default=True,
    help="Check if papers exist in local Zotero (default: True)",
)
@click.pass_context
def references(ctx, doi, limit, min_citations, check_library):
    """Find papers referenced by a given paper using Semantic Scholar.

    Examples:
        pyzotero references --doi "10.1038/nature12373"

        pyzotero references --doi "10.1038/nature12373" --limit 50

        pyzotero references --doi "10.1038/nature12373" --min-citations 100

    """
    try:
        # Get references from Semantic Scholar
        click.echo(f"Fetching references for DOI: {doi}...", err=True)
        result = get_references(doi, id_type="doi", limit=limit)
        papers = result.get("papers", [])

        # Apply citation filter
        if min_citations > 0:
            papers = filter_by_citations(papers, min_citations)

        if not papers:
            click.echo(json.dumps({"count": 0, "papers": []}))
            return

        # Optionally annotate with library status
        if check_library:
            click.echo("Checking local Zotero library...", err=True)
            locale = ctx.obj.get("locale", "en-US")
            zot = _get_zotero_client(locale)
            doi_map = _build_doi_index(zot)
            output_papers = _annotate_with_library(papers, doi_map)
        else:
            output_papers = [_format_s2_paper(p) for p in papers]

        click.echo(
            json.dumps({"count": len(output_papers), "papers": output_papers}, indent=2)
        )

    except PaperNotFoundError:
        click.echo("Error: Paper not found in Semantic Scholar.", err=True)
        sys.exit(1)
    except RateLimitError:
        click.echo("Error: Rate limit exceeded. Please wait and try again.", err=True)
        sys.exit(1)
    except SemanticScholarError as e:
        click.echo(f"Error: {e!s}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e!s}", err=True)
        sys.exit(1)


@main.command()
@click.option(
    "-q",
    "--query",
    required=True,
    help="Search query string",
)
@click.option(
    "--limit",
    type=int,
    default=20,
    help="Maximum number of results to return (default: 20, max: 100)",
)
@click.option(
    "--year",
    help="Year filter (e.g., '2020', '2018-2022', '2020-')",
)
@click.option(
    "--open-access/--no-open-access",
    default=False,
    help="Only return open access papers (default: False)",
)
@click.option(
    "--sort",
    type=click.Choice(["citations", "year"], case_sensitive=False),
    help="Sort results by citation count or year (descending)",
)
@click.option(
    "--min-citations",
    type=int,
    default=0,
    help="Minimum citation count filter (default: 0)",
)
@click.option(
    "--check-library/--no-check-library",
    default=True,
    help="Check if papers exist in local Zotero (default: True)",
)
@click.pass_context
def s2search(ctx, query, limit, year, open_access, sort, min_citations, check_library):
    """Search for papers on Semantic Scholar.

    Search across Semantic Scholar's index of over 200M papers.

    Examples:
        pyzotero s2search -q "climate adaptation"

        pyzotero s2search -q "machine learning" --year 2020-2024

        pyzotero s2search -q "neural networks" --open-access --limit 50

        pyzotero s2search -q "deep learning" --sort citations --min-citations 100

    """
    try:
        # Search Semantic Scholar
        click.echo(f'Searching Semantic Scholar for: "{query}"...', err=True)
        result = search_papers(
            query,
            limit=limit,
            year=year,
            open_access_only=open_access,
            sort=sort,
            min_citations=min_citations,
        )
        papers = result.get("papers", [])
        total = result.get("total", len(papers))

        if not papers:
            click.echo(json.dumps({"count": 0, "total": total, "papers": []}))
            return

        # Optionally annotate with library status
        if check_library:
            click.echo("Checking local Zotero library...", err=True)
            locale = ctx.obj.get("locale", "en-US")
            zot = _get_zotero_client(locale)
            doi_map = _build_doi_index(zot)
            output_papers = _annotate_with_library(papers, doi_map)
        else:
            output_papers = [_format_s2_paper(p) for p in papers]

        click.echo(
            json.dumps(
                {"count": len(output_papers), "total": total, "papers": output_papers},
                indent=2,
            )
        )

    except RateLimitError:
        click.echo("Error: Rate limit exceeded. Please wait and try again.", err=True)
        sys.exit(1)
    except SemanticScholarError as e:
        click.echo(f"Error: {e!s}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e!s}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
