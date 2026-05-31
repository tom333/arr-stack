"""IntentConfig pydantic model + load_intent loader for intent.yml (Phase 28 / INTENT-01).

Defines the typed schema for the new ``intent.yml`` operator-edited file.
Every downstream plan in Phase 28 (cross-seed generator, generate CLI) imports
``CrossSeedConfig`` / ``load_intent`` from here.

Design decisions:
- extra=forbid on IntentConfig / ToolsConfig / CrossSeedConfig: unknown keys
  fail loudly (exit 2) rather than silently — mirrors the RootConfig convention.
- extra=allow on SagaEntry: Phase 28 ships the schema stub; Phase 29
  (SAGAS) will tighten the policy once the full saga schema is locked.
- ``load_intent`` mirrors ``load_config`` verbatim (YAML(typ="safe") + try/except
  wrapping all errors into ConfigError) — the same operator mental model.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from ruyaml import YAML

from arrconf.exceptions import ConfigError


class CrossSeedConfig(BaseModel):
    """Configuration block for the cross-seed tool (XSEED, INTENT-01)."""

    model_config = ConfigDict(extra="forbid")

    torznab: list[str] = Field(
        default_factory=list,
        description="List of torznab URLs (Prowlarr: http://host/N/api?apikey=KEY).",
    )
    torrent_clients: list[str] = Field(
        default_factory=list,
        description="Client connection strings (e.g. qbittorrent:http://user:pass@host:port).",
    )
    link_dirs: list[str] = Field(
        default_factory=list,
        description="Hardlink destination dirs.",
    )
    link_type: str = Field(
        default="hardlink",
        description="symlink|hardlink|reflink.",
    )
    action: str = Field(
        default="inject",
        description="inject|save.",
    )


class ToolsConfig(BaseModel):
    """Absorbed external tools (cross_seed, qbit_manage)."""

    model_config = ConfigDict(extra="forbid")

    cross_seed: CrossSeedConfig | None = Field(
        default=None,
        description="cross-seed block (XSEED). None when unconfigured.",
    )


class SagaEntry(BaseModel):
    """A single saga declaration.

    Schema present-but-unexercised in P28 (D-05).
    Phase 29 (SAGAS) will tighten the extra-key policy to forbid once the
    full saga schema is locked.
    """

    # relaxed until P29 locks the schema — do NOT tighten here
    model_config = ConfigDict(extra="allow")

    name: str = Field(description="Saga name. Full schema locked in Phase 29 (SAGAS).")


class IntentConfig(BaseModel):
    """Root schema for intent.yml (INTENT-01, Phase 28).

    Top-level layout: ``tools:`` mapping + ``sagas:`` list.
    Only ``tools.cross_seed`` is exercised in P28; ``sagas`` is present
    for schema completeness.
    """

    model_config = ConfigDict(extra="forbid")

    tools: ToolsConfig = Field(
        default_factory=ToolsConfig,
        description="Absorbed external tools (cross_seed, qbit_manage).",
    )
    sagas: list[SagaEntry] = Field(
        default_factory=list,
        description="Saga declarations. Schema present-but-unexercised in P28 (D-05).",
    )


def load_intent(path: Path) -> IntentConfig:
    """Load and validate an intent.yml file.

    Raises ``ConfigError`` (mapped to CLI exit code 2) for missing file,
    YAML parse failure, or pydantic validation failure.
    """
    if not path.exists():
        raise ConfigError(f"Intent file not found: {path}")
    yaml = YAML(typ="safe")
    try:
        with path.open("r", encoding="utf-8") as f:
            raw = yaml.load(f) or {}
    except Exception as e:
        raise ConfigError(f"YAML parse error in {path}: {e}") from e
    try:
        cfg = IntentConfig.model_validate(raw)
    except ValidationError as e:
        raise ConfigError(f"Intent validation error in {path}: {e}") from e
    return cfg
