[![Build Status](https://travis-ci.org/urschrei/pyzotero.png?branch=dev)](https://travis-ci.org/urschrei/pyzotero) [![Wheel Status](https://pypip.in/wheel/Pyzotero/badge.svg)](https://pypi.python.org/pypi/Pyzotero/) [![Supported Python versions](https://pypip.in/py_versions/Pyzotero/badge.svg)](https://pypi.python.org/pypi/Pyzotero/)

``` python
from pyzotero import zotero
zot = zotero.Zotero(library_id, library_type, api_key)
items = zot.top(limit=5)
# we've retrieved the latest five top-level items in our library
# we can print each item's item type and ID
for item in items:
    print('Item: %s | Key: %s') % (item['data']['itemType'], item['data']['key'])
```

# Description #
Pyzotero is a Python wrapper for the [Zotero read and write APIs (currently API v3)][1]. You'll require a library ID and access key, which can be set up [here][2].

See [Read The Docs][3] for full documentation of available Pyzotero methods, code examples, and sample output.

# Installation #

* Using [pip][10]: `pip install pyzotero`  
* From a wheel: `pip install --use-wheel pyzotero`  
* From a local clone, if you wish to install Pyzotero from a specific branch: 

Example:

``` bash
git clone git://github.com/urschrei/pyzotero.git
cd pyzotero
git checkout dev
pip install .
```

Installation using `easy_install` may be successful, but is neither tested nor officially supported – pip is the preferred method.

## Testing ##

Run `test_zotero.py` in the [pyzotero/test](test) directory, or, using [Nose][7], `nosetests` from the top-level directory.

## Issues ##

Pyzotero remains in development as of October 2014. The latest commits can be found on the [dev branch][9]. If you encounter an error, please open an issue.

## Pull Requests ##

Pull requests are welcomed. Please read the [contribution guidelines](CONTRIBUTING.md). 

## Versioning ##
As of v1.0.0, Pyzotero is versioned according to [Semver](http://semver.org); version increments are performed as follows:  



1. MAJOR version when you make incompatible API changes,
2. MINOR version when you add functionality in a backwards-compatible manner, and
3. PATCH version when you make backwards-compatible bug fixes.

# License #

Pyzotero is licensed under version 3 of the [GNU General Public License][8]. See `license.txt` for details.  

[1]: https://www.zotero.org/support/dev/web_api/v3/start
[2]: https://www.zotero.org/settings/keys/new
[3]: http://pyzotero.readthedocs.org/en/latest/
[4]: http://packages.python.org/Pyzotero/
[5]: http://feedparser.org
[6]: http://pypi.python.org/pypi/pip
[7]: https://nose.readthedocs.org/en/latest/
[8]: http://www.gnu.org/copyleft/gpl.html
[9]: https://github.com/urschrei/pyzotero/tree/dev
[10]: http://www.pip-installer.org/en/latest/index.html
