---
phase: 02-arrconf-cluster-validation
plan: 02
type: summary
wave: 1
status: complete
delivered_tag: 0.1.2
delivered_digest: sha256:c1e94fb9b07f1350d9414aabfeb2f3c5784b789ef4a7ee12d516b85039890b7e
ci_run_id: 25531943867
captured: 2026-05-08
---

# Plan 02-02 Summary — v0.1.x Image Release + GHCR Anonymous Pull

## Outcome

`ghcr.io/tom333/arr-stack-arrconf:0.1.2` published, **publicly pullable from a logged-out Docker daemon**. Phase 1 HUMAN-UAT #1 marked passed in `.planning/phases/01-arrconf-poc-json-schema/01-HUMAN-UAT.md` (item #1 result line updated 2026-05-08).

ROADMAP success criteria for v0.1.x release — **SATISFIED via v0.1.2** (v0.1.0 + v0.1.1 left in tag history as bootstrap artifacts; see Deviations).

## Machine-readable outputs

> Plan 02-03's grep consumer reads `image_tag_verified:` from inside this fenced block (B-NEW-01 contract).

```
image_tag_verified: 0.1.2
```

## Human-readable narrative

| Property | Value |
|---|---|
| Delivered tag | `0.1.2` (also `latest`, `sha-db0f163`, `branch-main` available) |
| Image digest | `sha256:c1e94fb9b07f1350d9414aabfeb2f3c5784b789ef4a7ee12d516b85039890b7e` |
| Image size | 153 MB (slightly over plan's ~80 MB target — acceptable; uv-built venv carries Python wheels) |
| CI workflow | `.github/workflows/arrconf-image.yml` |
| CI run ID | 25531943867 |
| CI conclusion | success |
| CI duration | ~14s build (cache hit on uv layers from earlier failed runs) |
| GHCR visibility | public (verified via anonymous pull from logged-out daemon — no manual UI toggle was needed) |
| Anonymous pull command | `docker logout ghcr.io && docker pull ghcr.io/tom333/arr-stack-arrconf:0.1.2` |
| Anonymous pull result | success — image downloaded, layers verified, then `docker rmi` cleanup OK |

## Pitfall 2 resolution

`metadata-action@v5` template `type=semver,pattern={{version}}` strips the leading `v` — confirmed empirically. **Plan 02-03 must use `0.1.2`** in `values.yaml.image.tag`, NOT `v0.1.2`. The regex patterns in 02-03 acceptance criteria already match `^v?0\.1\.[012]$` to be permissive, but the actual delivered literal is `0.1.2`.

## Deviations from plan

1. **v0.1.0 → v0.1.1 → v0.1.2 retarget chain** — two consecutive blockers consumed two semver bumps:
   - **v0.1.0**: pushed alongside the first-ever `git push -u origin main`. GitHub Actions did not fire arrconf-image.yml because the workflow file wasn't yet indexed on the default branch (well-known race for first-ever push of a repo with workflows). Tag stays in history per CLAUDE.md "Ne pas amender un tag de release publié".
   - **v0.1.1**: pushed after retarget. CI fired this time, but build failed: `ghcr.io/astral-sh/uv:0.11-python3.13-bookworm-slim: not found`. Latent Phase 1 bug — uv 0.9.x is current latest on PyPI, tags 0.5–0.9 exist on GHCR; 0.10/0.11 don't. Phase 1 never caught this because CI never ran. Fixed in commit `db0f163` (`fix(arrconf): pin uv builder image to 0.9 (latent Phase 1 bug)`).
   - **v0.1.2**: built and published successfully.

2. **GHCR visibility was already public** — the plan assumed GHCR defaults to private (Pitfall 7) and required a manual UI toggle. In practice, when the package was first published from a public repo via GitHub Actions, it inherited public visibility automatically. Anonymous pull worked first try. **The Pitfall 7 prediction did NOT manifest here.** Worth noting for future runs / different account configurations — GHCR's default visibility behavior may vary based on org/user settings.

3. **Token scope gap** — gh CLI auth (`tguyader`) lacks `read:packages` scope, so `gh api /users/tom333/packages/container/arr-stack-arrconf` returns 403. Substituted the dispositive check by querying the registry directly with an anonymous token (`https://ghcr.io/v2/tom333/arr-stack-arrconf/tags/list`), which both confirmed tag presence AND public visibility (anon access works = package is public). The `docker pull` from logged-out daemon is the redundant belt-and-braces verification.

4. **Image size 153 MB vs plan target ~80 MB** — uv multi-stage build doesn't strip as aggressively as plan estimate suggested. Not a blocker for Phase 2 (no size SLO defined). Worth revisiting in a future Phase 1 follow-up if image-size optimization becomes a goal.

## What this unblocks

- Plan 02-03 can now read `image_tag_verified: 0.1.2` from this SUMMARY's `## Machine-readable outputs` fenced block, write `.cluster-services` with `IMAGE_TAG_VERIFIED=0.1.2`, and substitute into `my-kluster/charts/arrconf/values.yaml.image.tag` without inference.
- ADR-3 (GHCR anonymous pull design) — verified end-to-end.
- REQ-bootstrap-exception runtime guarantee — image exists, is pullable, will run as the env-injection Pod in Wave 3.

## Commit chain

```
db0f163 fix(arrconf): pin uv builder image to 0.9 (latent Phase 1 bug)
76e2c97 docs(02): retarget image release v0.1.0 -> v0.1.1 (first-push race)
6a1795e docs(02-01): SUMMARY — pre-deploy snapshot baseline complete
38fa3ce snapshot(02): re-capture before-phase-2 baseline + evidence dir (ADR-6 / D-30 #1)
```

Tag refs on origin: `v0.1.0`, `v0.1.1`, `v0.1.2` — the first two are bootstrap-only; only `v0.1.2` corresponds to a published GHCR image.
