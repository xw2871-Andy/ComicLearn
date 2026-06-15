"""Shared project version and release metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = PROJECT_ROOT / "VERSION"
RELEASES_FILE = PROJECT_ROOT / "RELEASES.json"
FALLBACK_VERSION = "0.0.0"


def get_version() -> str:
    """Return the current ComicLearn version from the repository version file."""

    try:
        version = VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return FALLBACK_VERSION
    return version or FALLBACK_VERSION


def get_release_history() -> dict[str, Any]:
    """Return release metadata suitable for the Studio API."""

    current = get_version()
    try:
        data = json.loads(RELEASES_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}

    releases = data.get("releases")
    if not isinstance(releases, list):
        releases = []

    return {
        "current": str(data.get("current") or current),
        "releases": releases,
    }


__version__ = get_version()
