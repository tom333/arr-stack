"""Pydantic models + YAML loader for arrconf config.

Top-level schema used by ``schema_gen.write_schema`` to produce the JSON
Schema consumed by yaml-language-server (D-16). ``load_config`` is the
Wave 3 entrypoint that the typer CLI calls before reconciliation.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from ruyaml import YAML

from arrconf.exceptions import ConfigError
from arrconf.resources.sonarr.download_client import DownloadClient


class DownloadClientsSection(BaseModel):
    """A list of download_clients with opt-in prune (D-04)."""

    model_config = ConfigDict(extra="forbid")
    prune: bool = Field(
        default=False,
        description="Opt-in deletion of unmanaged resources (D-04).",
    )
    items: list[DownloadClient] = Field(default_factory=list)


class SonarrInstance(BaseModel):
    """A single Sonarr instance (Phase 1 supports only ``main`` per ADR-7)."""

    model_config = ConfigDict(extra="forbid")
    base_url: str = Field(description="Sonarr base URL e.g. http://sonarr.svc:8989")
    download_clients: DownloadClientsSection = Field(default_factory=DownloadClientsSection)


class SonarrConfig(BaseModel):
    """Sonarr config block (single instance per ADR-7)."""

    model_config = ConfigDict(extra="forbid")
    main: SonarrInstance | None = None


class AppsConfig(BaseModel):
    """Top-level apps config — one block per *arr family member."""

    model_config = ConfigDict(extra="forbid")
    sonarr: SonarrConfig | None = None


class RootConfig(BaseModel):
    """Top-level arrconf YAML schema (root for JSON Schema generation)."""

    model_config = ConfigDict(extra="forbid")
    apps: AppsConfig = Field(default_factory=AppsConfig)


def load_config(path: Path) -> RootConfig:
    """Load and validate a YAML config file.

    Raises ``ConfigError`` (mapped to CLI exit code 2) for missing file,
    YAML parse failure, or pydantic validation failure (D-13 / D-22).
    """
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    yaml = YAML(typ="safe")
    try:
        with path.open("r", encoding="utf-8") as f:
            raw = yaml.load(f) or {}
    except Exception as e:
        raise ConfigError(f"YAML parse error in {path}: {e}") from e
    try:
        return RootConfig.model_validate(raw)
    except ValidationError as e:
        raise ConfigError(f"Config validation error in {path}: {e}") from e
