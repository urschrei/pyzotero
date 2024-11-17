[![Supported Python versions](https://img.shields.io/pypi/pyversions/Pyzotero.svg?style=flat)](https://pypi.python.org/pypi/Pyzotero/) [![Docs](https://readthedocs.org/projects/pyzotero/badge/?version=latest)](http://pyzotero.readthedocs.org/en/latest/?badge=latest) [![PyPI Version](https://img.shields.io/pypi/v/Pyzotero.svg)](https://pypi.python.org/pypi/Pyzotero) [![Anaconda-Server Badge](https://anaconda.org/conda-forge/pyzotero/badges/version.svg)](https://anaconda.org/conda-forge/pyzotero) [![Downloads](https://pepy.tech/badge/pyzotero)](https://pepy.tech/project/pyzotero)  

# Pyzotero: An API Client for the Zotero API

## Project Overview

Pyzotero is a Python client for the Zotero API.

## Prerequisites

This project is built using Python 3.7 and up. Ensure you have Python installed before proceeding.

## Installation Steps:

### Option 1: Using pip

```bash
pip install pyzotero
```

### Option 2: Using Anaconda

```bash
conda config --add channels conda-forge && conda install pyzotero
```

### Option 3: From a local clone

```bash
git clone git://github.com/urschrei/pyzotero.git
cd pyzotero
git checkout dev
pip install .
```

## Quickstart

1. You'll need the ID of the personal or group library you want to access:
    - Your **personal library ID** is available [here](https://www.zotero.org/settings/keys), in the section `Your userID for use in API calls`
    - For **group libraries**, the ID can be found by opening the group's page: `https://www.zotero.org/groups/groupname`, and hovering over the `group settings` link. The ID is the integer after `/groups/`
2. You'll also need<sup>†</sup>  an **API key** [here][2].
3. Determine the `library_type`: `'user'` for personal libraries, `'group'` for shared group libraries.

Example usage:

```python
from pyzotero import zotero
zot = zotero.Zotero(library_id, library_type, api_key)
items = zot.top(limit=5)
for item in items:
    print('Item: %s | Key: %s' % (item['data']['itemType'], item['data']['key']))
```

## Documentation

Full documentation of available Pyzotero methods, code examples, and sample output is available on [Read The Docs][3].

## Testing

Run `pytest .` from the top-level directory to execute tests.

## Issues

The latest commits can be found on the [dev branch][9]. If you encounter an error, please open an issue.

## Pull Requests

Pull requests are welcomed. Please read the [contribution guidelines](CONTRIBUTING.md). In particular, please **base your PR on the `dev` branch**.

## Versioning

Pyzotero follows [Semver](http://semver.org):
1. MAJOR version increments with incompatible API changes,
2. MINOR version increments with added functionality (backwards-compatible),
3. PATCH version increments with backwards-compatible bug fixes.

## License

Pyzotero is licensed under the [Blue Oak Model Licence 1.0.0][8]. See [LICENCE.md](LICENCE.md) for details.

## Citation

Pyzotero has a DOI: [![DOI](https://zenodo.org/badge/1423403.svg)](https://zenodo.org/badge/latestdoi/1423403).
Sample citation:

> Stephan Hügel, The Pyzotero Authors (2019, May 18). urschrei/pyzotero: Version v1.3.15. http://doi.org/10.5281/zenodo.2917290


[1]: https://www.zotero.org/support/dev/web_api/v3/start
[2]: https://www.zotero.org/settings/keys/new
[3]: http://pyzotero.readthedocs.org/en/latest/
[7]: https://nose2.readthedocs.io/en/latest/
[8]: https://opensource.org/license/blue-oak-model-license
[9]: https://github.com/urschrei/pyzotero/tree/dev
[10]: http://www.pip-installer.org/en/latest/index.html
† This isn't strictly true: you only need an API key for personal libraries and non-public group libraries.

