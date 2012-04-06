``` python
from pyzotero import zotero
zot = zotero.Zotero(library_id, library_type, api_key)
items = zot.top(limit = 5)
# we have now retrieved the last five top-level items in our library
# we can print each item's item type and ID
for item in items:
    print 'Item Type: %s | Key: %s' % (item['itemType'], item['key'])
```

# Description #
Pyzotero is a Python wrapper for the [Zotero read and write APIs][1]. You'll require a library ID and access key, which can be set up [here][2].

See [Read The Docs][3] for full documentation of available Pyzotero methods, code examples, and sample output.

# Installation #

* using [pip][10]: `pip install pyzotero` 
* From a local clone, if you wish to install Pyzotero from a specific branch: 

Example:

``` bash
git clone git://github.com/urschrei/pyzotero.git
cd pyzotero
git checkout dev
pip install .
```
    

* Alternatively, download the latest version from <https://github.com/urschrei/pyzotero/downloads>, and point pip at the zip file:  
Example: `pip install ~/Downloads/urschrei-pyzotero-v0.3-0-g04ff544.zip`

Installation using `easy_install` may be successful, but is neither tested nor officially supported – pip is the preferred method.

## Testing ##

Run `tests.py` in the `pyzotero` directory, or, using [Nose][7], `nosetests` from the top-level directory.

## Issues ##

Pyzotero remains in development as of March 2012. The latest commits can be found on the [dev branch][9]. If you encounter an error, please open an issue.

## Pull Requests ##

Pull requests are welcomed. Please ensure that you base your changes on the most recent commit in the `dev` branch, rebasing against it prior to opening the request if necessary.

# License #

Pyzotero is licensed under version 3 of the [GNU General Public License][8]. See `license.txt` for details.


[1]: http://www.zotero.org/support/dev/server_api
[2]: https://www.zotero.org/settings/keys/new
[3]: http://pyzotero.readthedocs.org/en/latest/
[4]: http://packages.python.org/Pyzotero/
[5]: http://feedparser.org
[6]: http://pypi.python.org/pypi/pip
[7]: http://somethingaboutorange.com/mrl/projects/nose/1.0.0/
[8]: http://www.gnu.org/copyleft/gpl.html
[9]: https://github.com/urschrei/pyzotero/tree/dev
[10]: http://www.pip-installer.org/en/latest/index.html
