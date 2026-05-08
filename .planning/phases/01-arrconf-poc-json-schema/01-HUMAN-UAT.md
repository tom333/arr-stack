---
status: partial
phase: 01-arrconf-poc-json-schema
source: [01-VERIFICATION.md]
started: 2026-05-07T12:04:09Z
updated: 2026-05-07T12:04:09Z
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
result: [partial: Phase 2 Plan 02-05 ran apply against real Sonarr; `managed_tag_created` event emitted + arrconf-managed tag (id=1) created in Sonarr ✅. PUT downloadclient/1 then failed with HTTP 400 because YAML overwrites qBit credentials with `''` and Sonarr's pre-save validation can't authenticate to qBit. Phase 1 design issue: secrets cannot be safely represented in YAML. Tag stays orphan in Sonarr. Deferred to Phase 3 (or Phase 2.1 interrupt) — fix is to merge cluster's stored field values for sensitive/empty fields before PUT. See arr-stack/.planning/phases/02-arrconf-cluster-validation/02-05-SUMMARY.md §Root cause.]

## Summary

total: 3
passed: 1
issues: 1
pending: 1
skipped: 0
blocked: 0

## Gaps
