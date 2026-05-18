"""Categories resource — Phase 9 D-04/D-05.

Top-level cross-cutting model. Each Category drives Phase 10's propagation
to qBit (1 qBit category per Category), Sonarr/Radarr (4 resources per
Category), configarr (3 quality profiles total derived from profile union),
Seerr (animeTags for profile=anime), Jellyfin (PathInfos under 2 super-libraries).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Closed-set enums per CONTEXT.md D-01 + D-02. Adding a 4th profile
# requires an ADR + a code change (see REQUIREMENTS.md "Out of Scope").
Kind = Literal["movies", "series"]
Profile = Literal["general", "anime", "family"]


class Category(BaseModel):
    """A single Category — declarative input for Phase 10's 6-app propagation.

    Match key: ``name`` (kebab-case slug, stable across reconcile runs).
    D-04 invariant: ``base_path`` MUST equal ``f"/media/{name}"``.
    """

    model_config = ConfigDict(extra="forbid")
    name: str = Field(
        description="Kebab-case slug (e.g. 'series-emilie'). Stable match key.",
        pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$",
    )
    kind: Kind = Field(description="Media kind — drives Sonarr vs Radarr propagation.")
    profile: Profile = Field(
        description=(
            "Quality profile group — drives configarr profile selection (Phase 10) "
            "and Seerr animeTags routing for profile=anime."
        ),
    )
    display: str = Field(description="Title Case human label (e.g. 'Séries - Émilie').")
    base_path: str = Field(description="Absolute path under /media — MUST be /media/{name} (D-04).")

    @model_validator(mode="after")
    def _enforce_base_path_invariant(self) -> Category:
        """D-04 STRICT: base_path = /media/{name}, no override."""
        expected = f"/media/{self.name}"
        if self.base_path != expected:
            raise ValueError(
                f"base_path {self.base_path!r} != expected {expected!r} (D-04 strict invariant)"
            )
        return self
