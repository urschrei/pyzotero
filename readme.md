# Description #

A Python wrapper for the [Zotero API][1]. You'll require a user ID and access key, which can be set up [here][2].

See [Read The Docs][3] or [packages.python.org][4] for full documentation of available methods. The package itself also includes complete documentation in HTML, PDF and ePub formats.

# Installation #

* using pip: `pip install pyzotero` 
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

I assume that running setup.py will also work using `easy_install`, but I haven't tested it.

The [feedparser][5] (>= v5.0.1) and [pytz][9] modules are required. They will be automatically installed when installing pyzotero using [pip][6].

## Testing ##

Run `tests.py` in the `pyzotero` directory, or, using [Nose][7], `nosetests` from the top-level directory.

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
[9]: http://pypi.python.org/pypi/pytz/
