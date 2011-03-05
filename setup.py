#!/usr/bin/env python
# encoding: utf-8
"""
setup.py

Created by Stephan Hügel on 2011-03-04
"""
#!/usr/bin/env python

from setuptools import setup, find_packages
import zotero

setup(
    name = 'Pyzotero',
    version = zotero.__version__,
    description = 'Python wrapper for the Zotero API',
    author = 'Stephan Hügel',
    author_email = 'hugels@tcd.ie',
    url = "https://github.com/urschrei/pyzotero",
    packages = find_packages(),
)