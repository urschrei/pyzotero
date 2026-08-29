[![Supported Python versions](https://img.shields.io/pypi/pyversions/Pyzotero.svg?style=flat)](https://pypi.python.org/pypi/Pyzotero/) [![Docs](https://readthedocs.org/projects/pyzotero/badge/?version=latest)](http://pyzotero.readthedocs.org/en/latest/?badge=latest) [![PyPI Version](https://img.shields.io/pypi/v/Pyzotero.svg)](https://pypi.python.org/pypi/Pyzotero) [![Anaconda-Server Badge](https://anaconda.org/conda-forge/pyzotero/badges/version.svg)](https://anaconda.org/conda-forge/pyzotero) [![Downloads](https://pepy.tech/badge/pyzotero)](https://pepy.tech/project/pyzotero)

# Pyzotero: An API Client for the Zotero API

# Quickstart

1. `uv add pyzotero` **or** `pip install pyzotero` **or** `conda install conda-forge::pyzotero`
2. You'll need the ID of the personal or group library you want to access:
    - Your **personal library ID** is available [here](https://www.zotero.org/settings/keys), in the section `Your userID for use in API calls`
    - For **group libraries**, the ID can be found by opening the group's page: `https://www.zotero.org/groups/groupname`, and hovering over the `group settings` link. The ID is the integer after `/groups/`
3. You'll also need<sup>†</sup> to get an **API key** [here][2]
4. Are you accessing your own Zotero library? `library_type` is `'user'`
5. Are you accessing a shared group library? `library_type` is `'group'`.

Then:

``` python
from pyzotero import Zotero

zot = Zotero(
    library_id, library_type, api_key
)  # local=True to use a running Zotero instead of the web API
items = zot.top(limit=5)
# we've retrieved the latest five top-level items in our library
# we can print each item's item type and ID
for item in items:
    print(f"Item: {item['data']['itemType']} | Key: {item['data']['key']}")
```

# Documentation

Full documentation of available Pyzotero methods, code examples, and sample output is available on [Read The Docs][3].

# Local Zotero API

Passing `local=True` directs Pyzotero at a running Zotero installation instead of the web API. Reads need no authentication. Writes need the user's consent, given through a dialog in Zotero, and a Zotero version that supports local writes.

## Using the local API

1. In Zotero, enable Settings > Advanced > "Allow other applications on this computer to communicate with Zotero".
2. Create a client with `local=True`. You can now read from the library.
3. To write, call `authorize_local()` first, and approve the dialog Zotero displays:

``` python
from pyzotero import Zotero

zot = Zotero("0", "user", local=True)
auth = zot.authorize_local("My Application")  # Zotero prompts the user
zot.create_items([item])
```

## How local write access works

`authorize_local()` returns a dict with a `key` and a `remember` flag. A key granted with "Allow" is single-use: the first successful write consumes it. A key granted with "Always Allow" has `remember` set to `True`; you can store it and pass it back on a later run as the `local_api_key` argument.

Versions reported by the local API are unrelated to web API versions, and are typically lower than those the local API reported before write support was added. They are scoped to `zot.server_id`, which identifies the Zotero instance. A program that persists local objects or versions must persist that ID alongside them and partition by it. See the [documentation][3] for a full explanation, more how-to guides, and reference material.

# Installation

* Using [uv][11]: `uv add pyzotero`
* Using [pip][10]: `pip install pyzotero`
* Using Anaconda: `conda install conda-forge::pyzotero`

Pyzotero also provides an optional [CLI](#command-line-interface) and [MCP server](#mcp-server) for working with a local Zotero library. Both require Zotero 7 with local API access enabled: Zotero > Settings > Advanced > "Allow other applications on this computer to communicate with Zotero". Both are read-only unless you run `pyzotero authorize`, which stores a local API key. With that key, the CLI's collection commands can write, and the MCP server can write if started with `--enable-writes`. Both console scripts are installed whichever extra you choose; one whose extra is missing exits with a message naming the extra to install.

# Command-Line Interface

Pyzotero includes an optional CLI for searching and querying your local Zotero library, and for managing its collections.

## Installing the CLI

* Using [uv][11]: `uv add "pyzotero[cli]"`
* Using [pip][10]: `pip install "pyzotero[cli]"`

Or run it directly without installing:

* Using [uvx][11]: `uvx --from "pyzotero[cli]" pyzotero search -q "your query"`
* Using [pipx][10]: `pipx run --spec "pyzotero[cli]" pyzotero search -q "your query"`

## Usage

```bash
# Search for top-level items
pyzotero search -q "machine learning"

# Search with full-text mode
pyzotero search -q "climate change" --fulltext

# Filter by item type
pyzotero search -q "methodology" --itemtype book --itemtype journalArticle

# Search for top-level items within a collection
pyzotero search --collection ABC123 -q "test"

# Output as JSON for machine processing
pyzotero search -q "climate" --json

# List all collections
pyzotero listcollections

# List available item types
pyzotero itemtypes

# Obtain and store a local API key, which permits writes from the CLI and the MCP server
pyzotero authorize --app-name "Claude Desktop"

# Create a collection, nested under an existing one
pyzotero createcollection "Frankenstein Cities" --parent FD9AUNP2

# Add items to, remove items from, or move items between collections
pyzotero addtocollection FD9AUNP2 ABC123 DEF456
pyzotero removefromcollection FD9AUNP2 ABC123
pyzotero movetocollection --from FD9AUNP2 --to X7Y8Z9W0 ABC123 DEF456
```

## Collection Commands

`createcollection`, `addtocollection`, `removefromcollection` and `movetocollection` write to your library. They need a stored local API key: run `pyzotero authorize` once and choose "Always Allow". Without a key, they exit with a message that says so. Each accepts `--json` and reports the keys it touched. The membership commands change items one at a time; if one fails, the error names the item and lists the items already changed, so that you can resume from there. `movetocollection` changes each item in one request, so an item's membership of other collections is kept.

## Search Behaviour

By default, `pyzotero search` searches only top-level item titles and metadata fields.

When the `--fulltext` flag is used, the search expands to include all full-text indexed content, including PDFs and other attachments. Since most full-text content comes from PDF attachments rather than top-level items, the CLI automatically retrieves the parent bibliographic items for any matching attachments. This ensures you receive useful bibliographic records (journal articles, books, etc.) rather than raw attachment items.

## Output Format

By default, the CLI outputs human-readable text with a subset of metadata including:
- Title, authors, date, publication
- Volume, issue, DOI, URL
- PDF attachments (with local file paths)

Use the `--json` flag to output structured JSON.

# MCP Server

Pyzotero includes an optional [MCP](https://modelcontextprotocol.io) server that exposes your local Zotero library and Semantic Scholar integration as tools for LLMs. This lets sandboxed applications such as Claude Desktop access your Zotero library without needing direct CLI access.

## Installing the MCP server

* Using [uv][11]: `uv add "pyzotero[mcp]"`
* Using [pip][10]: `pip install "pyzotero[mcp]"`
* As a standalone tool: `uv tool install "pyzotero[mcp]"`
* CLI and MCP server together: `uv tool install "pyzotero[cli,mcp]"`

## Claude Desktop Configuration

Add the following to your Claude Desktop configuration file:

If `pyzotero-mcp` is installed:

```json
{
  "mcpServers": {
    "zotero": {
      "command": "pyzotero-mcp"
    }
  }
}
```

Or, without installing, using uvx:

```json
{
  "mcpServers": {
    "zotero": {
      "command": "uvx",
      "args": ["--from", "pyzotero[mcp]", "pyzotero-mcp"]
    }
  }
}
```

## Available Tools

### Zotero Library Tools

| Tool | Description |
|------|-------------|
| `search` | Search the local Zotero library by query, item type, collection, tag, or full-text content |
| `get_item` | Get a single Zotero item by its key |
| `get_children` | Get child items (attachments, notes) of a Zotero item |
| `list_collections` | List all collections in the library |
| `list_tags` | List all tags, optionally filtered by collection |
| `get_fulltext` | Get full-text content of a PDF or other attachment |

### Semantic Scholar Tools

| Tool | Description |
|------|-------------|
| `find_related` | Find semantically similar papers using SPECTER2 embeddings |
| `get_citations` | Find papers that cite a given paper |
| `get_references` | Find papers referenced by a given paper |
| `search_semantic_scholar` | Search across Semantic Scholar's paper index |

The Semantic Scholar tools can optionally check whether results already exist in your local Zotero library (enabled by default via the `check_library` parameter).

### Write Tools (opt-in)

The server is read-only unless started with `--enable-writes`.

#### Enabling write tools

1. Obtain a persistent local API key, choosing "Always Allow" in Zotero's dialog:

   ```
   pyzotero authorize --app-name "Claude Desktop"
   ```

   The key and the Zotero server ID are stored in `$XDG_CONFIG_HOME/pyzotero/local-api-key.json` (`~/.config/pyzotero/local-api-key.json` if that variable is unset), readable only by you. The server reads the key from that file.

2. Add the `--enable-writes` flag:

   ```json
   {
     "mcpServers": {
       "zotero": {
         "command": "pyzotero-mcp",
         "args": ["--enable-writes"]
       }
     }
   }
   ```

3. Optional: to supply the key some other way, set `PYZOTERO_LOCAL_API_KEY` in the server's `env` block, and `PYZOTERO_LOCAL_SERVER_ID` beside it to save one request at startup. The environment takes precedence over the key file. `pyzotero authorize --no-store` prints a key without writing the file.

#### Available write tools

| Tool | Description |
|------|-------------|
| `list_item_fields` | List the fields and creator types valid for an item type |
| `create_item` | Create a new item |
| `update_item` | Update fields on an existing item |
| `add_tags` | Add tags to an existing item |
| `create_collection` | Create a collection, optionally nested |
| `add_to_collection` | File an existing item under a collection |
| `remove_from_collection` | Remove an item from a collection; the item itself is unchanged |
| `move_to_collection` | Move an item from one collection to another in one step |
| `add_attachment` | Attach a file on disk to an existing item |
| `delete_item` | Permanently delete an item. Requires `--enable-deletes` |

#### How the write tools behave

Without `--enable-writes`, the write tools are not merely disabled: they are never registered, so they do not appear in the model's tool list at all, and content in your library cannot induce a call to one.

`add_attachment` requires an **absolute** path. The server runs as a subprocess of your MCP client, so its working directory is not yours, and a relative path would resolve somewhere unintended; relative paths are rejected rather than guessed at. The file is copied into Zotero's storage, and syncs with the library if sync is enabled. Attaching a file that is already attached to the item is reported as unchanged rather than duplicated, so a retried call is safe.

`delete_item` is behind a second flag because deletion via the local API is irreversible: items are erased outright rather than moved to the trash, and the deletion propagates on sync. `--enable-deletes` implies `--enable-writes`.

# Development

## Installing from Source

``` bash
git clone git://github.com/urschrei/pyzotero.git
cd pyzotero
git checkout main
# specify --dev if you're planning on running tests
uv sync
```

## Testing

Run `pytest .` from the top-level directory. This requires the `dev` dependency group to be installed: `uv sync --dev` / `pip install --group dev`

## Issues

The latest commits can be found on the [main branch][9], although new features are currently rare. If you encounter an error, please open an issue.

## Pull Requests

Pull requests are welcomed. Please read the [contribution guidelines](CONTRIBUTING.md). In particular, please **base your PR on the `main` branch**.

## Versioning

As of v1.0.0, Pyzotero is versioned according to [Semver](http://semver.org); version increments are performed as follows:

1. MAJOR version will increment with incompatible API changes,
2. MINOR version will increment when functionality is added in a backwards-compatible manner, and
3. PATCH version will increment with backwards-compatible bug fixes.

# Citation

Pyzotero has a DOI:
[![DOI](https://zenodo.org/badge/1423403.svg)](https://zenodo.org/badge/latestdoi/1423403)
You may also cite Pyzotero using [CITATION.cff](CITATION.cff).
A sample citation (APA 6th edition) might look like:
> Stephan Hügel, The Pyzotero Authors (2019, May 18). urschrei/pyzotero: Version v1.3.15. http://doi.org/10.5281/zenodo.2917290

# License

Pyzotero is licensed under the [Blue Oak Model Licence 1.0.0][8]. See [LICENSE.md](LICENSE.md) for details.

[1]: https://www.zotero.org/support/dev/web_api/v3/start
[2]: https://www.zotero.org/settings/keys/new
[3]: http://pyzotero.readthedocs.org/en/latest/
[7]: https://nose2.readthedocs.io/en/latest/
[8]: https://opensource.org/license/blue-oak-model-license
[9]: https://github.com/urschrei/pyzotero/tree/main
[10]: http://www.pip-installer.org/en/latest/index.html
[11]: https://docs.astral.sh/uv
† This isn't strictly true: you only need an API key for personal libraries and non-public group libraries.
