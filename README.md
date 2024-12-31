[![Supported Python versions](https://img.shields.io/pypi/pyversions/Pyzotero.svg?style=flat)](https://pypi.python.org/pypi/Pyzotero/) [![Docs](https://readthedocs.org/projects/pyzotero/badge/?version=latest)](http://pyzotero.readthedocs.org/en/latest/?badge=latest) [![PyPI Version](https://img.shields.io/pypi/v/Pyzotero.svg)](https://pypi.python.org/pypi/Pyzotero) [![Anaconda-Server Badge](https://anaconda.org/conda-forge/pyzotero/badges/version.svg)](https://anaconda.org/conda-forge/pyzotero) [![Downloads](https://pepy.tech/badge/pyzotero)](https://pepy.tech/project/pyzotero)  

# Pyzotero: An API Client for the Zotero API

# Quickstart

1. `pip install pyzotero` **or** `conda config --add channels conda-forge && conda install pyzotero`
2. You'll need the ID of the personal or group library you want to access:
    - Your **personal library ID** is available [here](https://www.zotero.org/settings/keys), in the section `Your userID for use in API calls`
    - For **group libraries**, the ID can be found by opening the group's page: `https://www.zotero.org/groups/groupname`, and hovering over the `group settings` link. The ID is the integer after `/groups/`
3. You'll also need<sup>†</sup> to get an **API key** [here][2]
4. Are you accessing your own Zotero library? `library_type` is `'user'`
5. Are you accessing a shared group library? `library_type` is `'group'`.  

Then:

``` python
from pyzotero import zotero
zot = zotero.Zotero(library_id, library_type, api_key) # local=True for read access to local Zotero
items = zot.top(limit=5)
# we've retrieved the latest five top-level items in our library
# we can print each item's item type and ID
for item in items:
    print('Item: %s | Key: %s' % (item['data']['itemType'], item['data']['key']))
```

# Documentation

Full documentation of available Pyzotero methods, code examples, and sample output is available on [Read The Docs][3].

# Installation

* Using [pip][10]: `pip install pyzotero` (it's available as a wheel, and is tested on Python 3.7 and up)
* Using Anaconda:`conda config --add channels conda-forge && conda install pyzotero`
* From a local clone, if you wish to install Pyzotero from a specific branch: 

Example:

``` bash
git clone git://github.com/urschrei/pyzotero.git
cd pyzotero
git checkout main
pip install .
```

## Testing

Run `pytest .` from the top-level directory.

## Issues

The latest commits can be found on the [main branch][9], although new features are currently rare. If you encounter an error, please open an issue.

## Pull Requests

Pull requests are welcomed. Please read the [contribution guidelines](CONTRIBUTING.md). In particular, please **base your PR on the `dev` branch**.

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
† This isn't strictly true: you only need an API key for personal libraries and non-public group libraries.

