"""Pydantic models for arrconf YAML config (RootConfig).

Top-level schema used by ``schema_gen.write_schema`` to produce the JSON
Schema consumed by yaml-language-server (D-16). YAML loading itself is a
Wave 3 concern — only the model shape ships in Wave 1.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

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
    """Load and validate YAML config.

    Raises ConfigError on parse/validation failure (W3 fills body).
    """
    raise NotImplementedError("Wave 3 — load YAML via ruyaml + RootConfig.model_validate")
