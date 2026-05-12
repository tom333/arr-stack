---
phase: 04-umbrella-chart-migration-des-9-apps
plan: 06
type: execute
wave: 5
depends_on: ["04-05"]
files_modified:
  - .github/workflows/chart-lint.yml
  - renovate.json
  - examples/values-prod.yaml
autonomous: true
requirements:
  - REQ-helm-validation
  - REQ-renovate-image-tracking
tags: [ci, renovate, helm, kubeconform, github-actions]
must_haves:
  truths:
    - "`.github/workflows/chart-lint.yml` exists and runs on PRs touching the chart, values, examples, renovate.json, or itself"
    - "The workflow installs Helm, adds bjw-s-labs Helm repo, runs `helm dependency update`, `helm lint`, renders the chart, and pipes the output through kubeconform with the 1.33.0 schema"
    - "The workflow validates `renovate.json` syntax via `npx renovate-config-validator` AND calls `tools/scripts/check-renovate-annotations.sh`"
    - "`renovate.json` carries the customManagers regex from RESEARCH §Unknown #4 (combination strategy) AND a packageRules block auto-merging minor/patch but gating majors"
    - "`examples/values-prod.yaml` exists and is byte-identical to `charts/arr-stack/values.yaml` (D-04-VALUES-03)"
    - "The chart-lint workflow run is green on the branch that introduces these files"
  artifacts:
    - path: ".github/workflows/chart-lint.yml"
      provides: "CI gate for chart correctness (lint + kubeconform + renovate validator + annotation check)"
      contains: "kubeconform"
    - path: "renovate.json"
      provides: "Bot config: customManagers regex matching `# renovate: image=` annotations in values.yaml; packageRules for automerge policy"
      contains: "customManagers"
    - path: "examples/values-prod.yaml"
      provides: "Documentation copy of the production values (D-04-VALUES-03); used as the -f input by both CI and the operator at cutover"
  key_links:
    - from: ".github/workflows/chart-lint.yml"
      to: "tools/scripts/check-renovate-annotations.sh"
      via: "CI step `- name: Check renovate annotations` runs the script"
      pattern: "check-renovate-annotations.sh"
    - from: "renovate.json customManagers regex"
      to: "charts/arr-stack/values.yaml `# renovate: image=` annotations"
      via: "Renovate cloud-side bot reads renovate.json, finds annotations, opens bump PRs"
      pattern: "matchStrings"
    - from: "examples/values-prod.yaml"
      to: "charts/arr-stack/values.yaml"
      via: "examples is a documentation copy/symlink — kept in sync (mention in README)"
      pattern: "examples/values-prod.yaml"
---

<objective>
Wire the chart into a CI gate (lint + render + kubeconform + schema + Renovate config validator + annotation check) and configure Renovate's customManagers so the `# renovate: image=` annotations placed in Plans 03/04/05 actually drive bump PRs.

Purpose: REQ-helm-validation requires `helm lint` + kubeconform + schema parsing to gate every PR. REQ-renovate-image-tracking requires a working customManagers regex. SC#2 (REQ-pr-to-cluster-latency E2E) cannot be tested until Renovate config is in place.

Output: One new workflow file, an updated renovate.json, and a `examples/values-prod.yaml` documentation copy.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/04-umbrella-chart-migration-des-9-apps/04-CONTEXT.md
@.planning/phases/04-umbrella-chart-migration-des-9-apps/04-RESEARCH.md
@.planning/phases/04-umbrella-chart-migration-des-9-apps/04-PATTERNS.md
@CLAUDE.md
@.github/workflows/tests.yml
@renovate.json
@charts/arr-stack/values.yaml

<interfaces>
<!-- chart-lint.yml workflow shape — verbatim from RESEARCH §Unknown #6 + PATTERNS §".github/workflows/chart-lint.yml" target block -->

Trigger paths:
  pull_request:
    - charts/arr-stack/**
    - examples/**
    - renovate.json
    - .github/workflows/chart-lint.yml
    - tools/scripts/check-renovate-annotations.sh   <-- added by this plan
  push (branches: [main]):
    - charts/arr-stack/**
    - examples/**

Helm repo to register: bjw-s-labs at https://bjw-s-labs.github.io/helm-charts

kubeconform flags: -strict -ignore-missing-schemas -kubernetes-version 1.33.0
(K8s cluster runs 1.33.9 — RESEARCH §Environment Availability)

losisin schema action: losisin/helm-values-schema-json@v1 (validates values.yaml against values.schema.json)
renovate-config-validator: npx --yes renovate-config-validator renovate.json

<!-- Renovate customManagers — verbatim from RESEARCH §Unknown #4 -->
matchStringsStrategy: combination
regex 1: #\s*renovate:\s*image=(?<depName>[^\s]+)\s*\n\s*repository:\s*(?<registryUrl>.*?)\/
regex 2: \s*tag:\s*["']?(?<currentValue>[^\s"']+)["']?
datasource: docker

packageRules:
  minor/patch/pin/digest → automerge: true
  major                  → automerge: false, labels: ["major-update"]
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 6.1: Author .github/workflows/chart-lint.yml (Helm + kubeconform + schema + renovate + annotations)</name>
  <files>.github/workflows/chart-lint.yml</files>
  <read_first>
    .github/workflows/tests.yml (existing workflow — structural analog: checkout, setup, run; replace `uv` setup with `helm` setup)
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-RESEARCH.md §Unknown #6 (verbatim workflow YAML)
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-PATTERNS.md §".github/workflows/chart-lint.yml" (analog mapping)
    tools/scripts/check-renovate-annotations.sh (the script the workflow will call — already in place from Plan 01 Task 1.2)
  </read_first>
  <action>
    Create `.github/workflows/chart-lint.yml` with EXACTLY this content (verbatim base from RESEARCH §Unknown #6, with the annotation-checker step added):

    ```yaml
    name: chart-lint

    on:
      pull_request:
        paths:
          - 'charts/arr-stack/**'
          - 'examples/**'
          - 'renovate.json'
          - '.github/workflows/chart-lint.yml'
          - 'tools/scripts/check-renovate-annotations.sh'
      push:
        branches: [main]
        paths:
          - 'charts/arr-stack/**'
          - 'examples/**'

    jobs:
      lint:
        runs-on: ubuntu-24.04
        permissions:
          contents: read
        steps:
          - uses: actions/checkout@v4

          - name: Set up Helm
            uses: azure/setup-helm@v4
            with:
              version: 'latest'

          - name: Add bjw-s chart repo
            run: helm repo add bjw-s-labs https://bjw-s-labs.github.io/helm-charts

          - name: Helm dependency update
            run: helm dependency update charts/arr-stack/

          - name: Helm lint
            run: helm lint charts/arr-stack/ -f examples/values-prod.yaml

          - name: Install kubeconform
            run: |
              curl -sL https://github.com/yannh/kubeconform/releases/latest/download/kubeconform-linux-amd64.tar.gz \
                | sudo tar xz -C /usr/local/bin

          - name: Render and validate manifests
            run: |
              helm template arr-stack charts/arr-stack/ \
                -f examples/values-prod.yaml \
                --namespace selfhost \
                | kubeconform \
                  -strict \
                  -ignore-missing-schemas \
                  -kubernetes-version 1.33.0

          - name: Validate values.yaml against values.schema.json
            uses: losisin/helm-values-schema-json@v1
            with:
              input: charts/arr-stack/values.yaml
              schema: charts/arr-stack/values.schema.json
              fail-on-errors: true

          - name: Validate Renovate config syntax
            run: npx --yes renovate-config-validator renovate.json

          - name: Check renovate annotations on every repository line
            run: bash tools/scripts/check-renovate-annotations.sh charts/arr-stack/values.yaml

          - name: Assert no :latest tag survives
            run: |
              if helm template arr-stack charts/arr-stack/ \
                   -f examples/values-prod.yaml \
                   --namespace selfhost \
                   | grep -E 'image:[[:space:]]+[^[:space:]]+:latest$'; then
                echo "::error::A :latest tag was found in the rendered output — pin it."
                exit 1
              fi
              echo "OK: no :latest tag in rendered output."

      # B3 Path A — Auto-tag on green merge to main.
      # Eliminates the manual T1→T2 release-tag step (Plan 09 Task 9.2 SC#2 latency).
      # Renovate auto-merges minor/patch PRs (renovate.json packageRules); this job
      # immediately cuts a patch tag so my-kluster's Renovate scan picks up the new
      # revision within the next scan cycle (~1h default).
      auto-tag:
        needs: lint
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        runs-on: ubuntu-24.04
        permissions:
          contents: write
        steps:
          - uses: actions/checkout@v4
            with:
              fetch-depth: 0
          - name: Bump patch tag (semver vX.Y.Z)
            uses: mathieudutour/github-tag-action@v6.2
            with:
              github_token: ${{ secrets.GITHUB_TOKEN }}
              default_bump: patch
              tag_prefix: v
              release_branches: main
              # Tag format MUST match the semver regex ^v[0-9]+\.[0-9]+\.[0-9]+$
              # so my-kluster's Renovate (using github-tags datasource on this repo)
              # discovers the bump.
    ```

    Notes:
    - The `Add bjw-s chart repo` step BEFORE `helm dependency update` is mandatory (RESEARCH Pitfall 9 — without it the dependency update fails on the GitHub runner because no Helm repo is registered).
    - `kubeconform -kubernetes-version 1.33.0` matches the cluster K8s version (1.33.9; minor.patch don't matter — kubeconform uses minor for schema lookup).
    - The `losisin/helm-values-schema-json@v1` action handles values↔schema validation independently of `helm lint`'s built-in check (belt-and-braces per RESEARCH §Unknown #8).
    - The `:latest` assertion step is a final guard in case the schema regex was too permissive (Plan 05 Task 5.2 acknowledged this risk).
    - **`auto-tag` job (B3 Path A)** runs only on push to `main` (post-merge); it depends on `lint` so a red CI blocks the tag. The action `mathieudutour/github-tag-action@v6.2` is pinned by tag — Renovate will manage future bumps via `helmv3`/`github-actions` managers. This job is what eliminates the manual T1→T2 release-tag latency that Plan 09 SC#2 timeline used to depend on the operator for.

    Smoke-test locally if `act` is installed (optional) — otherwise rely on opening a PR. Skip local smoke; the next step is Task 6.2.
  </action>
  <verify>
    <automated>
      test -f .github/workflows/chart-lint.yml && \
      python3 -c "import yaml; yaml.safe_load(open('.github/workflows/chart-lint.yml'))" && \
      grep -q 'azure/setup-helm@v4' .github/workflows/chart-lint.yml && \
      grep -q 'helm repo add bjw-s-labs' .github/workflows/chart-lint.yml && \
      grep -q 'kubeconform' .github/workflows/chart-lint.yml && \
      grep -q 'kubernetes-version 1.33.0' .github/workflows/chart-lint.yml && \
      grep -q 'losisin/helm-values-schema-json@v1' .github/workflows/chart-lint.yml && \
      grep -q 'renovate-config-validator' .github/workflows/chart-lint.yml && \
      grep -q 'check-renovate-annotations.sh' .github/workflows/chart-lint.yml && \
      grep -q ':latest' .github/workflows/chart-lint.yml && \
      grep -q 'auto-tag:' .github/workflows/chart-lint.yml && \
      grep -q 'mathieudutour/github-tag-action' .github/workflows/chart-lint.yml && \
      grep -q "contents: write" .github/workflows/chart-lint.yml
    </automated>
  </verify>
  <acceptance_criteria>
    - File exists and is valid YAML.
    - `lint` job has all 9 required steps: checkout, setup-helm, repo add, dependency update, lint, kubeconform install, render+kubeconform, schema validation, renovate config validation, annotation check, :latest guard.
    - **`auto-tag` job (B3 Path A)** exists, has `needs: lint`, is gated by `if: github.event_name == 'push' && github.ref == 'refs/heads/main'`, has `permissions: contents: write`, and uses `mathieudutour/github-tag-action@v6.2` with `default_bump: patch` + `tag_prefix: v` so produced tags match `^v[0-9]+\.[0-9]+\.[0-9]+$`.
    - Trigger paths include `charts/arr-stack/**`, `examples/**`, `renovate.json`, the workflow itself, AND `tools/scripts/check-renovate-annotations.sh`.
    - kubeconform pinned to K8s schema `1.33.0`.
    - losisin schema action pinned to `@v1`.
    - bjw-s repo URL is `https://bjw-s-labs.github.io/helm-charts` (the `bjw-s-labs` org).
    - When this branch is pushed AND a PR is opened, the workflow MUST run and exit 0 (verified manually by Plan SUMMARY).
  </acceptance_criteria>
  <done>
    CI workflow is in place. When the PR for this plan opens, the workflow runs against the populated chart and must be green.
  </done>
</task>

<task type="auto">
  <name>Task 6.2: Update renovate.json with customManagers + packageRules and create examples/values-prod.yaml</name>
  <files>renovate.json, examples/values-prod.yaml</files>
  <read_first>
    renovate.json (current file — 3-line `extends: ["config:recommended"]` stub)
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-RESEARCH.md §Unknown #4 (exact customManagers + packageRules JSON)
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-PATTERNS.md §"renovate.json (modified)" (target verbatim)
    charts/arr-stack/values.yaml (the file customManagers will scan)
  </read_first>
  <action>
    **Step A — overwrite `renovate.json`** with EXACTLY this content (verbatim from RESEARCH §Unknown #4 "Exact `renovate.json` patch"):

    ```json
    {
      "$schema": "https://docs.renovatebot.com/renovate-schema.json",
      "extends": ["config:recommended"],
      "customManagers": [
        {
          "customType": "regex",
          "managerFilePatterns": ["/charts/arr-stack/values\\.yaml$"],
          "matchStringsStrategy": "combination",
          "matchStrings": [
            "#\\s*renovate:\\s*image=(?<depName>[^\\s]+)\\s*\\n\\s*repository:\\s*(?<registryUrl>.*?)\\/",
            "\\s*tag:\\s*[\"']?(?<currentValue>[^\\s\"']+)[\"']?"
          ],
          "datasourceTemplate": "docker"
        }
      ],
      "packageRules": [
        {
          "matchManagers": ["regex", "helmv3", "helm-values"],
          "matchUpdateTypes": ["minor", "patch", "pin", "digest"],
          "automerge": true
        },
        {
          "matchManagers": ["regex", "helmv3", "helm-values"],
          "matchUpdateTypes": ["major"],
          "automerge": false,
          "labels": ["major-update"]
        }
      ]
    }
    ```

    Validate locally:
    ```bash
    npx --yes renovate-config-validator renovate.json
    # Expected: "Validating renovate.json … OK"
    python3 -c "import json; json.load(open('renovate.json'))"   # syntactic JSON parse
    ```

    **Step B — create `examples/values-prod.yaml` as a verbatim copy of `charts/arr-stack/values.yaml`** (D-04-VALUES-03 — examples is the documentation duplicate; the future `arr-stack-app.yaml` in my-kluster has empty `helm.values:`, so `values.yaml` IS prod).

    ```bash
    mkdir -p examples
    cp charts/arr-stack/values.yaml examples/values-prod.yaml
    # Verify byte equivalence:
    diff charts/arr-stack/values.yaml examples/values-prod.yaml   # must produce no output
    ```

    Optional alternative: use a symlink (`ln -s ../charts/arr-stack/values.yaml examples/values-prod.yaml`). However, GitHub does NOT render symlinks well in the web UI, and `helm lint -f` on a symlink works but is less obvious to forking operators. PREFER a real file copy + a README note in Plan 07 stating it must be kept in sync (or fold the copy into a future pre-commit hook in a v0.2.x follow-up — out of scope for Phase 4).

    Smoke-test the customManagers regex against the populated values.yaml:
    ```bash
    # This is a sanity check using grep against the patterns Renovate will compile.
    grep -E '#\s*renovate:\s*image=' charts/arr-stack/values.yaml | wc -l
    # Expected ≥ 10 (one annotation per alias image — sonarr/radarr/prowlarr/cleanuparr/qbittorrent/seerr/flaresolverr/jellyfin/arrconf/configarr).
    grep -E 'tag: "[^"]+"' charts/arr-stack/values.yaml | wc -l
    # Expected ≥ 10.
    ```

    **W4 — customManagers regex extraction test.** `renovate-config-validator` only validates renovate.json SYNTAX, not that the regex actually captures the named groups against values.yaml. Run a synthetic extraction test with Python so a CI green run dispositively proves the regex will fire when Renovate scans:

    ```bash
    python3 <<'EOF'
    import json, re, sys
    cfg = json.load(open('renovate.json'))
    cm = cfg['customManagers'][0]
    patterns = [re.compile(p, re.MULTILINE) for p in cm['matchStrings']]
    values_text = open('charts/arr-stack/values.yaml').read()

    # Renovate uses combination strategy: each pattern matches independently, captures are merged
    # by position. We replicate the same logic here.
    matches_p1 = list(patterns[0].finditer(values_text))
    matches_p2 = list(patterns[1].finditer(values_text))

    # Each annotation block has: pattern 1 (depName + registryUrl) immediately followed by pattern 2 (currentValue)
    if len(matches_p1) < 10:
        print(f'FAIL: pattern 1 matched only {len(matches_p1)} times, expected >= 10')
        sys.exit(1)
    if len(matches_p2) < 10:
        print(f'FAIL: pattern 2 matched only {len(matches_p2)} times, expected >= 10')
        sys.exit(1)

    # Verify the 3 named groups are populated for the first 10 annotations
    triples = []
    for m1 in matches_p1[:10]:
        depName = m1.group('depName')
        registryUrl = m1.group('registryUrl')
        # Find the first pattern 2 match AFTER this pattern 1 match
        for m2 in matches_p2:
            if m2.start() > m1.end():
                currentValue = m2.group('currentValue')
                triples.append((depName, registryUrl, currentValue))
                break
        else:
            print(f'FAIL: no tag found after annotation for {depName}')
            sys.exit(1)

    for dep, reg, val in triples:
        if not dep or not reg or not val:
            print(f'FAIL: empty capture group — depName={dep!r} registryUrl={reg!r} currentValue={val!r}')
            sys.exit(1)

    print(f'MATCH: N={len(triples)} image tuples')
    for dep, reg, val in triples:
        print(f'  depName={dep}  registryUrl={reg}  currentValue={val}')
    EOF
    ```

    Expected output: `MATCH: N=10 image tuples` followed by 10 triples (one per alias). Acceptance criterion below grep-checks for this stdout token.

    Finally, run the full chart-lint workflow's first 3 local-equivalent commands to make sure Plan 06 commit will not break CI:
    ```bash
    helm repo add bjw-s-labs https://bjw-s-labs.github.io/helm-charts 2>/dev/null || true
    helm dependency update charts/arr-stack/
    helm lint charts/arr-stack/ -f examples/values-prod.yaml
    helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml --namespace selfhost > /dev/null
    npx --yes renovate-config-validator renovate.json
    tools/scripts/check-renovate-annotations.sh charts/arr-stack/values.yaml
    ```
    All commands must exit 0.
  </action>
  <verify>
    <automated>
      python3 -c "import json; json.load(open('renovate.json'))" && \
      grep -q 'customManagers' renovate.json && \
      grep -q '"matchStringsStrategy": "combination"' renovate.json && \
      grep -q '"datasourceTemplate": "docker"' renovate.json && \
      grep -q 'packageRules' renovate.json && \
      grep -q '"automerge": true' renovate.json && \
      grep -q 'major-update' renovate.json && \
      npx --yes renovate-config-validator renovate.json && \
      diff -q charts/arr-stack/values.yaml examples/values-prod.yaml && \
      helm lint charts/arr-stack/ -f examples/values-prod.yaml && \
      tools/scripts/check-renovate-annotations.sh charts/arr-stack/values.yaml
    </automated>
  </verify>
  <acceptance_criteria>
    - `renovate.json` is valid JSON: `python3 -c "import json; json.load(open('renovate.json'))"` exits 0.
    - `npx --yes renovate-config-validator renovate.json` exits 0.
    - `renovate.json` contains the `customManagers` block with `matchStringsStrategy: combination`, `datasourceTemplate: docker`, and BOTH regex strings.
    - `renovate.json` contains the `packageRules` block with `automerge: true` for minor/patch AND `automerge: false` + `major-update` label for major.
    - `examples/values-prod.yaml` exists and is byte-identical to `charts/arr-stack/values.yaml`: `diff -q charts/arr-stack/values.yaml examples/values-prod.yaml` shows no difference.
    - `helm lint charts/arr-stack/ -f examples/values-prod.yaml` exits 0.
    - The chart `tools/scripts/check-renovate-annotations.sh charts/arr-stack/values.yaml` exits 0.
    - At least 10 `# renovate: image=` annotations across values.yaml (one per alias image).
    - **W4 — customManagers regex extraction test passes**: the Python one-liner above (loads `renovate.json`, compiles the two `matchStrings` regexes, applies them to `charts/arr-stack/values.yaml`) prints `MATCH: N=10 image tuples` and exits 0. This dispositively proves Renovate's regex will fire when it scans the file. If the test fails or N<10, the customManagers regex is broken — fix it before merging. Falls back to "first live Renovate scan is authoritative" only if the synthetic test is infeasible (e.g. Python not available on the runner — not applicable here since CI uses ubuntu-24.04 which ships Python).
  </acceptance_criteria>
  <done>
    Renovate is configured to discover all 10 image tags via customManagers; examples/values-prod.yaml is the canonical input for `helm template` in CI and for the operator at cutover. The next plan (07) refreshes the docs; Plan 08 ships the cross-repo cutover.
  </done>
</task>

</tasks>

<verification>
- `.github/workflows/chart-lint.yml` is valid YAML and has all required steps.
- `renovate.json` validates against `npx renovate-config-validator`.
- `examples/values-prod.yaml` is byte-equivalent to `charts/arr-stack/values.yaml`.
- All Wave 0 scripts called by the CI workflow are present and executable.
- The PR that introduces these files MUST trigger the workflow and the workflow MUST be green.
</verification>

<success_criteria>
CI gate is in place. Plan 07 (docs) and Plan 08 (cross-repo cutover) can rely on the workflow catching chart regressions.
</success_criteria>

<output>
After completion, create `.planning/phases/04-umbrella-chart-migration-des-9-apps/04-06-ci-renovate-SUMMARY.md`. Include in particular the URL of the chart-lint CI run for the PR introducing this workflow.
</output>
