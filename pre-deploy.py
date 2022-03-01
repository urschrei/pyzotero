#!/usr/bin/env python
"""
pre-deploy.py

Created by Stephan Hügel on 2017-06-06

A simple check to ensure that the tag version and the library version coincide
Intended to be called before a Wheel is written using "upload"
"""

import os
import sys
import subprocess
import re
import io

if sys.version_info.major == 3:
    unicode = str


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


def check():
    git_version = (
        subprocess.check_output(["git", "describe", "--abbrev=0", "--tags"])
        .decode("utf-8")
        .strip()
    )
    library_version = unicode("v" + find_version("pyzotero/version.py")).strip()
    # invert the boolean because 1 (True) == Bash error exit code
    print("Git version: %s\nLibrary version: %s" % (git_version, library_version))
    return not library_version == git_version


if __name__ == "__main__":
    sys.exit(check())
