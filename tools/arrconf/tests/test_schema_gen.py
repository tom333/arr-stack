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


def test_schema_includes_download_client_descriptions(tmp_path: Path) -> None:
    """REQ-yaml-autocomplete: descriptions surface as VS Code hover tooltips."""
    out = tmp_path / "s.json"
    write_schema(out)
    data = json.loads(out.read_text())
    defs = data.get("$defs", {})
    dc_defs = [v for k, v in defs.items() if "DownloadClient" in k and "FieldKV" not in k]
    assert dc_defs, f"DownloadClient definition not found in $defs (keys: {list(defs.keys())})"
    dc_props = dc_defs[0].get("properties", {})
    assert "name" in dc_props, "DownloadClient.name property not found"
    assert dc_props["name"].get("description"), (
        "DownloadClient.name MUST have a description for VS Code autocomplete "
        "(REQ-yaml-autocomplete)"
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
