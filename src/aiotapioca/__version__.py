from __future__ import annotations

import importlib.metadata as importlib_metadata

from packaging.version import Version, parse


try:
    __version__ = importlib_metadata.version(__package__)
    parsed_version: Version | None = parse(__version__)
except importlib_metadata.PackageNotFoundError:
    __version__ = "UNKNOWN"
    parsed_version = None
