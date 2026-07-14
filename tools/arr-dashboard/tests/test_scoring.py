from pathlib import Path

import pytest

from arr_dashboard.scoring import load_scoring_intent, score_release

INTENT_YML = """
categories:
  - {name: films, kind: movies, profile: general, display: F, base_path: /media/films}
category_quality_profiles: {general: MULTi.VF, anime: Anime, family: Family}
profile_definitions:
  MULTi.VF:
    body:
      min_format_score: 0
      qualities:
        - {name: Bluray-1080p}
        - {name: WEB 1080p, qualities: [WEBDL-1080p, WEBRip-1080p]}
    custom_formats:
      - {trash_ids: [fr-vff]}
      - {trash_ids: [fr-x265-hd]}
      - {trash_ids: [fr-vostfr], score: -10000}
  Anime:
    body:
      min_format_score: 0
      qualities:
        - {name: Bluray-1080p}
        - {name: WEB 1080p, qualities: [WEBDL-1080p, WEBRip-1080p]}
    custom_formats:
      - {trash_ids: [fr-vff]}
      - {trash_ids: [fr-vostfr], score: 50}
configarr:
  customFormatDefinitions:
    - {trash_id: fr-vff, trash_scores: {default: 150}, specifications: [{implementation: ReleaseTitleSpecification, negate: false, required: false, fields: {value: "\\\\b(VFF|TRUEFRENCH)\\\\b"}}]}
    - {trash_id: fr-x265-hd, trash_scores: {default: 800}, specifications: [{implementation: ReleaseTitleSpecification, negate: false, required: true, fields: {value: "\\\\b(x265|hevc)\\\\b"}}, {implementation: ResolutionSpecification, negate: true, required: true, fields: {value: 2160}}]}
    - {trash_id: fr-vostfr, trash_scores: {default: -10000}, specifications: [{implementation: ReleaseTitleSpecification, negate: false, required: false, fields: {value: "\\\\bVOSTFR\\\\b"}}]}
"""


@pytest.fixture
def intent(tmp_path: Path):
    p = tmp_path / "intent.yml"
    p.write_text(INTENT_YML)
    return load_scoring_intent(p)


def test_vff_x265_accepted_and_scored(intent):
    r = score_release(
        "Film.2022.VFF.1080p.BluRay.x265",
        {"resolution": "1080p", "source": "BluRay"},
        "MULTi.VF",
        intent,
    )
    assert r.score == 950  # 150 VFF + 800 x265
    assert r.accepted
    assert r.quality == "Bluray-1080p"


def test_vostfr_rejected_on_multivf(intent):
    r = score_release(
        "Film.2022.VOSTFR.1080p.WEB-DL",
        {"resolution": "1080p", "source": "WEB"},
        "MULTi.VF",
        intent,
    )
    assert r.score <= -10000
    assert not r.accepted


def test_vostfr_positive_on_anime(intent):
    r = score_release(
        "Film.2022.VOSTFR.1080p.WEB-DL", {"resolution": "1080p", "source": "WEB"}, "Anime", intent
    )
    assert r.score == 50
    assert r.accepted


def test_2160p_rejected_quality_not_allowed(intent):
    r = score_release(
        "Film.2022.VFF.2160p.BluRay.x265",
        {"resolution": "2160p", "source": "BluRay"},
        "MULTi.VF",
        intent,
    )
    assert not r.accepted  # Bluray-2160p not in allowed qualities
