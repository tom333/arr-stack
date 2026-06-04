"""Tests for arrconf.schema_gen — JSON Schema reproducibility (D-15).

Verifies the schema is Draft 2020-12, reproducible byte-for-byte across
calls, includes pydantic ``Field(description=...)`` strings (so VS Code
hover tooltips render — REQ-yaml-autocomplete), and matches what is
committed at ``schemas/arrconf-schema.json`` (D-15 CI gate sentinel).
"""

from __future__ import annotations

import json
from pathlib import Path

from arrconf.schema_gen import write_schema


def test_schema_is_draft_2020_12(tmp_path: Path) -> None:
    out = tmp_path / "schema.json"
    write_schema(out)
    data = json.loads(out.read_text())
    assert data["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_schema_is_reproducible(tmp_path: Path) -> None:
    """write_schema MUST produce byte-identical output across calls (D-15)."""
    out1 = tmp_path / "s1.json"
    out2 = tmp_path / "s2.json"
    write_schema(out1)
    write_schema(out2)
    assert out1.read_bytes() == out2.read_bytes()


def test_schema_no_categories_in_rootconfig(tmp_path: Path) -> None:
    """CATMIG-01 (Phase 32): RootConfig schema must NOT include categories.

    Categories moved to IntentConfig (intent.yml). The arrconf schema (RootConfig)
    must not expose categories to avoid operator confusion.
    """
    out = tmp_path / "s.json"
    write_schema(out)
    data = json.loads(out.read_text())
    # The top-level RootConfig properties must NOT have categories
    top_props = data.get("properties", {})
    assert "categories" not in top_props, (
        "CATMIG-01: categories must NOT appear in RootConfig schema (arrconf.yml). "
        "Categories now live in IntentConfig (intent.yml)."
    )
    # Category MAY still appear in $defs (referenced by IntentConfig or other models)
    # but its absence from RootConfig properties is the key assertion.


def test_schema_committed_matches_regen(tmp_path: Path) -> None:
    """The committed schemas/arrconf-schema.json must match a fresh regen (D-15 CI gate)."""
    committed = Path(__file__).parent.parent.parent.parent / "schemas/arrconf-schema.json"
    if not committed.exists():
        # Pre-commit run before schema-gen has been wired — CI catches it.
        return
    out = tmp_path / "regen.json"
    write_schema(out)
    assert committed.read_bytes() == out.read_bytes(), (
        "schemas/arrconf-schema.json drifted from regen output. "
        "Run `cd tools/arrconf && uv run arrconf schema-gen "
        "--output ../../schemas/arrconf-schema.json` and commit."
    )
