# Phase 32: Categories migration (hard cut) - Context

**Gathered:** 2026-06-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Faire de `intent.yml` la **seule source hand-edited** pour `arrconf.yml`. Aujourd'hui `arrconf.yml` (323 lignes) est hand-edited et contient (a) le bloc `categories[]` (10 entrées, ~52 lignes) et (b) ~270 lignes de config app statique. Les générateurs purs (`generate_qbit_categories`, `generate_sonarr_resources`, `generate_radarr_resources`, `generate_jellyfin_libraries`, `generate_anime_tag_labels`) expandent les categories en ressources **au runtime d'`apply`/`diff`** — rien n'est écrit dans `arrconf.yml`.

Cette phase : déplacer `categories[]` dans `intent.yml`, y absorber aussi la config app statique, et faire émettre `arrconf.yml` **intégralement** par `arrconf generate` (compose categories-derived + apps pass-through). `arrconf.yml` devient 100% généré + read-only, byte-reproductible, couvert par la garde CI `generate-idempotence`. Hard cut : pas de double-source.

**Requirements:** CATMIG-01 (intent absorbe categories), CATMIG-02 (generate émet arrconf.yml complet), CATMIG-03 (arrconf.yml généré read-only + CI guard).

**Hors scope (autres phases):** génération de `configarr.yml` (Phase 33), UI sur intent (Phase 34), migration filesystem média (tâche ops manuelle, voir Deferred).
</domain>

<decisions>
## Implementation Decisions

### Où vit la config statique (crux)
- **D-32-01:** `intent.yml` **absorbe tout**. Il gagne un bloc `categories:` (lift verbatim depuis arrconf.yml) **et** un bloc `apps:` (ou équivalent) pass-through verbatim pour la config app statique (base_urls, prune flags, series_tags/movie_tags, content_routing, prowlarr/qbittorrent/seerr/jellyfin settings). `arrconf generate` **compose** les ressources categories-derived (via les générateurs purs existants) avec le pass-through `apps:` pour produire `arrconf.yml` complet. Un seul fichier hand-edited = vraie couche d'intention. Pas de fichier `arrconf-base.yml` séparé ; pas de modélisation pydantic typée de la config app (YAGNI — config stable, pass-through suffit).

### content_routing / series_tags / movie_tags
- **D-32-02:** **Restés statiques, pass-through verbatim** dans le bloc `apps:`. Les listes de keywords (family/anime, Pitfall 5) sont du jugement opérateur non-dérivable des categories — ne PAS tenter de les dériver des profils/kinds. KISS.

### Format de sortie arrconf.yml généré
- **D-32-03:** **YAML déterministe machine-order** (sérialisation triée stable via le dumper YAML du projet — ruyaml/pydantic model_dump). Header `# GENERATED — do not edit by hand` (+ pointer vers intent.yml). **Byte-for-byte reproductible** par `arrconf generate` (SC#4). Pas de préservation des commentaires/ordre humains actuels d'arrconf.yml — la doc vit désormais dans `intent.yml` ; arrconf.yml étant read-only, les commentaires y ont peu de valeur. NB : le modeline `# yaml-language-server: $schema=...` actuel d'arrconf.yml peut disparaître (fichier non hand-edited) — à confirmer en planning.

### Hard cut (pas de transition)
- **D-32-04:** Aucun chemin double-source, aucun warning deprecation. Opérateur unique → pas de compat fork. Après cette phase, un `arrconf.yml` hand-edité ne peut PAS coexister avec la version générée (SC#2). La garde CI échoue si `intent.yml` change sans régénérer `arrconf.yml`.

### Couplage generate ↔ arrconf.yml à inverser
- **D-32-05:** Le code actuel de `generate()` (`__main__.py:~1050`) charge `arrconf.yml` pour récupérer les categories (qbit_manage `cat:` mirror via `load_config(output_dir/"arrconf.yml")` → `generate_qbit_categories`). Après CATMIG, les categories viennent d'`intent.yml` → ce couplage doit s'inverser : `generate_qbit_categories` (et la génération qbit_manage) lisent les categories depuis l'intent, plus depuis arrconf.yml. Détail d'implémentation, mais dépendance réelle à traiter.

### Claude's Discretion
- Forme exacte du schéma `apps:` dans `intent.yml` (nom du bloc, nesting) — laisser au planner/researcher tant que c'est un pass-through fidèle qui reproduit les sections app actuelles d'arrconf.yml.
- Mécanisme de compose (les générateurs retournent des objets Python mergés au runtime d'apply ; il faut soit déplacer ce merge au generate-time, soit le réutiliser) — implémentation.
- Migration de la garde CI `generate-idempotence` pour couvrir `arrconf.yml` (path filter, `generate --check`).

### Reviewed Todos (not folded)
- `2026-05-27-migrer-mediatheque-existante-vers-buckets-categories-v0-3-0` (area: ops, score 0.6) — **non-foldé**. Tâche ops manuelle (déplacer fichiers média sur disque vers buckets Categories), sans rapport avec ce refactor code (categories[] → intent.yml). Reste en pending. Runbook dans CLAUDE.md.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Intent layer + generate foundation (Phase 28 / v0.10.0)
- `.planning/v0.10.0-intention-layer-DESIGN.md` — design d'origine de la couche d'intention (§2 architecture cible, §3 hors-tranche-1, modèle G1 local+committé).
- `tools/arrconf/arrconf/__main__.py` (fn `generate`, ~ligne 1001) — commande CLI `arrconf generate` existante (génère cross-seed + qbit_manage ; `--check` mode CI). À étendre pour émettre arrconf.yml.
- `tools/arrconf/arrconf/generators/categories.py` — générateurs purs categories → ressources (qbit/sonarr/radarr/jellyfin/anime-tags). Réutilisés au generate-time.
- `tools/arrconf/arrconf/generators/intent.py` — pattern générateur intent (cross-seed/qbit_manage, header `# GENERATED`, déterminisme `json.dumps(sort_keys=True)`).
- `tools/arrconf/arrconf/intent_config.py` — schéma pydantic `IntentConfig` (tools, sagas). À étendre avec `categories` + `apps` pass-through.

### Fichiers cibles
- `charts/arr-stack/files/intent.yml` — source hand-edited (actuellement tools + sagas ; gagne categories + apps).
- `charts/arr-stack/files/arrconf.yml` — 323 lignes, devient généré read-only.
- `schemas/intent-schema.json` + `schemas/arrconf-schema.json` — à régénérer (`arrconf schema-gen`).

### CI guard
- `.github/workflows/tests.yml` — job `generate-idempotence` (D-09, isolé de chart-lint). À étendre pour couvrir arrconf.yml.

### Conventions projet (CRITIQUE)
- `CLAUDE.md` §"Release pin co-bump pattern" — cette phase touche `tools/arrconf/**` → **co-bump `charts/arr-stack/values.yaml#arrconf.image.tag` OBLIGATOIRE** dans le même commit que le code Python.
- `CLAUDE.md` §"Idempotence (RÈGLE D'OR)" + ADR-6 snapshot discipline.
- ADR-10 (PROJECT.md `<decisions>`) — couche d'intention, modèle G1 (local + committé, CI idempotence guard). Étendu par cette phase.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Générateurs purs `generators/categories.py`** : `generate_qbit_categories`, `generate_sonarr_resources`, `generate_radarr_resources`, `generate_jellyfin_libraries`, `generate_anime_tag_labels`. Émettent déjà les ressources categories-derived — réutilisables au generate-time pour composer arrconf.yml.
- **Pattern `generate_cross_seed` / `generate_qbit_manage`** (`generators/intent.py`) : header `# GENERATED`, fonction pure, déterminisme par tri. Modèle à suivre pour le générateur arrconf.yml.
- **`arrconf generate` CLI** (`__main__.py`) : structure `--intent` / `--output-dir` / `--check` déjà en place. Ajouter l'émission arrconf.yml dans la même boucle.

### Established Patterns
- **G1 (ADR-10)** : generate en local, sortie committée read-only, CI vérifie l'idempotence (`generate --check` + `git diff --exit-code`).
- **Co-bump pin** : tout code `tools/arrconf/**` co-bump `values.yaml#arrconf.image.tag`.
- **Déterminisme** : sérialisation triée (`json.dumps(sort_keys=True)` pour intent.py ; équivalent YAML pour arrconf.yml).

### Integration Points
- `apply` / `diff` lisent `arrconf.yml` (`load_config`) — **inchangé** après CATMIG (ils lisent le fichier généré). Le merge categories-derived bascule du runtime d'apply vers le generate-time.
- Couplage à inverser : génération qbit_manage lit les categories depuis arrconf.yml → désormais depuis intent (D-32-05).
- ADR-6 : re-snapshot avant tout test live (mais cette phase est code/generate-only, pas d'écriture API nouvelle).
</code_context>

<specifics>
## Specific Ideas

- Lift `categories[]` **verbatim** depuis arrconf.yml vers intent.yml (mêmes champs `name`/`kind`/`profile`/`display`/`base_path`, 10 entrées prod).
- Le bloc `apps:` reproduit fidèlement les sections app actuelles d'arrconf.yml (sonarr/radarr/prowlarr/qbittorrent/seerr/jellyfin), y compris les stubs `prune: false` et les blocs `content_routing`/`series_tags`/`movie_tags`.
- Sortie arrconf.yml : header `# GENERATED — do not edit by hand`, pointer vers `intent.yml`.
</specifics>

<deferred>
## Deferred Ideas

- **Génération de `configarr.yml`** (CF/QP par catégorie) — Phase 33 (CFGARR-*).
- **UI sur intent.yml** — Phase 34 (UI-*).
- **Modélisation pydantic typée de la config app** (au lieu du pass-through) — non retenu (D-32-01) ; reconsidérer seulement si validation forte devient un besoin réel.

### Reviewed Todos (not folded)
- `2026-05-27-migrer-mediatheque-existante-vers-buckets-categories-v0-3-0` (ops) — tâche filesystem manuelle, hors scope code. Reste en pending.

</deferred>

---

*Phase: 32-categories-migration-hard-cut*
*Context gathered: 2026-06-03*
