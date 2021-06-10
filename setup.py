#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
setup.py

Created by Stephan Hügel on 2011-03-04
"""
import os
import re
import io
from setuptools import setup, find_packages


def read(*names, **kwargs):
    with io.open(
        os.path.join(os.path.dirname(__file__), *names),
        encoding=kwargs.get("encoding", "utf8"),
    ) as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


version = find_version("pyzotero/zotero.py")

with open('README.md') as f:
    readme = f.read()

setup(
    name="Pyzotero",
    version=version,
    description="Python wrapper for the Zotero API",
    author="Stephan Hügel",
    author_email="urschrei@gmail.com",
    license="MIT License",
    url="https://github.com/urschrei/pyzotero",
    include_package_data=True,
    download_url="https://github.com/urschrei/pyzotero/tarball/v%s" % version,
    keywords=["zotero"],
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    packages=find_packages(exclude=('test*')),
    install_requires=[
        "feedparser > 5.1.0, < 6",
        "pytz",
        "requests >= 2.21.0",
        "pathlib",
        "bibtexparser",
    ],
    extras_require={"ordereddict": ["ordereddict==1.1"]},
    long_description=readme,
    long_description_content_type="text/markdown",
)
