# Phase 2: Validation cluster - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-08
**Phase:** 02-arrconf-cluster-validation
**Areas discussed:** Mini-chart location + arrconf.yml shape, Schedule + concurrence (Q3), Protocole bascule dry-run → apply, Scope bootstrap secret

---

## Mini-chart location

| Option | Description | Selected |
|--------|-------------|----------|
| `my-kluster/charts/arrconf/` (mirror configarr) | Calque exact configarr. Phase 4 supprime le chart de my-kluster + l'ArgoCD App quand l'umbrella prend le relais (même migration que configarr). PRs Phase 2-3 atterrissent côté my-kluster. | ✓ |
| `arr-stack/charts/arrconf-only/` | Le chart vit dans arr-stack ; Phase 4 le transforme en umbrella. ArgoCD App (dans my-kluster) pointe arr-stack repo. Crée un décalage avec configarr/cleanuparr toujours en my-kluster jusqu'à Phase 4. | |
| Hybride (chart arr-stack, values+secret my-kluster) | Chart squelette dans arr-stack, values prod + ArgoCD App + secret côté my-kluster. Plus complexe mais découple chart vs config-prod. | |

**User's choice:** my-kluster/charts/arrconf/ (mirror configarr)
**Notes:** Décision motivée par la cohérence avec le pattern configarr déjà en place. Phase 4 fera la même migration pour les deux charts (configarr + arrconf) vers l'umbrella, ce qui simplifie le diff de migration.

---

## arrconf.yml shape Phase 2

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal Sonarr-only | Un seul bloc `sonarr.main` avec 1 download_client. Pas de stubs, pas de noise. Le schéma JSON valide déjà cette shape. Phase 3 ajoute les sections au fur et à mesure. | ✓ |
| Scaffold 6 apps avec stubs vides | `radarr: {}`, `prowlarr: {}`, etc. Demande modif schéma pour autoriser sections vides. Avantage : zero-PR-churn aux phases suivantes. | |
| Sonarr complet avec stubs commentaires Phase 3 | Sections futures `indexers: []`, `notifications: []`, etc. présentes mais commentées. Toujours obligation de modif schéma. | |

**User's choice:** Minimal Sonarr-only
**Notes:** « Pas de noise sans valeur immédiate ». Cohérent avec D-25 et avec le principe Phase 1 « stubs raise ScopeViolationError BEFORE network » : pas de YAML qui anticipe ce qui n'est pas encore implémenté.

---

## Schedule + concurrence (Q3)

| Option | Description | Selected |
|--------|-------------|----------|
| 4 h — sync configarr | `0 */4 * * *`. Calque exact configarr. Une seule cadence à retenir. Drift fenêtre max 4h. | ✓ |
| 6 h — recommandation spec | `0 */6 * * *`. Recommandation initiale spec.md §10 Q3. Désynchronise avec configarr. | |
| 1 h — réaction rapide | `0 * * * *`. Drift cap 1h, mais 24 runs/jour = overkill homelab single-user. | |

**User's choice:** 4h sync avec configarr
**Notes:** `concurrencyPolicy: Forbid`, `startingDeadlineSeconds: 600`, `successfulJobsHistoryLimit: 1`, `failedJobsHistoryLimit: 2` (mirror configarr).

---

## Bascule dry-run → apply

| Option | Description | Selected |
|--------|-------------|----------|
| 2 PRs successives sur Helm value `arrconfDryRun` | PR1 ajoute le chart en `true` → ArgoCD sync → 1 cycle d'observation → re-snapshot post-run = identique au baseline → PR2 flippe en `false`. Trace Git complète, revert atomique. | ✓ |
| 1 PR + `kubectl patch` temporaire | PR unique en `true`, bascule via patch one-shot, PR2 réaligne Git. Drift temporaire cluster vs Git pendant validation, contredit le principe GitOps. | |
| Default `false` dès PR1 + dry-run hors-cluster avant | `kubectl create job --from=cronjob/arrconf` avant la PR pour valider, puis PR1 directement en apply. Validation hors-Git, plus difficile à tracer. | |

**User's choice:** 2 PRs successives, Helm value `arrconfDryRun`
**Notes:** Respect strict du GitOps (zéro drift cluster vs Git). Le commit message PR2 documentera l'observation des logs PR1 + la date du re-snapshot post-PR1.

---

## Scope du bootstrap secret arrconf-env

| Option | Description | Selected |
|--------|-------------|----------|
| Juste SONARR_API_KEY (Phase 2 strict) | Une seule clé. Bump à chaque phase suivante (3 → +RADARR/PROWLARR, 5 → +QBT, 6 → +SEERR, 7 → +JELLYFIN). Principe moindre privilège. | ✓ |
| 7 clés upfront, valeurs vides pour futures | Un seul template à vie. arrconf valide en startup que la clé attendue est non-vide. Pod a 7 envvars. | |
| 7 clés upfront avec vraies valeurs | 1 PR à vie. Oblige à créer comptes admin Jellyfin / accès Seerr maintenant alors que Phase 7/6 sont loin. | |

**User's choice:** SONARR_API_KEY seul
**Notes:** Principe de moindre privilège ; cohérent CLAUDE.md « Aucune lecture de fichier de secrets — uniquement env » + REQ-bootstrap-exception.

---

## Claude's Discretion

Décisions opérationnelles laissées au planner / executor (mirror configarr sauf raison contraire) :

- Cluster service URL Sonarr : confirmer le service name dans `my-kluster/argocd/argocd-apps/sonarr-app.yaml`
- Pod securityContext (runAsNonRoot, runAsUser 1000)
- Resources requests/limits (mirror configarr 50m/128Mi req, 500m/512Mi limit)
- TZ env var Europe/Paris
- imagePullPolicy IfNotPresent
- ConfigMap checksum/config annotation
- Helm values.schema.json (optionnel Phase 2, déféré Phase 4)
- Outil de diff structuré entre snapshots (peut rester `diff -r` brut)
- Format exact du runbook drift detection (README arrconf vs README my-kluster/charts/arrconf/)

## Deferred Ideas

- `tools/snapshot/diff.sh` — script de diff structuré filtrant les champs read-only. Utile mais pas critique Phase 2.
- NetworkPolicy `selfhost` restrictive pour arrconf — défense en profondeur, **Phase 8 (durcissement)**.
- Notification Sonarr quand arrconf rétablit un drift — suppose Phase 3 `notifications` reconciler livré.
- `values.schema.json` du mini-chart — déféré Phase 4 (umbrella en aura besoin).
- Endpoint Prometheus arrconf metrics — hors-scope MVP, Phase post-MVP.
