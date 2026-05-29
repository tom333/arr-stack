"""Generate JSON Schema (Draft 2020-12) from ConfigarrRootConfig.

Local sibling of ``tools/arrconf/arrconf/schema_gen.py`` — mirrors that module's
pattern for ``ConfigarrRootConfig`` only. Do NOT import from ``arrconf.schema_gen``;
this module is self-contained per ADR-5.

Usage (regenerate committed schema)::

    python -m arrconf_ui.configarr_schema_gen

The generated ``schemas/configarr-schema.json`` is committed for reproducibility;
Plan 04 adds a CI ``git diff --exit-code`` gate to detect drift.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic.json_schema import GenerateJsonSchema

from arrconf_ui.configarr_config import ConfigarrRootConfig


class Draft202012Generator(GenerateJsonSchema):
    """Force ``$schema`` dialect to Draft 2020-12 (yaml-language-server preferred)."""

    schema_dialect = "https://json-schema.org/draft/2020-12/schema"

    def generate(
        self,
        schema: Any,
        mode: Literal["validation", "serialization"] = "validation",
    ) -> dict[str, Any]:
        """Generate the JSON Schema and force Draft 2020-12 dialect on the root."""
        json_schema: dict[str, Any] = super().generate(schema, mode=mode)
        json_schema["$schema"] = self.schema_dialect
        return json_schema


def _default_output_path() -> Path:
    """Return the canonical path to schemas/configarr-schema.json.

    Resolves from this file's location:
        tools/arrconf-ui/arrconf_ui/configarr_schema_gen.py
        parents[0] = tools/arrconf-ui/arrconf_ui
        parents[1] = tools/arrconf-ui
        parents[2] = tools
        parents[3] = <repo root>
    """
    return Path(__file__).resolve().parents[3] / "schemas" / "configarr-schema.json"


def write_configarr_schema(output_path: Path) -> None:
    """Write ConfigarrRootConfig JSON Schema reproducibly.

    Uses sort_keys=True for the D-15 git diff reproducibility check.
    """
    schema = ConfigarrRootConfig.model_json_schema(schema_generator=Draft202012Generator)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    output = _default_output_path()
    write_configarr_schema(output)
    print(f"Wrote configarr schema to {output}")  # noqa: T201
