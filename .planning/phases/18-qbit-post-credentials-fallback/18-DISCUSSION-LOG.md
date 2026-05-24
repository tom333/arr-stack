# Phase 18 — qBit POST credentials fallback — DISCUSSION LOG

**Date :** 2026-05-24
**Mode :** discuss (default)
**Workflow :** `/gsd-discuss-phase 18`

## Codebase scout

- `tools/arrconf/arrconf/generators/categories.py:74-87` (`_qbit_dc_fields_sonarr`) + `:98-111` (`_qbit_dc_fields_radarr`) : émettent `FieldKV(name="username", value="")` + `FieldKV(name="password", value="")` hardcodés vides. Le générateur est pur — aucun accès à env.
- `tools/arrconf/arrconf/settings.py:24-25` : `qbt_user`/`qbt_pass` déjà définis comme `SecretStr | None` via pydantic-settings. Lus depuis `QBT_USER` / `QBT_PASS` env vars.
- `tools/arrconf/arrconf/__main__.py:274-281` + `:549-556` : fail-fast pattern existant — `Exit(code=2)` si QBT_USER/QBT_PASS manquent pour le qBit reconciler natif (Phase 5).
- `tools/arrconf/arrconf/reconcilers/sonarr.py:540-556` : step `download_clients` (step_index 6), reçoit `derived.download_clients`, appelle `_resolve_download_client_tag_labels` (transform), puis `reconcile()`. Inject point Phase 18 = entre ces 2 calls.
- `tools/arrconf/arrconf/reconcilers/_shared.py:103` : `_resolve_download_client_tag_labels()` — pattern existant de "transform desired BEFORE reconcile". Phase 18 helper mirrors exactement ce shape.
- `tools/arrconf/arrconf/differ.py:148` : `merge_fields_for_put` SURVIT post-Phase-12 (vérifié). Omits credential fields des UPDATE PUT bodies → cluster preserves stored value → idempotence acquise pour SC#3.
- `tools/arrconf/arrconf/exceptions.py:22` : `ConfigError` already exists (CLI exit code 2).
- `tools/arrconf/arrconf/client_base.py:104-121` : `?forceSave=true` toujours set on *arr v3 UPDATE PUTs (ADR-8). Phase 18 n'a pas besoin d'y toucher.

Finding architectural clé : Phase 18 surface = **CREATE/POST uniquement**. UPDATE/PUT déjà résolu par l'infrastructure Phase 2.1. SC#3 (idempotence) tombe par construction.

## Gray areas identifiées (3)

1. **Inject location** — où placer le code de résolution env → fields[] ?
2. **Missing env behavior** — fail-fast `ConfigError` vs warn-and-continue ?
3. **Scope** — Sonarr-side + Radarr-side ensemble OU Sonarr d'abord seulement ?

## Décisions

### Q1 — Inject location

**Options présentées :**
- Helper dans `_shared.py` (Recommandé)
- Dans `__main__.py` avant reconcile call
- Dans le générateur lui-même

**Choix opérateur :** Helper dans `_shared.py`.

**Notes :** Mirrors le pattern `_resolve_download_client_tag_labels` existant. Garde les générateurs purs (testables sans env). Appelé depuis sonarr.py + radarr.py reconcile steps. DRY entre les 2 callers.

### Q2 — Missing env behavior

**Options présentées :**
- `ConfigError` fail-fast (Recommandé, match REQ SC#2)
- Warn + continue avec empty string

**Choix opérateur :** ConfigError fail-fast.

**Notes :** Match exactly REQ SC#2 + aligned avec qBit reconciler natif (`Exit(code=2)` ligne 281). Le message nomme le DC entry fautif. Pas de silent failure — anti-D-02.2-AUTH-REGRESSION discipline.

### Q3 — Scope

**Options présentées :**
- Sonarr + Radarr ensemble (Recommandé)
- Sonarr only d'abord

**Choix opérateur :** Sonarr + Radarr ensemble.

**Notes :** Le générateur émet déjà `_qbit_dc_fields_sonarr` ET `_qbit_dc_fields_radarr`. Les 2 reconcilers consument la même structure. Une seule fonction helper DRY entre eux. Pas de raison de dupliquer le travail en 2 phases.

## Deferred ideas

- **Helper plus générique pour autres "sensitive empty fields"** (Prowlarr api_key_env equivalent) — Le pattern Phase 18 pourrait être étendu si une future app a besoin d'env-injection pour ses fields[]. Pour l'instant, le helper est qBit-specific. Re-évaluer si Bazarr (v0.6.x candidate) a un besoin similaire.
- **Settings.py changes (e.g. validation qbt_user non-empty au boot)** — non retenu. La validation au reconciler-level est plus précise (par DC entry) et plus tardive (réagit à des env changes runtime).

## Scope creep redirected

Aucun. Discussion strictement focalisée sur env injection pour qBit creds dans download_clients POST.

## Outcome

CONTEXT.md écrit avec 5 D-decisions locked (D-18-INJECT-LOC-01, D-18-FAIL-FAST-01, D-18-SCOPE-01, D-18-IDEMPOTENCE-FREE, D-18-CHART-BUMP-01) + 0 research items (Phase 18 surface assez petite pour skip recherche externe) + 5 HUMAN-UAT scenarios provisionnels.

Plan-phase doit produire 1 plan unique 18-A (1 wave, ~5-6 tasks) couvrant : helper TDD + wiring sonarr/radarr + 4 respx tests + co-bump + triad + UAT runbook.
