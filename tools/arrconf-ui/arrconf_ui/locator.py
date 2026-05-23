"""Repo-root + arrconf.yml path locator (D-12).

The console script `arrconf-ui` is launched from anywhere; this module walks
the filesystem from the installed package location to find the repo root
(the parent of `tools/arrconf-ui/`) and the canonical arrconf.yml under
`charts/arr-stack/files/arrconf.yml`.
"""

from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    """Return the arr-stack repo root.

    Walks `parents[3]` from this file:
        tools/arrconf-ui/arrconf_ui/locator.py
        parents[0] = tools/arrconf-ui/arrconf_ui
        parents[1] = tools/arrconf-ui
        parents[2] = tools
        parents[3] = <repo root>
    """
    return Path(__file__).resolve().parents[3]


def arrconf_yml_path() -> Path:
    """Return the canonical path to charts/arr-stack/files/arrconf.yml."""
    return repo_root() / "charts" / "arr-stack" / "files" / "arrconf.yml"


def schema_json_path() -> Path:
    """Return the canonical path to schemas/arrconf-schema.json."""
    return repo_root() / "schemas" / "arrconf-schema.json"
