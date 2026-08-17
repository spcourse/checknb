"""Packaging for checknb.

The version lives in `checknb/__init__.py` and is read out of the source here
rather than imported -- importing the package at build time would require its
dependencies to already be installed.
"""

import re
from pathlib import Path

from setuptools import find_packages, setup

HERE = Path(__file__).parent


def read_version() -> str:
    source = (HERE / "checknb" / "__init__.py").read_text()
    match = re.search(r'^__version__ = "([^"]+)"', source, re.MULTILINE)
    if not match:
        raise RuntimeError("no __version__ in checknb/__init__.py")
    return match.group(1)


setup(
    name="checknb",
    version=read_version(),
    description="Run an nbgrader notebook and score its autograded test cells",
    long_description=(HERE / "README.md").read_text(),
    long_description_content_type="text/markdown",
    url="https://github.com/spcourse/checknb",
    license="GPL-2.0-only",
    packages=find_packages(include=["checknb", "checknb.*"]),
    # 3.11 is the floor across the Scientific Programming track.
    python_requires=">=3.11",
    install_requires=[
        # Provides the `jupyter nbconvert` command that actually runs the
        # notebook, and pulls in nbclient/nbformat with it.
        "nbconvert>=7.0",
        # The kernel the notebook is executed against. nbconvert does not
        # depend on it, and without it every run dies with "No such kernel".
        "ipykernel>=6.0",
    ],
    entry_points={
        "console_scripts": [
            "checknb = checknb.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Education",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Programming Language :: Python :: 3",
        "Topic :: Education :: Testing",
    ],
)
