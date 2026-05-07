# arrconf

Reconcile *arr app configurations from YAML to REST APIs. Phase 1 POC scope: Sonarr `download_clients` only.

See [`spec.md`](../../spec.md) §6.1 for architecture, [`CLAUDE.md`](../../CLAUDE.md) for project conventions, and [ADR-5 frontière configarr](../../spec.md#adr-5-configarr-conservé) for the boundary with configarr.

## Phase 1 Scope

arrconf in Phase 1 is a POC. It implements **only** the Sonarr `download_clients` reconciler end-to-end, plus 4 forward-compat stubs for Phase 3 endpoints (indexer / notification / root_folder / host_config) and 4 frontière-configarr stubs that raise `ScopeViolationError` per ADR-5.

Scope expansion: Phase 3 (Radarr + Prowlarr + Sonarr extension), Phase 5 (qBittorrent), Phase 6 (Seerr), Phase 7 (Jellyfin).

## Prerequisites

- Python 3.13 (or `uv python install 3.13`)
- [uv 0.11+](https://docs.astral.sh/uv/) — installed via `pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Optional for live testing: `kubectl` with access to the `selfhost` namespace of `my-kluster`

## Install (local dev)

```bash
cd tools/arrconf
uv sync --frozen
uv run arrconf --help
```

## Quick start

### 1. Generate the JSON Schema

```bash
cd tools/arrconf
uv run arrconf schema-gen --output ../../schemas/arrconf-schema.json
```

Commit the result. CI verifies idempotence: any pydantic model change must regenerate `schemas/arrconf-schema.json` (D-15).

### 2. Dump cluster state → YAML (against port-forwarded Sonarr)

```bash
# Terminal 1: port-forward Sonarr from my-kluster
kubectl -n selfhost port-forward svc/sonarr 8989:8989

# Terminal 2: dump
cd tools/arrconf
export SONARR_API_KEY=$(grep sonarr-api-key /path/to/my-kluster/secrets/configarr-secret.yaml | awk '{print $2}')
cat > /tmp/arrconf.yml <<'YML'
apps:
  sonarr:
    main:
      base_url: http://localhost:8989
      download_clients:
        prune: false
        items: []
YML
uv run arrconf --config /tmp/arrconf.yml dump --apps sonarr --output ../../examples/baseline-sonarr.yml
```

The output file's first line is `# yaml-language-server: $schema=../schemas/arrconf-schema.json` (D-16).

### 3. Verify round-trip

```bash
uv run arrconf --config ../../examples/baseline-sonarr.yml diff --apps sonarr
# Exit code 0 (no drift) ; logs show "no_drift" event
uv run arrconf --config ../../examples/baseline-sonarr.yml apply --apps sonarr --dry-run
# Exit code 0 ; logs show "no-op"
```

## Subcommands

| Command | Purpose | Exit codes |
|---------|---------|------------|
| `arrconf apply --config PATH [--apps a,b] [--dry-run]` | Reconcile YAML → APIs | 0 ok / 1 app failure / 2 config error |
| `arrconf dump [--apps a,b] [--output PATH]` | Read-only export YAML | 0 ok / 1 app failure / 2 config error |
| `arrconf diff --config PATH [--apps a,b]` | Compare YAML vs cluster | 0 no drift / 1 app failure / 2 config error / **3 drift detected** |
| `arrconf schema-gen [--output PATH]` | Export JSON Schema (Draft 2020-12) | 0 ok |

Common flags: `--config/-c PATH`, `--log-level/-l LEVEL` (or `ARRCONF_LOG_LEVEL` env), `--dry-run` on `apply` (or `ARRCONF_DRY_RUN=true`).

## Variables d'environnement

| Var | Required for | Notes |
|-----|--------------|-------|
| `SONARR_API_KEY` | apply / dump / diff sonarr | Sonarr → Settings → General → Security ; Phase 2 injects via `envFrom: secretRef` |
| `RADARR_API_KEY` | Phase 3 | |
| `PROWLARR_API_KEY` | Phase 3 | |
| `ARRCONF_LOG_LEVEL` | optional | Default `INFO`. JSON output when not TTY (CronJob), pretty when TTY |
| `ARRCONF_DRY_RUN` | optional | If `true`, default `--dry-run` for `apply` |

Secrets are read **only** from env (D-22, T-01-01). pydantic-settings wraps them in `SecretStr` to mask in `repr()` and structured logs.

## Frontière arrconf / configarr

arrconf does **not** touch `quality_profiles`, `custom_formats`, `quality_definitions`, or `media_naming` — those are owned by [configarr](https://configarr.de/) per [ADR-5](../../spec.md#adr-5-configarr-conservé). Any attempt to reconcile those endpoints raises `ScopeViolationError` and exits with code 2.

See [CLAUDE.md "Frontière arrconf / configarr"](../../CLAUDE.md#frontière-arrconf--configarr-lire-avant-tout-dev) for the full table.

## VS Code autocomplete demo (REQ-yaml-autocomplete)

1. Install the [Red Hat YAML extension](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml).
2. Open `examples/baseline-sonarr.yml` in VS Code or code-server.
3. The first line `# yaml-language-server: $schema=../schemas/arrconf-schema.json` is interpreted by the extension; the bottom-right corner of VS Code should show a "YAML" indicator with the schema badge.
4. Position your cursor under `download_clients:` and type a space — VS Code suggests valid field names (`prune:`, `items:`).
5. Inside an item, hover over `protocol:` — the description from the pydantic `Field(description=...)` appears as a tooltip.
6. Type an invalid value (e.g., `protocol: ftp`) — a red squiggle appears under it (validation against the JSON Schema).

## GHCR image — one-time public visibility step (Pitfall 7)

The CI workflow `.github/workflows/arrconf-image.yml` builds and pushes `ghcr.io/tom333/arr-stack-arrconf` on every push to `main` and on `v*` tags. **GHCR images default to private.** After the first successful push:

1. Visit https://github.com/users/tom333/packages/container/arr-stack-arrconf/settings
2. Scroll to "Danger Zone" → "Change visibility" → select **Public**
3. Confirm. From now on, anonymous pulls work: `docker pull ghcr.io/tom333/arr-stack-arrconf:latest`

This step is required for the Phase 2 K8s pods to pull the image without `imagePullSecrets`.

Note: as of 2026-04, this step is not automatable via `gh` CLI ([RESEARCH.md Pitfall 7](../../.planning/phases/01-arrconf-poc-json-schema/01-RESEARCH.md)).

## Troubleshooting

- **401 Unauthorized** on `apply`/`dump`/`diff`: check `SONARR_API_KEY` is set and matches the Sonarr instance (Settings → General → Security).
- **`missing_api_key` event + exit 2**: env var was unset or empty when the subcommand ran. arrconf fast-fails rather than silently using `""` as the key (which would manifest as a confusing 401 from upstream). Set `SONARR_API_KEY` and retry.
- **CI fails on "schemas/arrconf-schema.json drift"**: you changed a pydantic model and forgot to regenerate. Run `cd tools/arrconf && uv run arrconf schema-gen --output ../../schemas/arrconf-schema.json` and commit (D-15).
- **`docker pull` fails with "denied"**: GHCR package is still private. See "GHCR image — one-time public visibility step" above.
- **`mypy` complains about untyped fields**: add type hints. CI is strict (`disallow_untyped_defs = true`).

## Tests

```bash
cd tools/arrconf
uv run pytest -x                                          # quick run, fail-fast
uv run pytest --cov --cov-fail-under=70                   # coverage gate
uv run pytest tests/test_round_trip.py -v                 # round-trip property
uv run pytest tests/test_scope_violation.py -v            # frontière configarr (T-01-05)
```

Coverage is scoped to `arrconf.differ` + `arrconf.reconcilers.sonarr` per [Pitfall 6 workaround](../../.planning/phases/01-arrconf-poc-json-schema/01-RESEARCH.md). All HTTP is mocked via `respx` — no live API calls in CI.

### Fixture redaction discipline (D-22, T-01-07)

Test fixtures under `tests/fixtures/` are sanitised copies of real Sonarr/Radarr API responses. Any string that resembles an API key, token, or password MUST be replaced with `***REDACTED***` BEFORE commit. CI runs a regex audit on every push; commits with a plausible secret in the fixtures are rejected. See [ADR-D-22](../../.planning/phases/01-arrconf-poc-json-schema/01-CONTEXT.md) and the snapshot redaction logic in `tools/snapshot/`.

## Snapshot discipline

Before any cluster test that writes to a new app or new resource type, **always** snapshot first:

```bash
tools/snapshot/snapshot.sh --apps sonarr --output snapshots/before-test-$(date +%FT%H%M)/
```

Snapshots are committed to git. See [ADR-6](../../spec.md#adr-6-snapshot-baseline-avant-toute-écriture) and [`tools/snapshot/README.md`](../snapshot/README.md).
