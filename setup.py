#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
setup.py

Created by Stephan Hügel on 2011-03-04
"""
#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name = 'Pyzotero',
    version = '0.6.6',
    description = 'Python wrapper for the Zotero API',
    author = 'Stephan Hügel',
    author_email = 'hugels@tcd.ie',
    license = 'GNU GPL Version 3',
    url = 'https://github.com/urschrei/pyzotero',
    packages = find_packages(),
    install_requires = ['feedparser >= 5.0.1', 'elementtree >= 1.2.7'],
)