"""Pure quality-profile scorer, driven by intent.yml (single source of truth).

Replicates the custom-format scoring that configarr/Radarr apply: each CF regex is
matched against a release title, per-profile scores are summed, and a quality
allow-list + min_format_score cutoff decide acceptance. NOT the full Radarr parser —
the definitive decision stays in Radarr at grab time (spec Section 2 limitation).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from arrconf.intent_config import load_intent


@dataclass(frozen=True)
class ScoringIntent:
    """Extracted, precompiled scoring inputs from an IntentConfig."""

    cf_specs: dict[str, dict[str, Any]]
    profiles: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class ScoreResult:
    score: int
    accepted: bool
    quality: str | None
    reasons: list[str]


def _quality_bucket(resolution: str | None, source: str | None) -> str | None:
    """Map parsed (resolution, source) to a Radarr quality leaf name."""
    if not resolution or not source:
        return None
    res = resolution.lower()
    src = source.upper().replace("-", "")
    res_tag = {"2160p": "2160p", "1080p": "1080p", "720p": "720p", "480p": "480p"}.get(res)
    if res_tag is None:
        return None
    if src == "BLURAY":
        return f"Bluray-{res_tag}"
    if src == "REMUX":
        return f"Remux-{res_tag}"
    if src == "HDTV":
        return f"HDTV-{res_tag}"
    if src in ("WEB", "WEBDL"):
        return f"WEBDL-{res_tag}"
    if src == "WEBRIP":
        return f"WEBRip-{res_tag}"
    return None


def load_scoring_intent(path: Path) -> ScoringIntent:
    intent = load_intent(path)

    cf_specs: dict[str, dict[str, Any]] = {}
    for cf in intent.configarr.get("customFormatDefinitions", []):
        tid = cf["trash_id"]
        compiled = []
        for spec in cf.get("specifications", []):
            impl = spec.get("implementation")
            val = spec.get("fields", {}).get("value")
            entry: dict[str, Any] = {
                "impl": impl,
                "negate": bool(spec.get("negate", False)),
                "required": bool(spec.get("required", False)),
            }
            if impl == "ReleaseTitleSpecification":
                entry["rx"] = re.compile(str(val), re.IGNORECASE)
            elif impl == "ResolutionSpecification":
                entry["res"] = int(val)
            compiled.append(entry)
        cf_specs[tid] = {
            "default": int(cf.get("trash_scores", {}).get("default", 0)),
            "specs": compiled,
        }

    profiles: dict[str, dict[str, Any]] = {}
    for name, pdef in intent.profile_definitions.items():
        cf_scores: dict[str, int] = {}
        for ref in pdef.custom_formats:
            for tid in ref.trash_ids:
                cf_scores[tid] = (
                    ref.score if ref.score is not None else cf_specs.get(tid, {}).get("default", 0)
                )
        allowed: set[str] = set()
        for q in pdef.body.get("qualities", []):
            if "qualities" in q:
                allowed.update(q["qualities"])
            else:
                allowed.add(q["name"])
        profiles[name] = {
            "cf_scores": cf_scores,
            "allowed": allowed,
            "min": int(pdef.body.get("min_format_score", 0)),
        }
    return ScoringIntent(cf_specs=cf_specs, profiles=profiles)


def _cf_matches(specs: list[dict[str, Any]], title: str, resolution: str | None) -> bool:
    """A CF matches when every REQUIRED spec matches (after negate). Single-spec
    required=false CFs (the common FR case) match on that spec alone."""
    if not specs:
        return False
    results: list[bool] = []
    for s in specs:
        if s["impl"] == "ReleaseTitleSpecification":
            m = bool(s["rx"].search(title))
        elif s["impl"] == "ResolutionSpecification":
            want = {2160: "2160p", 1080: "1080p", 720: "720p", 480: "480p"}.get(s["res"])
            m = resolution == want
        else:
            m = False
        if s["negate"]:
            m = not m
        if s["required"] and not m:
            return False
        results.append(m)
    return all(results)


def score_release(
    title: str, quality_parsed: dict[str, Any], profile_name: str, intent: ScoringIntent
) -> ScoreResult:
    prof = intent.profiles.get(profile_name)
    if prof is None:
        return ScoreResult(
            score=0, accepted=False, quality=None, reasons=[f"unknown profile {profile_name}"]
        )

    resolution = quality_parsed.get("resolution")
    source = quality_parsed.get("source")
    bucket = _quality_bucket(resolution, source)

    score = 0
    reasons: list[str] = []
    for tid, per_profile_score in prof["cf_scores"].items():
        spec = intent.cf_specs.get(tid)
        if not spec:
            continue
        if _cf_matches(spec["specs"], title, resolution):
            score += per_profile_score
            reasons.append(f"{'+' if per_profile_score >= 0 else ''}{per_profile_score} {tid}")

    quality_allowed = bucket is not None and bucket in prof["allowed"]
    accepted = quality_allowed and score >= prof["min"]
    if not quality_allowed:
        reasons.append(f"quality {bucket or 'unknown'} not allowed")
    return ScoreResult(score=score, accepted=accepted, quality=bucket, reasons=reasons)
