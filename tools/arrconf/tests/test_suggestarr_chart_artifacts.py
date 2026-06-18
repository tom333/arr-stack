"""Phase 14 Plan 03 — chart-artifacts integration test (revision-2 narrowed scope per D-10).

Scope:
  (a) D-01 env remap correctness in values.yaml
      suggestarr.controllers.main.containers.main.env
  (b) D-09 Renovate annotation present + correct format (docker.io/ciuse99/suggestarr)
  (c) D-14 NO ingress block under suggestarr
  (d) SuggestArr alias listed in Chart.yaml dependencies (Plan 01 deliverable)
  (e) charts/arr-stack/charts/suggestarr/Chart.yaml exists (unpacked dependency, Plan 01)
  (f) helm template emits Deployment + PVC + Service for SuggestArr AND does NOT
      emit a ConfigMap named suggestarr-config
  (g) PVC declared with 1Gi capacity

Does NOT exercise the SuggestArr daemon runtime — that's covered by 14-HUMAN-UAT.md
Scenario 3 (operator-driven post-deploy verification via web UI + Seerr request
observation).

Does NOT assert on SEER_ANIME_PROFILE_CONFIG or JELLYFIN_LIBRARIES content — those
values are configured by the operator via the SuggestArr web UI POST-DEPLOY (per
13-RESEARCH lines 488 / 492-494). The values to enter are recorded in
.planning/phases/14-suggestarr-implementation/evidence/derived-routing-values.md
(Plan 02 Task 2.1 output) and consumed by 14-HUMAN-UAT.md Scenario 3.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ruyaml import YAML as _YAML

REPO_ROOT = Path(__file__).resolve().parents[3]
VALUES_YAML = REPO_ROOT / "charts" / "arr-stack" / "values.yaml"
CHART_YAML = REPO_ROOT / "charts" / "arr-stack" / "Chart.yaml"
SUGGESTARR_DEP_CHART = REPO_ROOT / "charts" / "arr-stack" / "charts" / "suggestarr" / "Chart.yaml"
VALUES_PROD = REPO_ROOT / "examples" / "values-prod.yaml"

# D-01 env remap expectations: SuggestArr-expected env name → arrconf-env secret key name
EXPECTED_ENV_REMAP = {
    "JELLYFIN_TOKEN": "JELLYFIN_API_KEY",
    "SEER_TOKEN": "SEERR_API_KEY",
    "TMDB_API_KEY": "TMDB_API_KEY",
}

# arrconf-env expected keys per CLAUDE.md §"Variables d'environnement" + D-02 TMDB_API_KEY add
EXPECTED_ARRCONF_ENV_KEYS = {
    "SONARR_API_KEY",
    "RADARR_API_KEY",
    "PROWLARR_API_KEY",
    "QBT_USER",
    "QBT_PASS",
    "SEERR_API_KEY",
    "JELLYFIN_API_KEY",
    "TMDB_API_KEY",
}

_yaml = _YAML(typ="safe")


def _load_yaml(path: Path) -> dict:  # type: ignore[type-arg]
    with path.open() as fh:
        return _yaml.load(fh)  # type: ignore[no-any-return]


def _helm_template_docs() -> list[dict]:  # type: ignore[type-arg]
    """Run `helm template` and return parsed multi-doc YAML output.

    Skips if helm unavailable.
    """
    if not shutil.which("helm"):
        import pytest

        pytest.skip("helm CLI not available on PATH — skipping helm-template-dependent assertion")
    result = subprocess.run(
        [
            "helm",
            "template",
            str(REPO_ROOT / "charts" / "arr-stack"),
            "-f",
            str(VALUES_PROD),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    docs: list[dict] = []  # type: ignore[type-arg]
    for doc in _yaml.load_all(result.stdout):
        if doc is not None:
            docs.append(doc)
    return docs


# ----- (a) D-01: env remap correctness -----


def test_d01_env_remap_jellyfin_token_to_jellyfin_api_key() -> None:
    values = _load_yaml(VALUES_YAML)
    env_list = values["suggestarr"]["controllers"]["main"]["containers"]["main"]["env"]
    entry = next(
        (e for e in env_list if isinstance(e, dict) and e.get("name") == "JELLYFIN_TOKEN"),
        None,
    )
    assert entry is not None, "JELLYFIN_TOKEN env var not declared (D-01 remap broken)"
    ref = entry["valueFrom"]["secretKeyRef"]
    assert ref["name"] == "arrconf-env", f"unexpected secretKeyRef.name={ref['name']!r}"
    assert ref["key"] == "JELLYFIN_API_KEY", (
        f"D-01 remap drift: JELLYFIN_TOKEN should map to JELLYFIN_API_KEY, got {ref['key']!r}"
    )


def test_d01_env_remap_seer_token_to_seerr_api_key() -> None:
    values = _load_yaml(VALUES_YAML)
    env_list = values["suggestarr"]["controllers"]["main"]["containers"]["main"]["env"]
    entry = next(
        (e for e in env_list if isinstance(e, dict) and e.get("name") == "SEER_TOKEN"),
        None,
    )
    assert entry is not None, "SEER_TOKEN env var not declared (D-01 remap broken)"
    ref = entry["valueFrom"]["secretKeyRef"]
    assert ref["name"] == "arrconf-env"
    assert ref["key"] == "SEERR_API_KEY", (
        f"D-01 remap drift: SEER_TOKEN should map to SEERR_API_KEY, got {ref['key']!r}"
    )


def test_d01_env_remap_tmdb_api_key_direct() -> None:
    values = _load_yaml(VALUES_YAML)
    env_list = values["suggestarr"]["controllers"]["main"]["containers"]["main"]["env"]
    entry = next(
        (e for e in env_list if isinstance(e, dict) and e.get("name") == "TMDB_API_KEY"),
        None,
    )
    assert entry is not None, "TMDB_API_KEY env var not declared (D-01/D-02 broken)"
    ref = entry["valueFrom"]["secretKeyRef"]
    assert ref["name"] == "arrconf-env"
    assert ref["key"] == "TMDB_API_KEY", (
        f"D-01: TMDB_API_KEY should be direct-named, got {ref['key']!r}"
    )


def test_all_secret_refs_target_arrconf_env_with_expected_keys() -> None:
    """Every secretKeyRef under suggestarr.env must use arrconf-env + an expected key.

    No surprise secret references — guards against D-01 remap drift.
    """
    values = _load_yaml(VALUES_YAML)
    env_list = values["suggestarr"]["controllers"]["main"]["containers"]["main"]["env"]
    secret_refs = [
        e
        for e in env_list
        if isinstance(e, dict) and "valueFrom" in e and "secretKeyRef" in e["valueFrom"]
    ]
    assert secret_refs, "no secretKeyRef entries found under suggestarr.env"
    for entry in secret_refs:
        ref = entry["valueFrom"]["secretKeyRef"]
        assert ref["name"] == "arrconf-env", (
            f"secretKeyRef.name={ref['name']!r} — expected 'arrconf-env' (D-01)"
        )
        assert ref["key"] in EXPECTED_ARRCONF_ENV_KEYS, (
            f"secretKeyRef.key={ref['key']!r} not in expected arrconf-env keys"
        )


# ----- (b) D-09: Renovate annotation -----


def test_d09_renovate_annotation_present_and_correctly_formatted() -> None:
    """Annotation must be on the line IMMEDIATELY above 'repository: ciuse99/suggestarr'.

    Per CLAUDE.md critical rule: the Renovate annotation line must be the line
    immediately preceding the repository: line.
    """
    text = VALUES_YAML.read_text()
    lines = text.splitlines()
    repo_line_idx = next(
        (
            i
            for i, line in enumerate(lines)
            if "ciuse99/suggestarr" in line and "repository:" in line
        ),
        None,
    )
    assert repo_line_idx is not None, "repository: ciuse99/suggestarr not found in values.yaml"
    assert repo_line_idx > 0, "repository: line at index 0 — no room for annotation above it"
    annotation_line = lines[repo_line_idx - 1].strip()
    expected = "# renovate: image=docker.io/ciuse99/suggestarr"
    assert annotation_line == expected, (
        f"D-09 Renovate annotation malformed or absent on line above repository:. "
        f"Got: {annotation_line!r}; expected: {expected!r}"
    )


# ----- (c) D-14: NO ingress block -----


def test_d14_no_ingress_block_under_suggestarr() -> None:
    values = _load_yaml(VALUES_YAML)
    assert "ingress" not in values["suggestarr"], (
        "suggestarr: has an ingress block — D-14 forbids it (web UI stays cluster-internal-only)"
    )


# ----- (d) Chart.yaml alias listed -----


def test_d_suggestarr_alias_listed_in_chart_yaml() -> None:
    chart = _load_yaml(CHART_YAML)
    aliases = [d.get("alias") for d in chart.get("dependencies", []) if isinstance(d, dict)]
    assert "suggestarr" in aliases, (
        f"suggestarr alias missing from Chart.yaml dependencies. Found aliases: {aliases}"
    )


def test_d_chart_yaml_has_exactly_15_aliases() -> None:
    """Sanity: 10 base + suggestarr (P14) + cross-seed (P30) + qbit-manage (P31)
    + arrconf-mcp + arr-dashboard."""
    chart = _load_yaml(CHART_YAML)
    aliases = [d.get("alias") for d in chart.get("dependencies", []) if isinstance(d, dict)]
    assert len(aliases) == 15, (
        f"expected 15 aliases (10 base + suggestarr + cross-seed + qbit-manage "
        f"+ arrconf-mcp + arr-dashboard), found {len(aliases)}: {aliases}"
    )


# ----- (e) Unpacked dependency directory exists -----


def test_e_suggestarr_dep_dir_unpacked() -> None:
    """Plan 01 unpack step (Helm 4 multi-alias workaround) must have created the dir."""
    assert SUGGESTARR_DEP_CHART.is_file(), (
        f"missing: {SUGGESTARR_DEP_CHART} — "
        "Plan 01 unpack step (Helm 4 multi-alias workaround) skipped or broken"
    )
    dep_chart = _load_yaml(SUGGESTARR_DEP_CHART)
    assert dep_chart.get("name") == "app-template", (
        f"unexpected name: {dep_chart.get('name')!r} (expected 'app-template')"
    )


# ----- (f) helm template emits expected kinds AND no suggestarr-config ConfigMap -----


def test_f_helm_template_emits_suggestarr_deployment() -> None:
    docs = _helm_template_docs()
    deployments = [
        d
        for d in docs
        if d.get("kind") == "Deployment" and d.get("metadata", {}).get("name") == "suggestarr"
    ]
    assert len(deployments) == 1, (
        f"expected exactly 1 Deployment named 'suggestarr', found {len(deployments)}"
    )
    image = deployments[0]["spec"]["template"]["spec"]["containers"][0]["image"]
    assert "ciuse99/suggestarr" in image, f"unexpected image: {image!r}"


def test_f_helm_template_emits_suggestarr_pvc() -> None:
    docs = _helm_template_docs()
    pvcs = [
        d
        for d in docs
        if d.get("kind") == "PersistentVolumeClaim"
        and "suggestarr" in d.get("metadata", {}).get("name", "")
    ]
    assert pvcs, (
        "no PersistentVolumeClaim with 'suggestarr' in its name found in helm template output"
    )


def test_f_helm_template_emits_suggestarr_service() -> None:
    docs = _helm_template_docs()
    services = [
        d
        for d in docs
        if d.get("kind") == "Service" and d.get("metadata", {}).get("name") == "suggestarr"
    ]
    assert len(services) == 1, (
        f"expected exactly 1 Service named 'suggestarr', found {len(services)}"
    )


def test_f_helm_template_does_not_emit_suggestarr_config_configmap() -> None:
    """Revision-2 negative assertion: SuggestArr does NOT receive a ConfigMap.

    Per 13-RESEARCH line 488: the original revision-1 plan invented a
    `templates/suggestarr-configmap.yaml` that SuggestArr silently ignored at
    runtime. Revision-2 deleted that mechanism — this test enforces the deletion.
    """
    docs = _helm_template_docs()
    suggestarr_configmaps = [
        d
        for d in docs
        if d.get("kind") == "ConfigMap" and d.get("metadata", {}).get("name") == "suggestarr-config"
    ]
    assert not suggestarr_configmaps, (
        f"unexpected ConfigMap named 'suggestarr-config' rendered "
        f"({len(suggestarr_configmaps)} found). "
        "Per 13-RESEARCH line 488, SuggestArr's config persists in its "
        "PVC-backed SQLite/YAML and is configured via the web UI post-deploy — "
        "no ConfigMap should be rendered. If this test fails, someone "
        "re-introduced the deleted ConfigMap mechanism."
    )


def test_f_no_suggestarr_configmap_template_file_in_repo() -> None:
    """Revision-2: belt-and-suspenders — no template file or source file in repo."""
    cm_template = REPO_ROOT / "charts" / "arr-stack" / "templates" / "suggestarr-configmap.yaml"
    cm_source = REPO_ROOT / "charts" / "arr-stack" / "files" / "suggestarr-config.yml"
    assert not cm_template.exists(), (
        f"{cm_template} should NOT exist (revision-2 deletion); see 13-RESEARCH line 488"
    )
    assert not cm_source.exists(), (
        f"{cm_source} should NOT exist (revision-2 deletion); see 13-RESEARCH line 488"
    )


# ----- (g) PVC sized 1Gi -----


def test_g_pvc_declared_1gi() -> None:
    """PVC size assertion against values.yaml — helm-template-independent (works without helm)."""
    values = _load_yaml(VALUES_YAML)
    pvc_block = values["suggestarr"]["persistence"]["config"]
    assert pvc_block["type"] == "persistentVolumeClaim", (
        f"persistence.config.type={pvc_block.get('type')!r} — expected 'persistentVolumeClaim'"
    )
    assert pvc_block["size"] == "1Gi", (
        f"persistence.config.size={pvc_block.get('size')!r} — expected '1Gi'"
    )
    assert pvc_block.get("accessMode") == "ReadWriteOnce", (
        f"persistence.config.accessMode={pvc_block.get('accessMode')!r} — expected 'ReadWriteOnce'"
    )
