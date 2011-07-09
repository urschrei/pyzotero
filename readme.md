# Description #

A Python wrapper for the [Zotero API][1]. You'll require a user ID and access key, which can be set up [here][2].

See <http://pyzotero.readthedocs.org/en/latest/> or <http://packages.python.org/Pyzotero/> for full documentation of available methods. The package itself also includes complete documentation in HTML, PDF and ePub formats.

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

The [feedparser][3] (>= v5.0.1) module is required. It should automatically be installed when installing pyzotero using [pip][4].

## Testing ##

Run `tests.py` in the `pyzotero` directory, or, using [Nose][5], `nosetests` from the top-level directory.