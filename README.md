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

Passing `local=True` directs Pyzotero at a running Zotero installation instead of the web API. Reads need no authentication; writes need the user's consent, given through a dialog in Zotero, and a Zotero version that supports local writes:

``` python
from pyzotero import Zotero

zot = Zotero("0", "user", local=True)
auth = zot.authorize_local("My Application")  # Zotero prompts the user
zot.create_items([item])
```

A key granted with "Always Allow" can be stored and passed back later as `local_api_key`. Versions and keys are scoped to a single Zotero instance, identified by `zot.server_id`. See the [local API documentation][12] for how this works, how-to guides, and reference material.

# Installation

* Using [uv][11]: `uv add pyzotero`
* Using [pip][10]: `pip install pyzotero`
* Using Anaconda: `conda install conda-forge::pyzotero`

Pyzotero also provides an optional [CLI](#command-line-interface) and [MCP server](#mcp-server) for working with a local Zotero library. Both require Zotero 7 with local API access enabled: Zotero > Settings > Advanced > "Allow other applications on this computer to communicate with Zotero". Both are read-only unless you run `pyzotero authorize`, which stores a local API key. With that key, the CLI's write commands can write, and the MCP server can write if started with `--enable-writes`. Both console scripts are installed whichever extra you choose; one whose extra is missing exits with a message naming the extra to install.

# Command-Line Interface

Pyzotero includes an optional CLI for searching your local Zotero library, adding items to it, and managing its collections.

* Using [uv][11]: `uv add "pyzotero[cli]"`
* Using [pip][10]: `pip install "pyzotero[cli]"`
* Without installing: `uvx --from "pyzotero[cli]" pyzotero search -q "your query"`

```bash
pyzotero search -q "machine learning" --json
pyzotero search -q "climate change" --fulltext
pyzotero listcollections
pyzotero authorize --app-name "My tool"   # store a local API key, which the write commands need
pyzotero createitem items.json --collection FD9AUNP2 --tag "to read"
```

Run `pyzotero --help` for the full list of commands, and see the [CLI documentation][13] for details of the write commands, search behaviour, and output formats.

# MCP Server

Pyzotero includes an optional [MCP](https://modelcontextprotocol.io) server that exposes your local Zotero library and Semantic Scholar integration as tools for LLM applications such as Claude Desktop.

* Using [uv][11]: `uv add "pyzotero[mcp]"`
* Using [pip][10]: `pip install "pyzotero[mcp]"`
* As a standalone tool: `uv tool install "pyzotero[mcp]"`

Add it to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "zotero": {
      "command": "pyzotero-mcp"
    }
  }
}
```

The server is read-only by default. Starting it with `--enable-writes` registers tools that create and modify items and collections, and `--enable-deletes` additionally registers permanent deletion. See the [MCP server documentation][14] for the configuration, the full list of tools, and how the write tools behave.

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
[12]: https://pyzotero.readthedocs.io/en/latest/#the-local-zotero-api
[13]: https://pyzotero.readthedocs.io/en/latest/#command-line-interface-usage
[14]: https://pyzotero.readthedocs.io/en/latest/#mcp-server
† This isn't strictly true: you only need an API key for personal libraries and non-public group libraries.
