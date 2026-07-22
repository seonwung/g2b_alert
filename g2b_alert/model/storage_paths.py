"""Resolve source, executable, and persistent data directories."""

import sys
import os
from pathlib import Path


def get_persistent_app_dir():
    base_dir = os.getenv("LOCALAPPDATA")
    if base_dir:
        return Path(base_dir) / "G2BAlert"
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def get_persistent_data_dir():
    return get_persistent_app_dir() / "data"
