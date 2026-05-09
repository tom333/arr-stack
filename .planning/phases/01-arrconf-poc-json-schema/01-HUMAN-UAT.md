---
status: partial
phase: 01-arrconf-poc-json-schema
source: [01-VERIFICATION.md]
started: 2026-05-07T12:04:09Z
updated: 2026-05-09T00:30:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. GHCR public visibility toggle — confirm image `ghcr.io/tom333/arr-stack-arrconf` is publicly pullable
expected: After the first push to `main` triggers `arrconf-image.yml`, the image package on GHCR is accessible via `docker pull ghcr.io/tom333/arr-stack-arrconf:sha-<short>` from a logged-out client. Pitfall 7: by default new GHCR packages are private until manually toggled in the package settings UI.
result: [passed: 2026-05-08 — verified by Phase 2 Plan 02-02 anonymous pull test. Tag delivered: `0.1.2` (v0.1.0 first-push race + v0.1.1 latent uv:0.11 Dockerfile bug — see 02-02 deviation_note + db0f163 fix). Digest: sha256:c1e94fb9b07f1350d9414aabfeb2f3c5784b789ef4a7ee12d516b85039890b7e. `docker pull ghcr.io/tom333/arr-stack-arrconf:0.1.2` succeeded from logged-out daemon — package was already public-accessible (likely inherited from public repo, no manual UI toggle needed). Pitfall 7 prediction did NOT manifest in this case.]

### 2. VS Code autocomplete demo against `examples/baseline-sonarr.yml`
expected: Open `examples/baseline-sonarr.yml` in VS Code (or code-server) with the YAML language-server extension. The modeline on line 1 (`# yaml-language-server: $schema=../schemas/arrconf-schema.json`) resolves the schema. Typing under `download_clients:` shows autocomplete suggestions for valid `DownloadClient` fields, with hover-tooltips populated from the pydantic field descriptions.
result: [pending]

### 3. Live round-trip against a real Sonarr instance
expected: Against a running Sonarr v4+ instance (e.g. via `kubectl port-forward svc/sonarr 8989:8989`), `arrconf dump --apps sonarr > /tmp/live.yml` followed by `arrconf diff --config /tmp/live.yml --apps sonarr` reports zero drift (exit 0). Engine-level round-trip is already locked by the respx-mocked `test_round_trip_dump_apply_dry_run_is_noop`; this human check confirms it survives a live API. Belongs to Phase 2 (cluster validation) but listed here for traceability.
result: [passed: live round-trip 2026-05-09 — Plan 02.1-04 Task 4.3. Live `arrconf dump --apps sonarr` against the cluster Sonarr (kubectl port-forward 8989) produces 1277-byte YAML with `password: '********'` (Sonarr API mask, not a REDACTED leak — D-36 filter only drops literal `***REDACTED***` which Sonarr does not emit for download_client password fields). `arrconf diff --config <dump> --apps sonarr` exits 0 (no_drift event), proving REQ-idempotence reaffirmed end-to-end. PR3 apply Job (Plan 02.1-03) attached `arrconf-managed` tag id=1 to the qBit downloadclient (closes Phase 2 success #4). Drift detection demo (Plan 02.1-04 Task 4.2) captured `plan_action action=update` event but PUT 400 on credential re-validation — D-02.1-06 architectural finding documented in deferred-items.md, fix shipped in v0.1.4 via `?forceSave=true`. Evidence: .planning/phases/02.1-field-merge-fix/evidence/drift-demo-2026-05-09.log + snapshots/post-phase2.1-2026-05-09/ + snapshots/drift-test-2026-05-09/.]

## Summary

total: 3
passed: 2
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
