---
phase: 20-categories-cleanup-audit
verified: 2026-05-26T08:15:00Z
status: human_needed
score: 8/9 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Opérateur exécute `arrconf audit` contre le cluster live, remplit les cellules `?` dans 20-AUDIT.md, puis exécute `arrconf audit-verify` (exit 0)"
    expected: "20-AUDIT.md remplacé par l'inventaire réel du cluster (films/séries sur legacy paths listés, mappings résolus sans `?` ni `TBD`), puis `audit-verify` exit 0 confirmant les 4 gates (zéro `?`, YAML valide, paths ∈ categories[], tags live valides)"
    why_human: "Nécessite les env vars (SONARR_API_KEY, RADARR_API_KEY, QBT_USER, QBT_PASS, SEERR_API_KEY, JELLYFIN_API_KEY) + kubectl port-forwards actifs sur le workstation opérateur. Chaque cellule `?` du fichier généré est une décision par-item (quelle série appartient à Émilie vs Thomas vs Zoé, quels films Ghibli vs Disney) — connaissance opérateur exclusive à Claude ne peut pas simuler."
---

# Phase 20 : Categories Cleanup Audit — Rapport de vérification

**Phase Goal :** Produire un inventaire exhaustif read-only de l'état legacy v0.2.0 (Radarr / Sonarr / qBittorrent / Seerr / Jellyfin) avec tables de mapping `legacy_path → Category` et `legacy_tag → Category_tag` prêtes pour les phases destructives 21-23. L'audit se matérialise par deux nouveaux sous-commandes Typer (`arrconf audit` et `arrconf audit-verify`) adossées à un nouveau module `arrconf/audit.py` ; la gate verify refuse les cellules non-résolues.
**Vérifié :** 2026-05-26T08:15:00Z
**Statut :** human_needed
**Re-vérification :** Non — vérification initiale

---

## Vérité observables

| # | Vérité | Statut | Evidence |
|---|--------|--------|----------|
| 1 | L'opérateur peut exécuter `uv run arrconf audit` et produire un `20-AUDIT.md` complet | ✓ VERIFIED | CLI enregistrée (`arrconf --help` montre `audit` et `audit-verify`). `run_audit()` émet Markdown + appendix YAML. Module `audit.py` (997 LOC) existe, importe sans erreur. Le scaffold `20-AUDIT.md` existe et documente la procédure de génération contre le cluster. |
| 2 | L'audit capture chaque torrent qBit hors Category save_paths | ✓ VERIFIED | `audit_qbittorrent()` itère sur `/torrents/info`, compare `save_path` vs `{"/data/<cat.name>"}`, émet `torrents_to_relocate`. Test `test_audit_qbittorrent_legacy_save_path_detected` PASS. |
| 3 | L'audit énumère les tags legacy vs Category avec action prune/rename proposée | ✓ VERIFIED | `audit_radarr()` et `audit_sonarr()` produisent chacun un bloc `tags` avec `proposed_action: "prune"` pour `is_legacy_tag(label)`. Tests Pitfall 2 (SERIES vs MOVIES mappings séparés) PASS. |
| 4 | Les auto-mappings correspondent verbatim à la table CLAUDE.md §"Filesystem migration" | ✓ VERIFIED | `AUTO_PATH_MAPPING = {"/media/anime": "/media/series-zoe", "/media/family": "/media/series-garcons", "/media/films-family": "/media/films-enfants"}`. Test `test_auto_path_mapping_matches_claude_md_filesystem_table` PASS. Assertion Python confirmée en runtime. |
| 5 | Les items ambigus sont pré-remplis avec des cellules `?` que l'opérateur édite | ✓ VERIFIED | `_render_markdown()` émet `?` lorsque `auto_target_rootFolder is None` et `current_rootFolder in OPERATOR_DECISION_PATHS`. `OPERATOR_DECISION_PATHS = {"/media/films-anime", "/media/series", "/media/films"}`. Test `test_audit_radarr_films_anime_left_for_operator` confirme que Spirited Away (films-anime) n'a pas de `auto_target_rootFolder`. |
| 6 | `arrconf audit-verify` est une gate exit (zéro `?`/`TBD`, YAML valide, paths ∈ categories[], tags live) | ✓ VERIFIED | `verify_audit()` implémente les 4 gates séquentielles : Gate 1 regex `\|\s*\?\s*\|` + `TBD`, Gate 2 extraction YAML fenced block + `YAML(typ="safe").load()`, Gate 3 `to.rootFolderPath ∈ {c.base_path}`, Gate 4 tags live re-GET conditionnel. 7 tests verify gate couverts (question cell, TBD cell, missing YAML, invalid path, valid pass...). |
| 7 | `arrconf/audit.py` ne contient que des `client.get(...)` — zéro mutation | ✓ VERIFIED | `grep -nP "\.(post\|put\|delete\|patch\|post_form)\(" audit.py` → exit 1 (zéro match). Les seuls appels réseau sont `.get("/movie")`, `.get("/tag")`, `.get("/downloadclient")`, `.get("/series")`, `.get("/torrents/info")`, `.get("/torrents/categories")`, `.get("/settings/sonarr")`, `.get("/Library/VirtualFolders")`. |
| 8 | Le même commit co-bumpe `arrconf.image.tag` 0.14.0 → 0.14.1 avec l'annotation Renovate préservée | ✓ VERIFIED | `charts/arr-stack/values.yaml` ligne 451 : `tag: "0.14.1"`. Annotation `# renovate: image=ghcr.io/tom333/arr-stack-arrconf` présente ligne 449. Commit `ee5ac19` documente le co-bump dans la même transaction. |
| 9 | Triade Python (`ruff format --check`, `ruff check`, `mypy`) passe et `pytest --cov-fail-under=70` reste vert | ✓ VERIFIED | `ruff format --check` : 95 fichiers OK. `ruff check` : All checks passed. `mypy arrconf` : Success — 0 issues in 56 source files. `pytest --cov-fail-under=70` : 442 tests PASS, couverture 83.47% (gate 70% franchie). 26 tests `test_audit.py` spécifiquement PASS en 0.93s. |

**Score :** 8/9 vérités vérifiées par automatisation. La 9e (T1 complète) est conditionnée à l'exécution humaine Task 6.

> **Note :** La vérité T1 est partiellement vérifiée — l'infrastructure CLI existe et fonctionne. Le scaffold `20-AUDIT.md` (58 lignes) est intentionnel : il contient les instructions pour générer le fichier réel. La population du fichier par `arrconf audit` contre le cluster live + résolution des cellules `?` + `audit-verify` exit 0 est la partie humaine requise (Task 6, identifiée comme checkpoint bloquant dans le PLAN).

---

## Artefacts requis

| Artefact | Attendu | Statut | Détails |
|----------|---------|--------|---------|
| `tools/arrconf/arrconf/audit.py` | Module read-only audit — 5 fonctions par-app + run_audit + verify_audit | ✓ VERIFIED | 997 LOC. Tous les symboles publics présents. 0 appel de mutation. ruyaml YAML(typ="safe"). `_assert_no_secrets()` garde défensive. |
| `tools/arrconf/arrconf/__main__.py` | Wiring Typer `audit` + `audit-verify` avec pre-flight env-var gates | ✓ VERIFIED | Import `from arrconf.audit import run_audit, verify_audit` à la ligne 18. Commandes `audit` (callback function) et `audit-verify` (name="audit-verify") visibles dans `--help`. |
| `tools/arrconf/tests/test_audit.py` | ≥ 15 tests respx-mockés couvrant tous les Pitfalls | ✓ VERIFIED | 937 LOC, 26 tests. Tous les 8 Pitfalls de RESEARCH.md couverts. Tous les 26 PASS. |
| `tools/arrconf/tests/fixtures/audit/` | 10 fichiers JSON de fixtures | ✓ VERIFIED | 10 fichiers présents : radarr_movies_mixed.json, radarr_tags_mixed.json, radarr_downloadclient_with_catchall.json, sonarr_series_mixed.json, sonarr_tags_mixed.json, sonarr_downloadclient_with_catchall.json, qbit_torrents_mixed.json, qbit_categories_aligned.json, seerr_settings_sonarr_legacy_anime.json, jellyfin_virtualfolders_post_phase16.json. |
| `charts/arr-stack/values.yaml` | Co-bump 0.14.0 → 0.14.1 avec annotation Renovate | ✓ VERIFIED | tag: "0.14.1" présent. Annotation `# renovate: image=...` préservée. |
| `.planning/phases/20-categories-cleanup-audit/20-AUDIT.md` | Scaffold Markdown + instructions pour génération live | ✓ VERIFIED (scaffold) | Fichier existe (58 lignes). Scaffold intentionnel documenté dans SUMMARY §"Known Stubs". Le fichier réel est généré par `arrconf audit` (action opérateur, Task 6). |

---

## Vérification des liaisons clés (Key Links)

| De | Vers | Via | Statut | Détail |
|----|------|-----|--------|--------|
| `audit.py` | `client_base.py` | `from arrconf.client_base import (JellyfinClient, QbittorrentClient, RadarrClient, SeerrClient, SonarrClient)` | ✓ WIRED | Import ligne 20-27. Clients utilisés dans `run_audit()`. |
| `__main__.py` | `audit.py` | `from arrconf.audit import run_audit, verify_audit` | ✓ WIRED | Import ligne 18. Les deux fonctions appelées dans `audit()` et `audit_verify_cmd()`. |
| `20-AUDIT.md` | `arrconf.yml` (categories[]) | `verify_audit` cross-check `to.rootFolderPath ∈ categories[*].base_path` | ✓ WIRED (logique) | Gate 3 implémentée dans `verify_audit()` lignes 946-966. Testé par `test_verify_audit_rejects_target_rootfolder_not_in_categories`. |
| `values.yaml` | `ghcr.io/tom333/arr-stack-arrconf:0.14.1` | patch bump co-ship avec tools/arrconf/** | ✓ WIRED | tag "0.14.1" en ligne 451. Commit `ee5ac19` contient les deux. |

---

## Trace de flux de données (Level 4)

Non applicable pour cette phase. `audit.py` est un module de lecture seule — il lit des données depuis des APIs REST (mocked en test par respx) et écrit un artefact fichier (`20-AUDIT.md`). Il n'y a pas de composant React/Vue ou de rendu dynamique à tracer. Le flux de données est direct : `client.get()` → dict Python → `_render_markdown()` → fichier.

---

## Spot-checks comportementaux

| Comportement | Commande | Résultat | Statut |
|-------------|----------|----------|--------|
| Module audit importable | `python -c "import arrconf.audit"` | Exit 0 | ✓ PASS |
| CLI audit visible dans --help | `uv run arrconf --help \| grep audit` | Lignes `audit` et `audit-verify` présentes | ✓ PASS |
| 26 tests audit passent | `pytest tests/test_audit.py -q` | 26 passed in 0.93s | ✓ PASS |
| Suite complète stable | `pytest --cov-fail-under=70 -q` | 442 passed, 83.47% coverage | ✓ PASS |
| Triade Python clean | `ruff format --check && ruff check && mypy arrconf` | Tous exits 0 | ✓ PASS |
| Read-only invariant | `grep -nP "\.(post\|put\|delete\|patch\|post_form)\(" audit.py` | Exit 1 — zéro match | ✓ PASS |
| Co-bump tag | `grep 'tag:' values.yaml \| grep 0.14.1` | `tag: "0.14.1"` trouvé | ✓ PASS |

---

## Couverture des requirements

| Requirement | Plan source | Description | Statut | Evidence |
|-------------|------------|-------------|--------|----------|
| CAT-CLEANUP-01 | 20-01-PLAN.md | Inventaire exhaustif items legacy v0.2.0 — Radarr/Sonarr root_folders, qBit save_paths, tags legacy, tables de mapping | ✓ SATISFAIT (partiellement — scaffold uniquement jusqu'à Task 6) | Module audit.py implémente les 7 GETs couvrant les (a)-(g) du requirement. Le livrable `20-AUDIT.md` est un scaffold en attente de l'exécution opérateur contre le cluster. L'infrastructure technique est complète et vérifiée par 26 tests. |

---

## Anti-patterns détectés

| Fichier | Ligne | Pattern | Sévérité | Impact |
|---------|-------|---------|----------|--------|
| `.planning/phases/20-categories-cleanup-audit/20-AUDIT.md` | 1-58 | Scaffold / placeholder — `> **STATUS: AWAITING OPERATOR**` | ℹ️ Info (intentionnel) | Design volontaire documenté dans SUMMARY §"Known Stubs". Le scaffold sera remplacé par l'inventaire réel lors de Task 6. N'est PAS un anti-pattern de code — c'est le checkpoint opérateur documenté dans le PLAN. |

Aucun anti-pattern bloquant détecté dans le code Python (`audit.py`, `__main__.py`, `test_audit.py`).

---

## Vérification humaine requise

### 1. Exécution de l'audit contre le cluster live (Task 6 — PLAN checkpoint)

**Test :** Depuis le workstation opérateur, avec les env vars cluster (`SONARR_API_KEY`, `RADARR_API_KEY`, `QBT_USER`, `QBT_PASS`, `SEERR_API_KEY`, `JELLYFIN_API_KEY`) et kubectl port-forwards ouverts :

```bash
cd tools/arrconf
uv run arrconf audit \
  --config ../../charts/arr-stack/files/arrconf.yml \
  --output ../../.planning/phases/20-categories-cleanup-audit/20-AUDIT.md
```

Puis ouvrir `20-AUDIT.md` dans VS Code, remplir chaque cellule `?` (décisions par-item sur `/media/films-anime`, `/media/series`, `/media/films`), puis :

```bash
uv run arrconf audit-verify \
  --input ../../.planning/phases/20-categories-cleanup-audit/20-AUDIT.md \
  --config ../../charts/arr-stack/files/arrconf.yml
# Doit exit 0
```

Committer le fichier `20-AUDIT.md` rempli.

**Attendu :** `20-AUDIT.md` remplacé par l'inventaire réel (films/séries sur les paths legacy listés, torrents qBit hors save_paths Category listés, tables de mapping complètes). `audit-verify` exit 0 confirmant les 4 gates. Zéro cellule `?` ou `TBD` restante dans le fichier final.

**Pourquoi humain :** (a) Requiert les secrets d'API du cluster (non commités, injectés via env). (b) Requiert des kubectl port-forwards actifs. (c) Chaque cellule `?` est une décision par-item qui dépend de la connaissance du contenu réel (quelle série appartient à Émilie/Thomas/Zoé/Garçons, quels films Ghibli vs Disney/Pixar, quels films "récents" vont dans `nouveaux-films`). Claude ne peut pas simuler ces décisions sans accès au cluster et à la connaissance métier de l'opérateur.

---

## Résumé des gaps

Aucun gap bloquant identifié. L'infrastructure technique (module `audit.py`, wiring Typer, tests, fixtures, co-bump) est complète et vérifiée.

Le seul item non-automatisable est le checkpoint humain Task 6 : l'exécution de `arrconf audit` contre le cluster live + résolution des cellules `?` + `audit-verify` exit 0 + commit du fichier peuplé. Ce checkpoint était identifié comme `type="checkpoint:human-action" gate="blocking"` dans le PLAN original — il n'est donc pas un gap technique mais la partie opérateur de la phase.

**Critère de passage vers Phase 21 :** `20-AUDIT.md` commité avec zéro `?`/`TBD`, `audit-verify` exit 0 documenté.

---

### Déviation notable : `_fetch_current_categories` non utilisée

Le PLAN spécifiait de réutiliser `_fetch_current_categories` depuis `arrconf.reconcilers.qbittorrent`. En pratique, `audit.py` appelle directement `client.get("/torrents/categories")` et traite lui-même le dict retourné. La SUMMARY indique que l'import a été supprimé par ruff (import inutilisé). L'implémentation est fonctionnellement équivalente et couverte par les tests — déviation mineure, sans impact sur la conformité.

---

_Vérifié : 2026-05-26T08:15:00Z_
_Vérificateur : Claude (gsd-verifier)_
