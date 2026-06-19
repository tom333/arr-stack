# arr-stack OSS Public Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a clean, de-personalized, Apache-2.0 monorepo suitable for a brand-new public OSS repo (1 squashed commit, no history), without touching the live private deployment.

**Architecture:** Work in a throwaway **export copy** (`/data/projets/perso/arr-stack-export`), NOT the live repo — the kid-name categories are LIVE (real `/media/series-*` dirs, Sonarr root folders, qBit categories); renaming them in the deployed configs would break the running stack. The live repo (`tom333/arr-stack`) stays as the private deploy source (made private after secret rotation). The export copy is de-personalized, gets governance files, is squashed to one commit, and pushed to a NEW public repo (final step gated on user confirmation).

**Tech Stack:** bash/git/sed, Helm, pytest (verify de-personalized tree still green).

**Decisions (locked):** new squashed repo · Apache-2.0 · monorepo · exclude `.planning/` + `docs/superpowers/` + `snapshots/` + dev artifacts.

---

## Preconditions (operator, NOT in this plan)

- [ ] **Rotate the leaked secrets FIRST** (public ~6 weeks): Seerr API key, Sonarr UI password, Radarr UI password (+ prudence: Sonarr/Radarr/Prowlarr API keys, qBit creds); update the `arrconf-env` sealed-secret. The export below excludes `snapshots/` so the new repo won't carry them, but the OLD public repo history still does until rotated + privatized.
- [ ] After rotation: make `tom333/arr-stack` **private** (it keeps the PII+secret history and remains the deploy source for my-kluster).

## File Structure (export copy)

Operate entirely under `/data/projets/perso/arr-stack-export`. Nothing here touches the live repo or cluster.

**EXCLUDE from the export** (personal / dev / forensic / secret):
`.git`, `.planning/`, `docs/superpowers/`, `snapshots/`, `graphify-out/`, `.code-review-graph/`, `.claude/`, `.opencode.json`, `.mcp.json`, `.migration-state.json`, `.env`, `.pytest_cache/`, `.ruff_cache/`, `**/__pycache__/`, `**/.venv/`, `**/node_modules/`, `**/dist/`, `charts/arr-stack/charts/` (vendored app-template — regenerated at deploy).

**KEEP:** `charts/arr-stack/` (templates, values.yaml, files/, Chart.yaml/lock, values.schema.json), `tools/{arrconf,arrconf-mcp,arr-dashboard,arrconf-ui,scripts,snapshot}/`, `examples/`, `schemas/`, `README.md`, `spec.md`, `CLAUDE.md`, `.github/workflows/`, `.gitignore`, `.pre-commit-config.yaml`, `.env.example`, `pyproject`/configs.

**RENAME MAP** (PII → generic illustrative; applied across the whole export):
| real | generic |
|---|---|
| `series-emilie` | `series-general` |
| `series-thomas` | `series-scifi` |
| `series-garcons` | `series-kids` |
| `series-zoe` | `series-anime` |
| `films-zoe` | `films-anime` |
| `tgu.ovh` | `example.com` |
| `A05s de Emilie` (snapshots only — excluded) | n/a |

`tom333` (GitHub handle / GHCR org) is KEPT — it's a public handle, normal for an OSS repo owned by it. `Thomas Guyader` full-name lines in shipped docs are reduced to `tom333`. The French generic words `enfants`/`nouveaux-films`/`films`/`series` are NOT PII — kept.

---

## Task 1: Build the clean export copy

**Files:** new dir `/data/projets/perso/arr-stack-export`

- [ ] **Step 1: rsync the tree with excludes**

```bash
SRC=/data/projets/perso/arr-stack
DST=/data/projets/perso/arr-stack-export
rm -rf "$DST" && mkdir -p "$DST"
rsync -a \
  --exclude='.git' --exclude='.planning' --exclude='docs/superpowers' \
  --exclude='snapshots' --exclude='graphify-out' --exclude='.code-review-graph' \
  --exclude='.claude' --exclude='.opencode.json' --exclude='.mcp.json' \
  --exclude='.migration-state.json' --exclude='.env' \
  --exclude='.pytest_cache' --exclude='.ruff_cache' \
  --exclude='__pycache__' --exclude='.venv' --exclude='node_modules' \
  --exclude='dist' --exclude='charts/arr-stack/charts' \
  "$SRC/" "$DST/"
```

- [ ] **Step 2: verify NO excluded-class content leaked into the copy**

```bash
cd /data/projets/perso/arr-stack-export
test ! -e .env && test ! -d .planning && test ! -d snapshots && test ! -d docs/superpowers && echo "excludes OK" || { echo "LEAK: an excluded path is present"; exit 1; }
# docs/ should now be empty or absent → remove if empty
[ -d docs ] && find docs -type f | head && rmdir -p docs 2>/dev/null || true
```
Expected: `excludes OK`.

- [ ] **Step 3: scan the copy for any leftover SECRET (must be zero)**

```bash
cd /data/projets/perso/arr-stack-export
grep -rnoE '"(apiKey|password|token)"\s*:\s*"[A-Za-z0-9+/=._-]{12,}"' . --include='*.json' --include='*.yml' --include='*.yaml' 2>/dev/null | grep -viE 'REDACT|<|example|placeholder|\$\{' | head
```
Expected: NO output (snapshots excluded; fixtures are REDACTED/synthetic). If anything prints, stop and sanitize that file before continuing.

- [ ] **Step 4: commit nothing yet (no git here until Task 5).** Report the file count + that excludes/secret checks passed.

---

## Task 2: De-personalize the export (rename map) + verify green

**Files:** all of `/data/projets/perso/arr-stack-export`

- [ ] **Step 1: apply the rename map repo-wide**

```bash
cd /data/projets/perso/arr-stack-export
# order matters: rename the longer/specific tokens; films-zoe before series-zoe is irrelevant (distinct), but do tgu.ovh last
FILES=$(grep -rlE 'series-emilie|series-thomas|series-garcons|series-zoe|films-zoe|tgu\.ovh' . \
  --exclude-dir=.venv --exclude-dir=node_modules --exclude-dir=__pycache__ 2>/dev/null)
for f in $FILES; do
  sed -i \
    -e 's/series-emilie/series-general/g' \
    -e 's/series-thomas/series-scifi/g' \
    -e 's/series-garcons/series-kids/g' \
    -e 's/series-zoe/series-anime/g' \
    -e 's/films-zoe/films-anime/g' \
    -e 's/tgu\.ovh/example.com/g' \
    "$f"
done
```

- [ ] **Step 2: verify zero PII tokens remain in the copy**

```bash
cd /data/projets/perso/arr-stack-export
grep -rniE 'emilie|thomas|\bzoe\b|garcons|guyader|tgu\.ovh' . \
  --exclude-dir=.venv --exclude-dir=node_modules --exclude-dir=__pycache__ 2>/dev/null | grep -v 'series-scifi' | head -20
```
Expected: NO output. (`series-thomas`→`series-scifi` removes the only "thomas"; the `grep -v series-scifi` guard is belt-and-suspenders.) If `guyader`/`Thomas Guyader` remains in `spec.md`/`README.md`, replace the author line with `tom333`.

- [ ] **Step 3: run ALL test suites on the copy — must stay green (rename is uniform)**

```bash
cd /data/projets/perso/arr-stack-export/tools/arrconf && uv run pytest -q
cd ../arr-dashboard && uv run pytest -q
cd ../arrconf-ui && uv run pytest -q
cd ../arrconf-mcp && uv run pytest -q
```
Expected: all green (the rename is a consistent string substitution across fixtures + assertions, so equality assertions still hold). If a test fails, the rename was non-uniform in that file — inspect + fix that file, re-run.

- [ ] **Step 4: regenerate derived artifacts so they match the renamed intent.yml**

The committed `arrconf.yml`, `configarr.yml`, `qbit_manage/config.yml`, `cross-seed/config.js`, `schemas/intent-schema.json`, `schemas/arrconf-schema.json` are generated from `intent.yml`. After the rename, regenerate so they're consistent (the sed already renamed them in-place, but regenerate to be authoritative):
```bash
cd /data/projets/perso/arr-stack-export/tools/arrconf
uv run arrconf generate --intent ../../charts/arr-stack/files/intent.yml --output-dir ../../charts/arr-stack/files/
uv run arrconf intent-schema-gen --output ../../schemas/intent-schema.json
uv run arrconf schema-gen --output ../../schemas/arrconf-schema.json
git --no-pager -C ../.. diff --stat 2>/dev/null || true   # no git yet; just confirm files exist
grep -rniE 'emilie|thomas|\bzoe\b' ../../charts/arr-stack/files/ | grep -v series-scifi | head
```
Expected: no PII in the regenerated files.

- [ ] **Step 5: genericize the qbit_manage / cross-seed tracker examples + infra-specific values**

In `charts/arr-stack/files/qbit_manage/config.yml`, replace the real tracker hostnames with placeholders + a comment:
```yaml
# Example tracker→tag rules. Replace with YOUR trackers.
trackers:
  your-tracker.example:
    tag: your-tracker
```
In `charts/arr-stack/files/cross-seed/config.js`, replace the hardcoded Prowlarr indexer IDs (`/2/api`, `/5/api`, …) with a documented placeholder:
```js
// Replace N with YOUR Prowlarr per-indexer torznab IDs (Prowlarr → Indexers → each has a /N/ feed)
torznab: ["http://prowlarr.<your-namespace>.svc.cluster.local:9696/N/api?apikey=${PROWLARR_API_KEY}"],
```
(Keep `${PROWLARR_API_KEY}` env-ref — never a literal key.)

- [ ] **Step 6: report** PII-zero confirmation + all-suites-green.

---

## Task 3: Governance + docs

**Files (create in the export):** `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `.github/ISSUE_TEMPLATE/bug_report.md`, `.github/ISSUE_TEMPLATE/feature_request.md`, `.github/pull_request_template.md`; rewrite `README.md`; extend `.gitignore`.

- [ ] **Step 1: LICENSE (Apache-2.0)**

Fetch the canonical text: `curl -fsSL https://www.apache.org/licenses/LICENSE-2.0.txt -o /data/projets/perso/arr-stack-export/LICENSE` and replace the `[yyyy] [name of copyright owner]` placeholder in the appendix with `2026 tom333`. Verify the file is ~11KB and starts with `Apache License`.

- [ ] **Step 2: SECURITY.md**

```markdown
# Security Policy

## Reporting a vulnerability
Open a private security advisory via GitHub (Security → Report a vulnerability) or email the maintainer. Do not file public issues for vulnerabilities.

## Secrets
This project reads ALL credentials from environment variables (`envFrom: secretRef` in-cluster; `.env` for local dev — gitignored). Never commit API keys, passwords, or tokens. `snapshots/` (forensic API captures) are intentionally NOT part of this repo because they can contain live credentials — sanitize before sharing any cluster capture.
```

- [ ] **Step 3: CONTRIBUTING.md**

```markdown
# Contributing

Thanks for your interest! arr-stack is a Helm umbrella chart + a Python reconciler (`arrconf`) + a dashboard.

## Dev setup
- Python: `cd tools/arrconf && uv sync` (same for arr-dashboard / arrconf-mcp / arrconf-ui).
- Triad before commit (CI gate): `uv run ruff format --check . && uv run ruff check . && uv run mypy <package>`.
- Tests: `uv run pytest`. Mock APIs with `respx` — never hit a real *arr in tests.
- Helm: `helm lint charts/arr-stack/` (vendor app-template first — see README "Local verification").

## Conventions
- Conventional Commits (`feat:`/`fix:`/…) — drives the auto-tag release.
- `arrconf` reconcilers are idempotent + diff-before-write. configarr owns quality profiles / custom formats; arrconf must never write those endpoints.
- No secrets in the repo. No `:latest` image tags.

## PRs
Open against `main`. CI (lint + tests + helm) must pass. One focused change per PR.
```

- [ ] **Step 4: CODE_OF_CONDUCT.md** — use the Contributor Covenant 2.1 short pointer:
```markdown
# Code of Conduct
This project adopts the [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). Be respectful. Report unacceptable behavior to the maintainer via a private channel.
```

- [ ] **Step 5: .github templates**

`bug_report.md`:
```markdown
---
name: Bug report
about: Something isn't working
labels: bug
---
**What happened**

**Expected**

**Stack version / image tags** (chart git tag + arrconf/arr-dashboard image tags)

**Logs** (arrconf apply / dashboard; redact secrets)

**Environment** (k8s flavor, single/multi-node, storage)
```
`feature_request.md`:
```markdown
---
name: Feature request
about: Suggest an idea
labels: enhancement
---
**Problem**

**Proposed solution**

**Scope note** (arrconf vs configarr boundary — quality profiles/custom formats are configarr's domain)
```
`pull_request_template.md`:
```markdown
## What
## Why
## Testing
- [ ] triad (ruff + mypy) green
- [ ] pytest green
- [ ] helm lint green (if chart touched)
- [ ] no secrets / no PII / no `:latest`
```

- [ ] **Step 6: rewrite README.md (English, OSS quickstart)**

Replace the existing README with a public-facing one covering: one-paragraph what/why (GitOps-managed *arr media stack: Helm umbrella + `arrconf` reconciler + lifecycle dashboard; wraps configarr for TRaSH profiles); a **"Is this for you?"** scope box (single-node-friendly, single Sonarr/Radarr instance + tags, opinionated Categories model; Bazarr/Lidarr/Readarr out of scope); **Reference architecture** (microk8s single node, hostPath torrents + NFS media, qBit NodePort 6881 + router dst-nat — all configurable in `values.yaml`); **Quickstart** (`helm dependency build` + the app-template multi-alias vendor step, `helm install -f examples/values-prod.yaml`, bootstrap secrets via env/secretRef, edit `intent.yml` → `arrconf generate`); **Components** (arrconf / arrconf-ui / arr-dashboard / arrconf-mcp one-liners); **Config** pointer to `intent.yml` (the hand-edited source of truth) + the Categories concept; **Local verification**; **License: Apache-2.0**. No personal domains/paths — use `example.com`, `<your-namespace>`, `/your/torrents/path`.

- [ ] **Step 7: extend .gitignore** — append (so future personal artifacts never re-enter):
```
.planning/
docs/superpowers/
snapshots/
graphify-out/
.code-review-graph/
.claude/
.opencode.json
.mcp.json
.migration-state.json
```

- [ ] **Step 8: trim internal docs** — `CLAUDE.md` and `spec.md` are internal/historical (FR, GSD-heavy). For the public repo, either (a) keep `CLAUDE.md` (useful contributor "how" doc — but strip the personal "État actuel / cluster" + my-kluster paths + any tgu.ovh already handled), or (b) move both to `docs/`. **Decision: keep `CLAUDE.md` (de-personalized via Task 2 sed) as `docs/ARCHITECTURE.md`; drop `spec.md`** (its content folds into README + ARCHITECTURE). Verify no `guyader`/`my-kluster` absolute paths remain in `docs/ARCHITECTURE.md`.

- [ ] **Step 9: report** the created files list.

---

## Task 4: Final pre-push audit on the export

**Files:** the whole export

- [ ] **Step 1: exhaustive PII + secret sweep (must be clean)**

```bash
cd /data/projets/perso/arr-stack-export
echo "== PII ==" ; grep -rniE 'emilie|thomas|\bzoe\b|garcons|guyader|tgu\.ovh' . --exclude-dir=.venv --exclude-dir=node_modules --exclude-dir=__pycache__ | grep -v series-scifi | head
echo "== secrets ==" ; grep -rnoE '"(apiKey|password|token)"\s*:\s*"[A-Za-z0-9+/=._-]{12,}"' . --include='*.json' --include='*.yml' --include='*.yaml' | grep -viE 'REDACT|<|example|placeholder|\$\{' | head
echo "== my-kluster abs paths ==" ; grep -rniE '/home/moi|my-kluster|selfhost\.svc' . --exclude-dir=.venv --exclude-dir=node_modules | grep -vE 'svc\.cluster\.local|<your' | head
echo "== :latest guard ==" ; grep -rnE 'tag:\s*"?latest"?' charts/ | head
echo "== governance present ==" ; for f in LICENSE SECURITY.md CONTRIBUTING.md CODE_OF_CONDUCT.md README.md .gitignore; do test -e "$f" && echo "ok $f" || echo "MISSING $f"; done
```
Expected: PII empty, secrets empty, no stray `/home/moi`/`my-kluster` (svc.cluster.local DNS is fine — it's generic k8s), no `:latest`, all governance present.

- [ ] **Step 2: helm lint + render the de-personalized chart**

```bash
cd /data/projets/perso/arr-stack-export
helm dependency build charts/arr-stack/ 2>/dev/null || true
# vendor app-template (same workaround as CI) then lint
helm pull bjw-s-labs/app-template --version 5.0.0 --untar --untardir charts/arr-stack/charts/ 2>/dev/null || true
for a in sonarr radarr prowlarr qbittorrent cleanuparr seerr flaresolverr jellyfin suggestarr arrconf configarr cross-seed qbit-manage arrconf-mcp arr-dashboard; do [ ! -d charts/arr-stack/charts/$a ] && cp -r charts/arr-stack/charts/app-template charts/arr-stack/charts/$a; done
helm lint charts/arr-stack/ -f examples/values-prod.yaml
```
Expected: `1 chart(s) linted, 0 chart(s) failed`. (The vendored `charts/arr-stack/charts/` is gitignored — not committed.)

- [ ] **Step 3: report** the audit result. ALL must be clean before Task 5.

---

## Task 5: Create the public repo (GATED — explicit user confirmation required)

**Do NOT run this task without the user confirming: (a) secrets rotated, (b) final repo name, (c) they've eyeballed the export.**

- [ ] **Step 1: confirm with the user** the new repo name (suggest `tom333/arr-stack` is taken+leaked → e.g. `tom333/arrstack` or rename old to `-private` and reuse the name). Get explicit go.

- [ ] **Step 2: init + squash to one clean commit**

```bash
cd /data/projets/perso/arr-stack-export
git init -b main
git add -A
git status --short | head -40   # eyeball: no .env, no snapshots, no .planning
git commit -m "feat: arr-stack — GitOps *arr media stack (Helm umbrella + arrconf reconciler + dashboard)

Apache-2.0. See README for quickstart + reference architecture."
```

- [ ] **Step 3: create the public repo + push** (after user confirms name `<NAME>`)

```bash
cd /data/projets/perso/arr-stack-export
gh repo create <NAME> --public --source=. --remote=origin --description "GitOps-managed *arr media stack: Helm umbrella chart + arrconf reconciler + lifecycle dashboard" --push
```

- [ ] **Step 4: post-push verification**

```bash
gh repo view <NAME> --json visibility,licenseInfo -q '{visibility:.visibility,license:.licenseInfo.spdxId}'
# GitHub should detect LICENSE → spdxId "Apache-2.0"
```
Expected: `PUBLIC` + `Apache-2.0`. Spot-check the GitHub file tree: no `.planning`, no `snapshots`, no PII.

- [ ] **Step 5: operator follow-ups (report, don't execute)**: make `tom333/arr-stack` (old) private; add repo topics/About; (optional later) publish the Helm chart to a GitHub-Pages Helm repo + Artifact Hub; decouple from my-kluster in docs.

---

## Self-Review

**Spec coverage (vs the audit + decisions):**
- New squashed clean repo, no history: Task 5 (git init + 1 commit). ✅
- Exclude `.planning/` + `docs/superpowers/` + snapshots + dev artifacts: Task 1 excludes + Task 3 `.gitignore`. ✅
- Apache-2.0: Task 3 Step 1 + Task 5 verify. ✅
- Monorepo (keep all tools + chart): Task 1 KEEP list. ✅
- De-personalize PII (kid names, domain) WITHOUT touching live configs: Task 2 operates on the export copy only; live repo untouched. ✅
- Secret leak not carried forward: snapshots excluded (Task 1) + secret sweeps (Tasks 1/4). Rotation is an operator precondition. ✅
- Governance (LICENSE/CONTRIBUTING/CoC/SECURITY/templates/README): Task 3. ✅
- Infra de-personalization (trackers, indexer IDs, tgu.ovh) + reference-arch docs: Task 2 Step 5 + Task 3 README. ✅
- Public-push gated on confirmation: Task 5 header + Step 1. ✅

**Placeholder scan:** Governance file contents are complete (not "TODO"); README is specified by required sections (acceptable for a doc-writing step — the writer fills prose, no code placeholder). ✅

**Consistency:** rename map identical in Task 2 sed, Task 2 verify, and Task 4 audit (`series-scifi` guard everywhere). Export path `/data/projets/perso/arr-stack-export` consistent across all tasks. ✅

**Risk notes:**
- The rename is a blunt global sed — Task 2 Step 3 (full test suites green) is the safety net proving uniformity. `\bzoe\b` substring risk is low (no English word contains it); the audit (Task 4) re-checks.
- `series-anime` (from series-zoe) must not collide with an existing `series-anime` category — verified: none exists in intent.yml today.
- Helm `examples/values-prod.yaml` still carries the reference hostPath/NodePort — that's intended (documented as reference arch in README), not PII; kept configurable.
