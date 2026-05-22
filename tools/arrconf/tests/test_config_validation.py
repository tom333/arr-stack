"""D-13 dispositive: confirms ``extra="forbid"`` on Section models rejects
legacy v0.3.0 YAML shape (flat ``*.items`` blocks under generator-fed sections).

The exact error string captured by this test is the **canonical** sample
quoted verbatim in CLAUDE.md's ``## v0.3.0 → v0.4.0 deprecation`` section
(Plan D Task D.1). Do not edit the test's assertions without updating
the doc — they are intentionally coupled.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from arrconf.config import RootConfig


def test_load_config_rejects_legacy_items_field() -> None:
    """A YAML fragment with legacy ``sonarr.main.tags.items`` MUST raise
    ``ValidationError(type='extra_forbidden')`` after Plan B removes the
    ``items`` field from generator-fed Section models.

    The captured error structure is the cross-plan handoff to Plan D Task D.1's
    CLAUDE.md edit (see 12-B SUMMARY's ``## Captured D-13 ValidationError``
    section).
    """
    legacy_shape = {
        "sonarr": {
            "main": {
                "base_url": "http://sonarr.test",
                "tags": {
                    "prune": False,
                    "items": [{"label": "tv"}],  # D-13 trigger: legacy v0.3.0 field
                },
            }
        }
    }

    with pytest.raises(ValidationError) as exc_info:
        RootConfig.model_validate(legacy_shape)

    errors = exc_info.value.errors()
    extra_forbidden = [e for e in errors if e["type"] == "extra_forbidden"]
    assert extra_forbidden, f"expected extra_forbidden error, got: {errors}"

    # The error's location must point at the items field — anchors the
    # CLAUDE.md "field-path resolution" claim.
    paths = [tuple(e["loc"]) for e in extra_forbidden]
    assert any("items" in p for p in paths), f"items not in any error loc: {paths}"
