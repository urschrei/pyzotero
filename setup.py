#!/usr/bin/env python
# encoding: utf-8
"""
setup.py

Created by Stephan Hügel on 2011-03-04
"""
#!/usr/bin/env python

from setuptools import setup, find_packages
import pyzotero.zotero as z

setup(
    name = 'Pyzotero',
    version = z.__version__,
    description = 'Python wrapper for the Zotero API',
    author = 'Stephan Hügel',
    author_email = 'hugels@tcd.ie',
    license = 'GNU GPL Version 3',
    url = 'https://github.com/urschrei/pyzotero',
    packages = find_packages(),
)