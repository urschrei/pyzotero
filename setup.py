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
    version = '0.9.9',
    description = 'Python wrapper for the Zotero API',
    author = 'Stephan Hügel',
    author_email = 'urschrei@gmail.com',
    license = 'GNU GPL Version 3',
    url = 'https://github.com/urschrei/pyzotero',
    download_url = 'https://github.com/urschrei/pyzotero/tarball/v0.9.9',
    keywords = ['zotero'],
    classifiers = [
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries :: Python Modules',
        ],
    packages = find_packages(),
    install_requires = ['feedparser >= 5.0.1', 'pytz', 'poster >= 0.8.1'],
    long_description = """\
A Python wrapper for the Zotero Server API
------------------------------------------

Provides methods for accessing all Zotero Server API calls currently provided.
A full list is available here: http://www.zotero.org/support/dev/server_api

This version requires Python 2.7.x
            """
)
