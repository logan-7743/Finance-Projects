"""Filesystem paths for the local event corpus."""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def events_data_root() -> Path:
    override = os.environ.get("EVENTS_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return repo_root() / "data" / "events"


def raw_dir(source: str) -> Path:
    return events_data_root() / "raw" / source


def normalized_path(name: str) -> Path:
    return events_data_root() / "normalized" / name


def manifest_path() -> Path:
    return events_data_root() / "manifest.json"
