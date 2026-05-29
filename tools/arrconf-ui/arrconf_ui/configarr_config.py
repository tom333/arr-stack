"""Pydantic models for configarr.yml (CFGUI-02).

Models EXACTLY the real-file top-level subset (5 keys) per Assumption A1:
  trashGuideUrl, recyclarrConfigUrl, customFormatDefinitions, sonarr, radarr.

``extra="forbid"`` on every model class means:
- Out-of-scope *arrs (whisparr, readarr, lidarr) are CORRECTLY rejected — they are
  explicitly out-of-scope per PROJECT.md / CLAUDE.md.
- Unmodeled per-instance keys (delete_unmanaged_custom_formats, etc.) are rejected.

Extension point: if ``sonarrEnabled``/``radarrEnabled`` are ever needed (e.g. D-08 Option B
revisited), add them here as ``Optional[bool] = None`` fields on ``ConfigarrRootConfig``.

ADR-5: This file lives in ``tools/arrconf-ui/arrconf_ui/`` ONLY — NEVER ``tools/arrconf/``.
SC#3: No *arr URL is constructed or dialed anywhere in this module.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ---------------------------------------------------------------------------
# MediaNaming — ONE type for both sonarr (series/season/episodes) and radarr
# (folder/movie) keys. All fields Optional (Pitfall 5 — configarr does not
# split the type; real file uses series keys on sonarr, folder/movie on radarr).
# ---------------------------------------------------------------------------


class EpisodesNaming(BaseModel):
    """Episode naming patterns (sonarr)."""

    model_config = ConfigDict(extra="forbid")

    rename: bool | None = None
    standard: str | None = None
    daily: str | None = None
    anime: str | None = None


class MovieNaming(BaseModel):
    """Movie naming patterns (radarr)."""

    model_config = ConfigDict(extra="forbid")

    rename: bool | None = None
    standard: str | None = None


class MediaNaming(BaseModel):
    """Media naming configuration — one type covering both sonarr and radarr keys.

    Both sets of keys are Optional so a sonarr instance (series/season/episodes)
    and a radarr instance (folder/movie) both validate against this single model.
    Pitfall 5: do NOT split into SonarrMediaNaming/RadarrMediaNaming.
    """

    model_config = ConfigDict(extra="forbid")

    # radarr keys
    folder: str | None = None
    movie: MovieNaming | None = None

    # sonarr keys
    series: str | None = None
    season: str | None = None
    episodes: EpisodesNaming | None = None


# ---------------------------------------------------------------------------
# QualityDefinition (readOnly — managed by configarr/TRaSH, not editable)
# ---------------------------------------------------------------------------


class QualityDefQuality(BaseModel):
    """A single quality tier inside a quality definition."""

    model_config = ConfigDict(extra="forbid")

    quality: str
    title: str | None = None
    min: float
    preferred: float
    max: float


class QualityDefinition(BaseModel):
    """Quality definition — readOnly, typed for validation and schema generation."""

    model_config = ConfigDict(extra="forbid")

    type: str | None = None
    preferred_ratio: float | None = None
    qualities: list[QualityDefQuality] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# QualityProfile (editable)
# ---------------------------------------------------------------------------


class ResetUnmatchedScores(BaseModel):
    """Reset unmatched scores configuration inside a quality profile."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    except_: list[str] = Field(default_factory=list, alias="except")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Upgrade(BaseModel):
    """Upgrade configuration inside a quality profile.

    Conditional-required (Pitfall 3): when ``allowed=True``, both
    ``until_quality`` and ``until_score`` are required. When ``allowed=False``
    they are optional. Validated via ``@model_validator(mode='after')``.
    """

    model_config = ConfigDict(extra="forbid")

    allowed: bool
    until_quality: str | None = None
    until_score: int | None = None
    min_format_score: int | None = None

    @model_validator(mode="after")
    def _require_until_fields_when_allowed(self) -> Upgrade:
        if self.allowed:
            missing = []
            if self.until_quality is None:
                missing.append("until_quality")
            if self.until_score is None:
                missing.append("until_score")
            if missing:
                raise ValueError(f"upgrade.allowed=true requires: {', '.join(missing)}")
        return self


class QualityGroup(BaseModel):
    """A quality group (may bundle multiple codec/resolution qualities)."""

    model_config = ConfigDict(extra="forbid")

    name: str
    qualities: list[str] = Field(default_factory=list)
    enabled: bool | None = None


class QualityProfile(BaseModel):
    """A quality profile entry inside an arr instance."""

    model_config = ConfigDict(extra="forbid")

    name: str
    reset_unmatched_scores: ResetUnmatchedScores | None = None
    upgrade: Upgrade | None = None
    min_format_score: int | None = None
    score_set: str | None = None
    quality_sort: str | None = None
    language: str | None = None
    qualities: list[QualityGroup] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# CustomFormat (editable)
# ---------------------------------------------------------------------------


class AssignScoresTo(BaseModel):
    """Score assignment for a custom format entry."""

    model_config = ConfigDict(extra="forbid")

    name: str
    score: int | None = None
    use_default_score: bool | None = None


class CustomFormat(BaseModel):
    """A custom format entry in the arr instance's custom_formats list.

    Note: the deprecated ``quality_profiles`` key is intentionally NOT modeled;
    ``extra="forbid"`` will reject it, which is desirable (configarr deprecated it).
    Use ``assign_scores_to`` instead (current API).
    """

    model_config = ConfigDict(extra="forbid")

    trash_ids: list[str] = Field(default_factory=list)
    assign_scores_to: list[AssignScoresTo] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# CustomFormatDefinition (editable — the hand-rolled French CF definitions)
# ---------------------------------------------------------------------------


class Specification(BaseModel):
    """A specification inside a custom format definition.

    ``fields`` is typed as ``dict[str, Any]`` (Pitfall 4): ``value`` is ``str``
    for ReleaseTitleSpecification (regex) but ``int`` for ResolutionSpecification
    (e.g. 2160). Do NOT constrain the value type further.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    implementation: str
    negate: bool | None = None
    required: bool | None = None
    fields: dict[str, Any] = Field(default_factory=dict)


class CustomFormatDefinition(BaseModel):
    """A custom format definition (TRaSH-meta variant used in the real file)."""

    model_config = ConfigDict(extra="forbid")

    trash_id: str
    trash_scores: dict[str, int] | None = None
    trash_regex: str | None = None
    trash_description: str | None = None
    name: str
    includeCustomFormatWhenRenaming: bool | None = None  # noqa: N815
    specifications: list[Specification] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# ArrInstance — per-instance shape (sonarr.main / radarr.main)
# ---------------------------------------------------------------------------


class ArrInstance(BaseModel):
    """Per-arr-instance configuration block.

    ``base_url`` is a plain stored string — NEVER dialed (SC#3/ADR-5).
    ``api_key`` holds a ``!env NAME`` tag-literal reference (safe to surface;
    the tag reference is a variable name, not a secret — D-04).
    ``media_naming`` and ``quality_definition`` are readOnly (D-02): managed by
    configarr/TRaSH and must not be edited via the UI (hence ``readOnly: true``
    in the generated JSON Schema).
    """

    model_config = ConfigDict(extra="forbid")

    base_url: str  # stored/echoed verbatim, NEVER dialed (SC#3/ADR-5)
    api_key: str = Field(json_schema_extra={"readOnly": True})
    media_naming: MediaNaming | None = Field(default=None, json_schema_extra={"readOnly": True})
    quality_definition: QualityDefinition | None = Field(
        default=None, json_schema_extra={"readOnly": True}
    )
    quality_profiles: list[QualityProfile] = Field(default_factory=list)
    custom_formats: list[CustomFormat] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# ConfigarrRootConfig — top-level model
# ---------------------------------------------------------------------------


class ConfigarrRootConfig(BaseModel):
    """Root configuration model for configarr.yml.

    Models EXACTLY the 5 real-file top-level keys per Assumption A1.
    ``extra="forbid"`` correctly rejects out-of-scope *arrs (whisparr, readarr,
    lidarr) — they are explicitly out-of-scope per PROJECT.md/CLAUDE.md.

    ADR-5: Lives here in ``tools/arrconf-ui/arrconf_ui/`` ONLY.
    Never import ``RootConfig`` from ``arrconf.config`` here.
    """

    model_config = ConfigDict(extra="forbid")

    trashGuideUrl: str | None = None  # noqa: N815
    recyclarrConfigUrl: str | None = None  # noqa: N815
    customFormatDefinitions: list[CustomFormatDefinition] = Field(default_factory=list)  # noqa: N815
    sonarr: dict[str, ArrInstance] = Field(default_factory=dict)
    radarr: dict[str, ArrInstance] = Field(default_factory=dict)
