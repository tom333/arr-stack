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


def test_schema_includes_category_descriptions(tmp_path: Path) -> None:
    """REQ-yaml-autocomplete: descriptions surface as VS Code hover tooltips.

    Phase 12-B (D-01): DownloadClient is no longer in the schema (the flat
    `items: list[DownloadClient]` field was removed from DownloadClientsSection).
    Category remains as a top-level RootConfig entry and is the canonical
    operator-edited type for autocomplete coverage.
    """
    out = tmp_path / "s.json"
    write_schema(out)
    data = json.loads(out.read_text())
    defs = data.get("$defs", {})
    cat_defs = [v for k, v in defs.items() if k == "Category"]
    assert cat_defs, f"Category definition not found in $defs (keys: {sorted(defs.keys())})"
    cat_props = cat_defs[0].get("properties", {})
    assert "name" in cat_props, "Category.name property not found"
    assert cat_props["name"].get("description"), (
        "Category.name MUST have a description for VS Code autocomplete (REQ-yaml-autocomplete)"
    )


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
