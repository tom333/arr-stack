"""Task 2 wiring + ordering test for category-tag enforcement.

Proves that ``apply`` calls ``reconcile_category_tags`` for BOTH Sonarr and
Radarr as the FINAL tagging step — after the per-app reconcile/profile steps.
(The legacy SAGAS-04 Sonarr series-tagging sub-step was removed in Task 3;
title tags are now owned exclusively by ``reconcile_category_tags``.)

Approach (lightest reliable): monkeypatch the lazily-imported call-site
functions on their source modules so they record an ordered call log instead of
hitting HTTP. ``SonarrClient``/``RadarrClient`` constructors do no I/O, so the
apply flow runs end-to-end without respx. We then assert ordering on the log.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import arrconf.__main__ as main_mod
import arrconf.reconcilers._category_profiles as cp_mod
import arrconf.reconcilers._category_tags as ct_mod
import arrconf.reconcilers.radarr as radarr_mod
import arrconf.reconcilers.sonarr as sonarr_mod
from arrconf.__main__ import app

runner = CliRunner()


@pytest.fixture
def arrconf_yml(tmp_path: Path) -> Path:
    cfg = tmp_path / "arrconf.yml"
    cfg.write_text(
        "sonarr:\n"
        "  main:\n"
        "    base_url: http://sonarr.test:8989\n"
        "radarr:\n"
        "  main:\n"
        "    base_url: http://radarr.test:7878\n",
        encoding="utf-8",
    )
    return cfg


@pytest.fixture
def intent_yml(tmp_path: Path) -> Path:
    intent = tmp_path / "intent.yml"
    intent.write_text(
        "categories:\n"
        "  - name: series\n"
        "    kind: series\n"
        "    profile: general\n"
        "    display: Series\n"
        "    base_path: /media/series\n"
        "  - name: films\n"
        "    kind: movies\n"
        "    profile: general\n"
        "    display: Films\n"
        "    base_path: /media/films\n"
        "sagas:\n"
        "  - name: Some Series Saga\n"
        "    kind: series\n",  # empty items -> SAGAS-04 runs but skips GET /series
        encoding="utf-8",
    )
    return intent


def test_category_tags_runs_for_both_apps_after_sagas(
    arrconf_yml: Path,
    intent_yml: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    kinds_seen: dict[str, set[str]] = {}

    def fake_reconcile_sonarr(client: Any, *a: Any, **kw: Any) -> sonarr_mod.SonarrResult:
        order.append("sonarr_reconcile")
        return sonarr_mod.SonarrResult()

    def fake_reconcile_radarr(client: Any, *a: Any, **kw: Any) -> radarr_mod.RadarrResult:
        order.append("radarr_reconcile")
        return radarr_mod.RadarrResult()

    def fake_profiles(client: Any, *a: Any, **kw: Any) -> list[str]:
        order.append("category_profiles")
        return []

    def fake_category_tags(
        client: Any,
        categories: Any,
        *,
        item_path: str,
        editor_path: str,
        ids_key: str,
        dry_run: bool,
    ) -> list[str]:
        order.append(f"category_tags:{item_path}")
        kinds_seen[item_path] = {c.kind for c in categories}
        return []

    # reconcile_sonarr/reconcile_radarr are imported at __main__ top level ->
    # patch on the __main__ namespace. The rest are lazily imported inside the
    # apply body -> patch on their source modules.
    monkeypatch.setattr(main_mod, "reconcile_sonarr", fake_reconcile_sonarr)
    monkeypatch.setattr(main_mod, "reconcile_radarr", fake_reconcile_radarr)
    monkeypatch.setattr(cp_mod, "reconcile_category_profiles", fake_profiles)
    monkeypatch.setattr(ct_mod, "reconcile_category_tags", fake_category_tags)

    result = runner.invoke(
        app,
        [
            "--config",
            str(arrconf_yml),
            "--intent",
            str(intent_yml),
            "apply",
            "--apps",
            "sonarr,radarr",
        ],
        env={
            "SONARR_API_KEY": "fake",
            "RADARR_API_KEY": "fake",
            "QBT_USER": "u",
            "QBT_PASS": "p",
        },
        catch_exceptions=False,
    )

    assert result.exit_code == 0, f"exit {result.exit_code}\n{result.output}"

    # Both apps invoked the final category-tags step.
    assert "category_tags:/series" in order, order
    assert "category_tags:/movie" in order, order

    # Category-tags runs after the per-app reconcile + profile steps (FINAL tagging step).
    assert order.index("category_tags:/series") > order.index("sonarr_reconcile"), order
    assert order.index("category_tags:/movie") > order.index("radarr_reconcile"), order

    # Each app receives ONLY its own kind of category (kind-filter at call site):
    # mixed cats must NOT leak movie tags into Sonarr (regression: a Radarr-only
    # 'films' tag is absent from Sonarr's /tag → ConfigError on apply).
    assert kinds_seen["/series"] == {"series"}, kinds_seen
    assert kinds_seen["/movie"] == {"movies"}, kinds_seen
