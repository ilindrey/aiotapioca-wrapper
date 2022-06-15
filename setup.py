#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import os
import re
import sys

description = """
It's an asynchronous fork of https://github.com/vintasoftware/tapioca-wrapper library.

Tapioca provides an easy way to make explorable Python API wrappers.
APIs wrapped by Tapioca follow a simple interaction pattern that works uniformly so developers don't need to learn how to use a new coding interface/style for each service API.

Source code hosted on Github: https://github.com/ilindrey/aiotapioca-wrapper

Documentation hosted by Readthedocs (original library, it's not asynchronous): http://tapioca-wrapper.readthedocs.io/en/stable/
"""

package = "aiotapioca"
requirements = [
    "aiohttp>=3.0",
    "orjson>=3.0.0",
    "pydantic>=1.0.0",
    "xmltodict>=0.9.2",
    "asyncio_atexit>=1.0,<2.0",
]
test_requirements = [
    "aioresponses>=0.7",
    "pytest>=7.0",
    "pytest-asyncio>=0.18",
    "yarl>=1.0,<2.0",
]
dev_requirements = [
    *test_requirements,
    "black>=22.0",
    "isort>=5.10.0",
]


def get_version(package):
    """
    Return package version as listed in `__version__` in `init.py`.
    """
    init_py = open(os.path.join(package, "__init__.py")).read()
    return re.search("^__version__ = ['\"]([^'\"]+)['\"]", init_py, re.MULTILINE).group(
        1
    )


# python setup.py register
if sys.argv[-1] == "publish":
    os.system("python setup.py sdist upload")
    args = {"version": get_version(package)}
    print("You probably want to also tag the version now:")
    print("  git tag -a %(version)s -m 'version %(version)s'" % args)
    print("  git push --tags")
    sys.exit()


setup(
    name="aiotapioca-wrapper",
    version=get_version(package),
    description="Python API client generator",
    long_description=description,
    author="Filipe Ximenes, Andrey Ilin",
    author_email="andreyilin@fastmail.com",
    url="https://github.com/ilindrey/aiotapioca-wrapper",
    package_dir={package: package},
    packages=[package, f"{package}.adapters", f"{package}.client"],
    include_package_data=True,
    install_requires=requirements,
    license="MIT",
    zip_safe=False,
    keywords="async,tapioca,wrapper,api",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
    ],
    python_requires=">=3.7",
    test_suite="tests",
    tests_require=test_requirements,
    extras_require={"dev": dev_requirements},
)
