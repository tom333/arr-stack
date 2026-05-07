"""Generate JSON Schema (Draft 2020-12) from RootConfig for VS Code autocomplete."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic.json_schema import GenerateJsonSchema

from arrconf.config import RootConfig


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


def write_schema(output_path: Path) -> None:
    """Write JSON Schema reproducibly (sort_keys=True for D-15 git diff check)."""
    schema = RootConfig.model_json_schema(schema_generator=Draft202012Generator)
    output_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
