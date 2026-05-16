"""Tests for content_tags step on Sonarr + Radarr reconcilers — Phase 6 (D-06-RETAG-01).

Genre-keyword-driven retagger. Runs as step 10 (AFTER series_tags / movie_tags).
Idempotence: items already carrying the rule's tag are excluded from the editor PUT body.

Pitfall 5 (research): keyword lists are conservative.
- Sonarr family: ['Family', 'Kids', 'Children']  (NOT 'Animation' — catches anime)
- Sonarr anime:  ['Anime']                        (TVDB first-class genre)
- Radarr family: ['Family'] only
- Radarr anime:  NO RULE                 (TMDB has no 'Anime'; 'Animation' catches Disney/Pixar)

Coverage gate: >= 80% on _reconcile_content_tags in both sonarr.py and radarr.py.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

from arrconf.client_base import RadarrClient, SonarrClient
from arrconf.config import (
    ContentRoutingRule,
    ContentRoutingSection,
    RadarrInstance,
    SonarrInstance,
)
from arrconf.exceptions import ReconcileError
from arrconf.reconcilers.radarr import _reconcile_content_tags as radarr_content_tags
from arrconf.reconcilers.sonarr import _reconcile_content_tags as sonarr_content_tags
from arrconf.resources.sonarr.tag import Tag

SONARR_BASE = "http://sonarr.test"
RADARR_BASE = "http://radarr.test"


def _tag(id_: int, label: str) -> Tag:
    return Tag(id=id_, label=label)


def _series(
    id_: int, title: str, genres: list[str], tags: list[int] | None = None
) -> dict[str, Any]:
    return {"id": id_, "title": title, "genres": genres, "tags": tags or []}


def _movie(
    id_: int, title: str, genres: list[str], tags: list[int] | None = None
) -> dict[str, Any]:
    return {"id": id_, "title": title, "genres": genres, "tags": tags or []}


def _sonarr_client() -> SonarrClient:
    return SonarrClient(base_url=SONARR_BASE, api_key="key")


def _radarr_client() -> RadarrClient:
    return RadarrClient(base_url=RADARR_BASE, api_key="key")


# ---------------------------------------------------------------------------
# Sonarr — family rule
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=f"{SONARR_BASE}/api/v3", assert_all_called=False)
def test_sonarr_family_match_tags_series_with_family_genre(
    respx_mock: respx.MockRouter,
) -> None:
    """Series with genres=['Family', 'Comedy'] → editor PUT with the series id + family tag."""
    all_tags = [_tag(1, "tv"), _tag(2, "family"), _tag(3, "anime")]
    cluster_series = [
        _series(10, "Family Show", ["Family", "Comedy"]),
        _series(11, "Drama Show", ["Drama"]),
    ]
    respx_mock.get("/series").mock(return_value=httpx.Response(200, json=cluster_series))
    editor_route = respx_mock.put("/series/editor").mock(return_value=httpx.Response(202, json={}))

    section = ContentRoutingSection(
        enable=True,
        rules=[ContentRoutingRule(tag="family", keywords=["Family", "Kids", "Children"])],
    )

    actions = sonarr_content_tags(_sonarr_client(), section, all_tags, dry_run=False)

    assert editor_route.call_count == 1
    body = json.loads(editor_route.calls[0].request.content)
    assert body["seriesIds"] == [10]
    assert body["tags"] == [2]  # family tag id
    assert body["applyTags"] == "add"
    assert body["moveFiles"] is False
    assert body["deleteFiles"] is False
    assert "content_tags:family:applied:1" in actions


@pytest.mark.respx(base_url=f"{SONARR_BASE}/api/v3", assert_all_called=False)
def test_sonarr_anime_match_tags_series_with_anime_genre(
    respx_mock: respx.MockRouter,
) -> None:
    """Series with genres=['Anime'] → editor PUT with anime tag."""
    all_tags = [_tag(1, "tv"), _tag(2, "family"), _tag(3, "anime")]
    cluster_series = [_series(20, "Cowboy Bebop", ["Anime", "Action"])]
    respx_mock.get("/series").mock(return_value=httpx.Response(200, json=cluster_series))
    editor_route = respx_mock.put("/series/editor").mock(return_value=httpx.Response(202, json={}))

    section = ContentRoutingSection(
        enable=True,
        rules=[ContentRoutingRule(tag="anime", keywords=["Anime"])],
    )

    sonarr_content_tags(_sonarr_client(), section, all_tags, dry_run=False)

    body = json.loads(editor_route.calls[0].request.content)
    assert body["seriesIds"] == [20]
    assert body["tags"] == [3]  # anime tag id


@pytest.mark.respx(base_url=f"{SONARR_BASE}/api/v3", assert_all_called=False)
def test_sonarr_no_genre_match_skips(respx_mock: respx.MockRouter) -> None:
    """Series with genres=['Drama', 'Crime'] — no match for family or anime rules → 0 PUTs."""
    all_tags = [_tag(1, "tv"), _tag(2, "family"), _tag(3, "anime")]
    cluster_series = [_series(30, "Pure Drama", ["Drama", "Crime"])]
    respx_mock.get("/series").mock(return_value=httpx.Response(200, json=cluster_series))
    editor_route = respx_mock.put("/series/editor").mock(return_value=httpx.Response(202, json={}))

    section = ContentRoutingSection(
        enable=True,
        rules=[
            ContentRoutingRule(tag="family", keywords=["Family", "Kids", "Children"]),
            ContentRoutingRule(tag="anime", keywords=["Anime"]),
        ],
    )

    actions = sonarr_content_tags(_sonarr_client(), section, all_tags, dry_run=False)

    assert editor_route.call_count == 0
    assert actions == []


@pytest.mark.respx(base_url=f"{SONARR_BASE}/api/v3", assert_all_called=False)
def test_sonarr_already_tagged_is_idempotent_noop(respx_mock: respx.MockRouter) -> None:
    """SC#5 mirror — series already carrying the family tag → 0 PUTs (idempotent)."""
    all_tags = [_tag(1, "tv"), _tag(2, "family")]
    cluster_series = [_series(40, "Already Tagged", ["Family"], tags=[2])]
    respx_mock.get("/series").mock(return_value=httpx.Response(200, json=cluster_series))
    editor_route = respx_mock.put("/series/editor").mock(return_value=httpx.Response(202, json={}))

    section = ContentRoutingSection(
        enable=True,
        rules=[ContentRoutingRule(tag="family", keywords=["Family"])],
    )

    sonarr_content_tags(_sonarr_client(), section, all_tags, dry_run=False)
    assert editor_route.call_count == 0


@pytest.mark.respx(base_url=f"{SONARR_BASE}/api/v3", assert_all_called=False)
def test_sonarr_multi_tag_family_plus_anime_coexist(respx_mock: respx.MockRouter) -> None:
    """genres=[Family, Anime] → 2 PUTs (one per rule), series in BOTH bodies."""
    all_tags = [_tag(1, "tv"), _tag(2, "family"), _tag(3, "anime")]
    cluster_series = [_series(50, "Anime For Kids", ["Family", "Anime"])]
    respx_mock.get("/series").mock(return_value=httpx.Response(200, json=cluster_series))
    editor_route = respx_mock.put("/series/editor").mock(return_value=httpx.Response(202, json={}))

    section = ContentRoutingSection(
        enable=True,
        rules=[
            ContentRoutingRule(tag="family", keywords=["Family", "Kids", "Children"]),
            ContentRoutingRule(tag="anime", keywords=["Anime"]),
        ],
    )

    sonarr_content_tags(_sonarr_client(), section, all_tags, dry_run=False)

    assert editor_route.call_count == 2
    bodies = [json.loads(c.request.content) for c in editor_route.calls]
    family_body = next(b for b in bodies if b["tags"] == [2])
    anime_body = next(b for b in bodies if b["tags"] == [3])
    assert family_body["seriesIds"] == [50]
    assert anime_body["seriesIds"] == [50]


@pytest.mark.respx(base_url=f"{SONARR_BASE}/api/v3", assert_all_called=False)
def test_sonarr_case_insensitive_genre_match(respx_mock: respx.MockRouter) -> None:
    """Lowercase genre 'family' matches 'Family' keyword (case-insensitive)."""
    all_tags = [_tag(1, "tv"), _tag(2, "family")]
    cluster_series = [_series(60, "Lower Case Genre", ["family"])]
    respx_mock.get("/series").mock(return_value=httpx.Response(200, json=cluster_series))
    editor_route = respx_mock.put("/series/editor").mock(return_value=httpx.Response(202, json={}))

    section = ContentRoutingSection(
        enable=True,
        rules=[ContentRoutingRule(tag="family", keywords=["Family"])],
    )

    sonarr_content_tags(_sonarr_client(), section, all_tags, dry_run=False)
    assert editor_route.call_count == 1


@pytest.mark.respx(base_url=f"{SONARR_BASE}/api/v3", assert_all_called=False)
def test_sonarr_animation_does_not_match_family(respx_mock: respx.MockRouter) -> None:
    """Pitfall 5: 'Animation' MUST NOT match the family rule (catches anime/Pixar otherwise)."""
    all_tags = [_tag(1, "tv"), _tag(2, "family")]
    cluster_series = [_series(70, "Just Animation", ["Animation"])]
    respx_mock.get("/series").mock(return_value=httpx.Response(200, json=cluster_series))
    editor_route = respx_mock.put("/series/editor").mock(return_value=httpx.Response(202, json={}))

    section = ContentRoutingSection(
        enable=True,
        rules=[ContentRoutingRule(tag="family", keywords=["Family", "Kids", "Children"])],
    )

    sonarr_content_tags(_sonarr_client(), section, all_tags, dry_run=False)
    assert editor_route.call_count == 0, "Pitfall 5: 'Animation' MUST NOT match family"


@pytest.mark.respx(base_url=f"{SONARR_BASE}/api/v3", assert_all_called=False)
def test_content_routing_disabled_skips(respx_mock: respx.MockRouter) -> None:
    """section.enable=False → no GET on /series, returns []."""
    all_tags = [_tag(1, "tv"), _tag(2, "family")]
    get_route = respx_mock.get("/series").mock(return_value=httpx.Response(200, json=[]))
    section = ContentRoutingSection(enable=False, rules=[])
    sonarr_content_tags(_sonarr_client(), section, all_tags, dry_run=False)
    assert get_route.call_count == 0


@pytest.mark.respx(base_url=f"{SONARR_BASE}/api/v3", assert_all_called=False)
def test_unknown_rule_tag_raises_ReconcileError(respx_mock: respx.MockRouter) -> None:
    """rule.tag='family' but no tag with label 'family' exists → ReconcileError."""
    all_tags = [_tag(1, "tv")]  # no 'family' tag
    respx_mock.get("/series").mock(return_value=httpx.Response(200, json=[]))
    section = ContentRoutingSection(
        enable=True,
        rules=[ContentRoutingRule(tag="family", keywords=["Family"])],
    )
    with pytest.raises(ReconcileError, match="rule.tag 'family' not found"):
        sonarr_content_tags(_sonarr_client(), section, all_tags, dry_run=False)


@pytest.mark.respx(base_url=f"{SONARR_BASE}/api/v3", assert_all_called=False)
def test_sonarr_dry_run_skips_put(respx_mock: respx.MockRouter) -> None:
    """dry_run=True → no PUT issued, returns dry_run action string."""
    all_tags = [_tag(1, "tv"), _tag(2, "family")]
    cluster_series = [_series(80, "Family Series", ["Family"])]
    respx_mock.get("/series").mock(return_value=httpx.Response(200, json=cluster_series))
    editor_route = respx_mock.put("/series/editor").mock(return_value=httpx.Response(202, json={}))

    section = ContentRoutingSection(
        enable=True,
        rules=[ContentRoutingRule(tag="family", keywords=["Family"])],
    )

    actions = sonarr_content_tags(_sonarr_client(), section, all_tags, dry_run=True)

    assert editor_route.call_count == 0
    assert "content_tags:family:dry_run:1" in actions


# ---------------------------------------------------------------------------
# Radarr — mirror tests
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_radarr_family_match_tags_movie_with_family_genre(
    respx_mock: respx.MockRouter,
) -> None:
    """Movie with genres=['Animation', 'Family', 'Musical'] → editor PUT with movieIds."""
    all_tags = [_tag(1, "movies"), _tag(2, "family")]
    cluster_movies = [
        _movie(100, "Frozen", ["Animation", "Family", "Musical"]),
        _movie(101, "Pure Drama", ["Drama"]),
    ]
    respx_mock.get("/movie").mock(return_value=httpx.Response(200, json=cluster_movies))
    editor_route = respx_mock.put("/movie/editor").mock(return_value=httpx.Response(202, json={}))

    section = ContentRoutingSection(
        enable=True,
        rules=[ContentRoutingRule(tag="family", keywords=["Family"])],
    )

    radarr_content_tags(_radarr_client(), section, all_tags, dry_run=False)

    body = json.loads(editor_route.calls[0].request.content)
    assert body["movieIds"] == [100]
    assert body["tags"] == [2]
    assert body["applyTags"] == "add"
    assert body["moveFiles"] is False
    assert body["deleteFiles"] is False
    assert body["addImportExclusion"] is False  # Radarr-specific (Phase 5 schema divergence)


def test_radarr_no_anime_rule_by_convention() -> None:
    """Pitfall 5: Radarr default config (Plan 06-06) MUST NOT have an anime rule.

    This test verifies the CONVENTION at the pydantic-model layer. A freshly-
    instantiated RadarrInstance starts with content_routing.rules=[] (Plan 06-02
    default). The architectural decision is enforced by code review + Plan 06-06
    chart static check; this test guards the default contract.
    """
    radarr = RadarrInstance(base_url="http://x")
    assert radarr.content_routing.enable is False
    assert radarr.content_routing.rules == []


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_radarr_movie_editor_body_has_addImportExclusion(
    respx_mock: respx.MockRouter,
) -> None:
    """Phase 5 schema divergence regression — Radarr body uses addImportExclusion (singular)."""
    all_tags = [_tag(1, "movies"), _tag(2, "family")]
    cluster_movies = [_movie(200, "Family Film", ["Family"])]
    respx_mock.get("/movie").mock(return_value=httpx.Response(200, json=cluster_movies))
    editor_route = respx_mock.put("/movie/editor").mock(return_value=httpx.Response(202, json={}))

    section = ContentRoutingSection(
        enable=True,
        rules=[ContentRoutingRule(tag="family", keywords=["Family"])],
    )
    radarr_content_tags(_radarr_client(), section, all_tags, dry_run=False)

    body = editor_route.calls[0].request.content.decode()
    assert "addImportExclusion" in body
    assert "addImportListExclusion" not in body  # Sonarr-shape would have "List" suffix


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_radarr_already_tagged_movie_is_noop(respx_mock: respx.MockRouter) -> None:
    """Radarr idempotence — movie already carrying the family tag → 0 PUTs."""
    all_tags = [_tag(1, "movies"), _tag(2, "family")]
    cluster_movies = [_movie(300, "Already Tagged", ["Family"], tags=[2])]
    respx_mock.get("/movie").mock(return_value=httpx.Response(200, json=cluster_movies))
    editor_route = respx_mock.put("/movie/editor").mock(return_value=httpx.Response(202, json={}))

    section = ContentRoutingSection(
        enable=True,
        rules=[ContentRoutingRule(tag="family", keywords=["Family"])],
    )

    radarr_content_tags(_radarr_client(), section, all_tags, dry_run=False)
    assert editor_route.call_count == 0


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_radarr_no_genre_match_noop(respx_mock: respx.MockRouter) -> None:
    """Radarr: movie with genres=['Action', 'Thriller'] — no match for family → 0 PUTs."""
    all_tags = [_tag(1, "movies"), _tag(2, "family")]
    cluster_movies = [_movie(400, "Action Movie", ["Action", "Thriller"])]
    respx_mock.get("/movie").mock(return_value=httpx.Response(200, json=cluster_movies))
    editor_route = respx_mock.put("/movie/editor").mock(return_value=httpx.Response(202, json={}))

    section = ContentRoutingSection(
        enable=True,
        rules=[ContentRoutingRule(tag="family", keywords=["Family"])],
    )

    actions = radarr_content_tags(_radarr_client(), section, all_tags, dry_run=False)

    assert editor_route.call_count == 0
    assert actions == []


def test_sonarr_no_anime_rule_default_empty() -> None:
    """SonarrInstance defaults: content_routing is disabled with no rules."""
    sonarr = SonarrInstance(base_url="http://x")
    assert sonarr.content_routing.enable is False
    assert sonarr.content_routing.rules == []


# ---------------------------------------------------------------------------
# Coverage gap fillers — ensure >= 80% on _reconcile_content_tags functions
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=f"{SONARR_BASE}/api/v3", assert_all_called=False)
def test_sonarr_enabled_with_no_rules_is_noop(respx_mock: respx.MockRouter) -> None:
    """enable=True but rules=[] → no GET on /series, returns []."""
    all_tags = [_tag(1, "tv")]
    get_route = respx_mock.get("/series").mock(return_value=httpx.Response(200, json=[]))
    section = ContentRoutingSection(enable=True, rules=[])
    actions = sonarr_content_tags(_sonarr_client(), section, all_tags, dry_run=False)
    assert get_route.call_count == 0
    assert actions == []


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_radarr_content_routing_disabled_skips(respx_mock: respx.MockRouter) -> None:
    """Radarr: section.enable=False → no GET on /movie, returns []."""
    all_tags = [_tag(1, "movies"), _tag(2, "family")]
    get_route = respx_mock.get("/movie").mock(return_value=httpx.Response(200, json=[]))
    section = ContentRoutingSection(enable=False, rules=[])
    radarr_content_tags(_radarr_client(), section, all_tags, dry_run=False)
    assert get_route.call_count == 0


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_radarr_enabled_with_no_rules_is_noop(respx_mock: respx.MockRouter) -> None:
    """Radarr: enable=True but rules=[] → no GET on /movie."""
    all_tags = [_tag(1, "movies")]
    get_route = respx_mock.get("/movie").mock(return_value=httpx.Response(200, json=[]))
    section = ContentRoutingSection(enable=True, rules=[])
    actions = radarr_content_tags(_radarr_client(), section, all_tags, dry_run=False)
    assert get_route.call_count == 0
    assert actions == []


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_radarr_unknown_rule_tag_raises_ReconcileError(respx_mock: respx.MockRouter) -> None:
    """Radarr: rule.tag='family' but no tag with label 'family' → ReconcileError."""
    all_tags = [_tag(1, "movies")]  # no 'family' tag
    respx_mock.get("/movie").mock(return_value=httpx.Response(200, json=[]))
    section = ContentRoutingSection(
        enable=True,
        rules=[ContentRoutingRule(tag="family", keywords=["Family"])],
    )
    with pytest.raises(ReconcileError, match="rule.tag 'family' not found"):
        radarr_content_tags(_radarr_client(), section, all_tags, dry_run=False)


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_radarr_dry_run_skips_put(respx_mock: respx.MockRouter) -> None:
    """Radarr: dry_run=True → no PUT issued, returns dry_run action string."""
    all_tags = [_tag(1, "movies"), _tag(2, "family")]
    cluster_movies = [_movie(500, "Family Movie", ["Family"])]
    respx_mock.get("/movie").mock(return_value=httpx.Response(200, json=cluster_movies))
    editor_route = respx_mock.put("/movie/editor").mock(return_value=httpx.Response(202, json={}))

    section = ContentRoutingSection(
        enable=True,
        rules=[ContentRoutingRule(tag="family", keywords=["Family"])],
    )

    actions = radarr_content_tags(_radarr_client(), section, all_tags, dry_run=True)

    assert editor_route.call_count == 0
    assert "content_tags:family:dry_run:1" in actions
