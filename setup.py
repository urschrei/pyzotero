#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
setup.py

Created by Stephan Hügel on 2011-03-04
"""

from setuptools import setup, find_packages

setup(
    name='Pyzotero',
    version='1.0.0',
    description='Python wrapper for the Zotero API',
    author='Stephan Hügel',
    author_email='urschrei@gmail.com',
    license='GNU GPL Version 3',
    url='https://github.com/urschrei/pyzotero',
    include_package_data=True,
    download_url='https://github.com/urschrei/pyzotero/tarball/v1.0.0',
    keywords=['zotero'],
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    packages=find_packages(),
    install_requires=['feedparser >= 5.1.0', 'pytz', 'requests', 'six'],
    extras_require={
        'ordereddict': ['ordereddict==1.1']
    },
    long_description="""\
A Python wrapper for the Zotero Server API
------------------------------------------

Provides methods for accessing all Zotero Server API v3 calls currently provided.
A full list is available here: http://www.zotero.org/support/dev/server_api

This version requires Python 2.7.x / 3.4.x"""
)
