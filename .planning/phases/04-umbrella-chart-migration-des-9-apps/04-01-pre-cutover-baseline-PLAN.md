---
phase: 04-umbrella-chart-migration-des-9-apps
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/current-image-tags.txt
  - .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd/sonarr.yaml
  - .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd/radarr.yaml
  - .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd/prowlarr.yaml
  - .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd/cleanuparr.yaml
  - .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd/qbittorrent.yaml
  - .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd/seerr.yaml
  - .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd/flaresolverr.yaml
  - .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd/jellyfin.yaml
  - .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd/arrconf.yaml
  - .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd/configarr.yaml
  - tools/scripts/check-renovate-annotations.sh
  - tools/scripts/byte-equivalence-diff.sh
autonomous: false
requirements:
  - REQ-umbrella-deployment
  - REQ-renovate-image-tracking
  - REQ-helm-validation
tags: [helm, kubernetes, argocd, baseline]
must_haves:
  truths:
    - "Currently-running image identifiers (image + digest) for qbittorrent / flaresolverr / cleanuparr are captured in evidence/current-image-tags.txt and committed"
    - "ArgoCD-managed manifests for all 10 unit Applications are exported into evidence/pre-cutover-argocd/ as the byte-equivalence baseline"
    - "tools/scripts/check-renovate-annotations.sh exits 0 against an empty/missing values.yaml today (no annotations to check) and exits 1 when a repository: line lacks an annotation"
    - "tools/scripts/byte-equivalence-diff.sh produces a diff report when called against the baseline directory"
  artifacts:
    - path: ".planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/current-image-tags.txt"
      provides: "Operator-captured image + digest pairs for qbittorrent/flaresolverr/cleanuparr (D-04-PIN-02)"
      contains: "qbittorrent"
    - path: ".planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd/sonarr.yaml"
      provides: "Pre-cutover Sonarr rendered manifests (ADR-6 baseline)"
    - path: "tools/scripts/check-renovate-annotations.sh"
      provides: "Renovate annotation enforcement helper (used by chart-lint.yml in Wave 4)"
      executable: true
    - path: "tools/scripts/byte-equivalence-diff.sh"
      provides: "Byte-equivalence diff automation (used in Wave 6 cutover)"
      executable: true
  key_links:
    - from: "evidence/current-image-tags.txt"
      to: "charts/arr-stack/values.yaml"
      via: "Wave 2/3 tasks read this file to populate tag: <semver> | tag: <existing>@sha256:<digest>"
      pattern: "current-image-tags.txt"
    - from: "evidence/pre-cutover-argocd/*.yaml"
      to: "tools/scripts/byte-equivalence-diff.sh"
      via: "Wave 6 cutover diff input"
      pattern: "pre-cutover-argocd"
---

<objective>
Capture the ADR-6 pre-cutover baseline and seed two helper scripts that downstream waves will use.

Purpose: Phase 4 is a migration with byte-equivalence as the verification gate (D-04-CUTOVER-03). Without a captured baseline of what ArgoCD currently renders for the 10 unit Apps and without the running image digests for the 3 `:latest` apps, Waves 2/3 cannot pin correctly and Wave 6 cannot verify the cutover. The two helper scripts live in `tools/scripts/` so they are reusable artefacts (not throwaway one-liners) and CI can call them in Wave 4.

Output: `evidence/current-image-tags.txt`, `evidence/pre-cutover-argocd/{10 files}.yaml`, `tools/scripts/check-renovate-annotations.sh`, `tools/scripts/byte-equivalence-diff.sh`.
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
@.planning/phases/04-umbrella-chart-migration-des-9-apps/04-VALIDATION.md
@CLAUDE.md
@spec.md

<interfaces>
<!-- The 10 unit ArgoCD Applications whose rendered output we are about to baseline.
     `argocd app manifests <name>` returns the K8s manifests ArgoCD currently considers the source of truth.
     If argocd CLI is unavailable on the workstation (STATE.md Phase 02.2 P05 lesson), fall back to
     `kubectl get application <name> -n argocd -o yaml` and then `kubectl get <kind> -n selfhost <name> -o yaml`
     per resource — slower but dispositive. -->

Unit App names (use in `argocd app manifests` loop):
  sonarr, radarr, prowlarr, cleanuparr, qbittorrent, seerr, flaresolverr, jellyfin, arrconf, configarr

Cluster context:
  namespace: selfhost
  argocd namespace: argocd
  current running images (RESEARCH §Running Image Digests, 2026-05-12):
    qbittorrent  lscr.io/linuxserver/qbittorrent:latest    sha256:2e0148428b6769e2ee1eb6781246b6fca4b70cd680edfcb16e7113d9d6cb1631
    flaresolverr ghcr.io/flaresolverr/flaresolverr:latest  sha256:7962759d99d7e125e108e0f5e7f3cdbcd36161776d058d1d9b7153b92ef1af9e
    cleanuparr   ghcr.io/cleanuparr/cleanuparr:latest      sha256:9b8f7a5f740c6cdc8f799a1d4b367ea560c0ce60799100afc3e14b6e3468cb5e
</interfaces>
</context>

<tasks>

<task type="checkpoint:human-action" gate="blocking">
  <name>Task 1.1: Operator captures currently-running image identifiers and ArgoCD manifests</name>
  <files>
    .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/current-image-tags.txt
    .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd/sonarr.yaml
    .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd/radarr.yaml
    .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd/prowlarr.yaml
    .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd/cleanuparr.yaml
    .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd/qbittorrent.yaml
    .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd/seerr.yaml
    .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd/flaresolverr.yaml
    .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd/jellyfin.yaml
    .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd/arrconf.yaml
    .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd/configarr.yaml
  </files>
  <read_first>
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-CONTEXT.md (D-04-PIN-02 verbatim command)
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-RESEARCH.md §Running Image Digests + §Unknown #10 (exact commands)
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-PATTERNS.md §Wave 0
  </read_first>
  <what-built>
    NOTHING by Claude yet — this is the operator gate that produces the inputs Waves 2/3/6 consume.
  </what-built>
  <how-to-verify>
    OPERATOR must run BOTH command blocks below on a workstation with `kubectl` and (ideally) `argocd` access to the cluster, then commit the outputs.

    **Step 1 — image identifiers (D-04-PIN-02 verbatim):**
    ```bash
    mkdir -p .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence
    for app in qbittorrent flaresolverr cleanuparr; do
      kubectl -n selfhost get pod -l app.kubernetes.io/name=$app \
        -o jsonpath='{.spec.containers[0].image}{"\n"}{.status.containerStatuses[0].imageID}{"\n---\n"}'
    done > .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/current-image-tags.txt
    cat .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/current-image-tags.txt
    ```
    Expected: three blocks separated by `---`, each with `<repo>:<tag>` then `<repo>@sha256:<digest>` (RESEARCH baseline confirms qbittorrent digest is `sha256:2e014842…`, flaresolverr `sha256:7962759d…`, cleanuparr `sha256:9b8f7a5f…`). If a digest has drifted since 2026-05-12, the NEW digest is authoritative — Waves 2/3 will pin to whatever this file says.

    **Step 2 — ArgoCD-managed manifests (ADR-6 baseline, RESEARCH §Unknown #10 block C):**
    ```bash
    mkdir -p .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd
    # Primary path — argocd CLI:
    for app in sonarr radarr prowlarr cleanuparr qbittorrent seerr flaresolverr jellyfin arrconf configarr; do
      argocd app manifests $app \
        > .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd/${app}.yaml
    done

    # Fallback (if `argocd` CLI not installed — STATE.md Phase 02.2 P05 lesson):
    # for app in sonarr radarr prowlarr cleanuparr qbittorrent seerr flaresolverr jellyfin arrconf configarr; do
    #   kubectl -n argocd get application $app -o jsonpath='{.status.sync.compareWith.target}' \
    #     > .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd/${app}.yaml
    #   # If target field is empty, capture all live K8s objects labeled with the app instead:
    #   # kubectl -n selfhost get all,ingress,configmap,pvc,secret -l app.kubernetes.io/instance=$app -o yaml > ...
    # done
    ```

    **Step 3 — anti-leak audit then commit:**
    ```bash
    grep -RinE '(api-key|apikey|password|token|secret).*[:=].{8,}' \
      .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/ || echo "no secret literals found"
    # If grep matches anything that is NOT envFrom.secretRef metadata, redact before commit.
    git add .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/
    git commit -m "docs(04): pre-cutover ADR-6 snapshot + running image digests"
    ```

    Then type `approved` (along with any operator notes about argocd CLI availability) so the executor can resume with Task 1.2.
  </how-to-verify>
  <acceptance_criteria>
    - File exists: `wc -l .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/current-image-tags.txt` returns at least 9 lines (3 blocks × 3 lines each).
    - Each :latest app appears: `grep -c 'qbittorrent\|flaresolverr\|cleanuparr' .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/current-image-tags.txt` returns at least 3.
    - All 10 ArgoCD manifest exports exist: `ls .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd/ | wc -l` returns 10.
    - Each export is non-empty: `find .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd/ -type f -size 0` returns no results.
    - Anti-leak pass: the grep audit above does not match any literal credential (only envFrom.secretRef names like `arrconf-env`).
    - Evidence committed: `git log -1 --name-only | grep -c 'evidence/'` >= 11.
    - **evidence/ NOT git-ignored** (CLAUDE.md "Ne pas ignorer snapshots/ dans .gitignore" applies to evidence/ too): `git check-ignore -v .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/ ; test $? -eq 1` (exit code 1 = NOT ignored = correct state). If `.gitignore` currently matches the path, ADD a negation rule `!.planning/phases/*/evidence/**` to `.gitignore` in this same commit BEFORE staging the evidence files.
  </acceptance_criteria>
  <resume-signal>Type "approved" once both files are committed and the operator has noted whether `argocd` CLI is available (impacts Wave 6 task scripting).</resume-signal>
</task>

<task type="auto">
  <name>Task 1.2: Author tools/scripts/check-renovate-annotations.sh and tools/scripts/byte-equivalence-diff.sh</name>
  <files>tools/scripts/check-renovate-annotations.sh, tools/scripts/byte-equivalence-diff.sh</files>
  <read_first>
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-PATTERNS.md §"tools/scripts/check-renovate-annotations.sh" + §"tools/scripts/byte-equivalence-diff.sh" (both scripts have verbatim shell source)
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-RESEARCH.md §Unknown #9 (byte-equivalence diff procedure + exclusion list)
    CLAUDE.md §"Conventions Helm — umbrella chart" §"Annotations Renovate (CRITIQUE)" (annotation format = `# renovate: image=<repo>` above `repository: <same-repo>`)
  </read_first>
  <action>
    Create `tools/scripts/check-renovate-annotations.sh` with mode `0755` containing exactly this body (verbatim from PATTERNS.md §"tools/scripts/check-renovate-annotations.sh"):

    ```bash
    #!/usr/bin/env bash
    # Check that every 'repository:' line in values.yaml has a preceding renovate annotation.
    # Usage: tools/scripts/check-renovate-annotations.sh [path/to/values.yaml]
    # Exits 0 if every repository: line is preceded by `# renovate: image=<same-repo>`.
    # Exits 1 if any repository: line is missing the annotation OR if the annotation repo
    # does not match the repository: value (e.g. annotation for sonarr above radarr's repo).
    set -euo pipefail

    FILE="${1:-charts/arr-stack/values.yaml}"

    if [[ ! -f "$FILE" ]]; then
      echo "ERROR: file not found: $FILE" >&2
      exit 1
    fi

    violations=0
    # Walk the file with awk; remember the previous non-blank, non-pure-whitespace line.
    # When we see a `repository:` key, the previous non-empty line MUST be
    # `# renovate: image=<repo>` where <repo> matches the value of `repository:`.
    awk '
      function trim(s) { sub(/^[[:space:]]+/, "", s); sub(/[[:space:]]+$/, "", s); return s }
      /^[[:space:]]*#/ || NF==0 { if (NF>0) prev_comment = trim($0); next_handled=0 }
      /^[[:space:]]*repository:[[:space:]]*/ {
        sub(/^[[:space:]]*repository:[[:space:]]*/, "")
        repo = trim($0)
        # Strip optional quotes
        gsub(/["'"'"']/, "", repo)
        expected = "# renovate: image=" repo
        if (prev_comment != expected) {
          printf("LINE %d: missing/mismatched annotation. expected=\"%s\" got=\"%s\"\n", NR, expected, prev_comment) > "/dev/stderr"
          exit 1
        }
        prev_comment = ""
        next
      }
      { prev_comment = "" }
    ' "$FILE"

    echo "OK: every repository: line in $FILE has a matching '# renovate: image=' annotation."
    ```

    Create `tools/scripts/byte-equivalence-diff.sh` with mode `0755` containing exactly this body (verbatim from PATTERNS.md §"tools/scripts/byte-equivalence-diff.sh" with the exclusion list from RESEARCH.md §Unknown #9):

    ```bash
    #!/usr/bin/env bash
    # Diff `helm template charts/arr-stack/` rendered output against the
    # ArgoCD-managed baseline captured in evidence/pre-cutover-argocd/.
    # Exits 0 if every per-app diff is empty after excluding ArgoCD-injected fields.
    # Usage: tools/scripts/byte-equivalence-diff.sh [evidence-dir] [values-file]
    set -euo pipefail

    EVIDENCE_DIR="${1:-.planning/phases/04-umbrella-chart-migration-des-9-apps/evidence}"
    VALUES_FILE="${2:-examples/values-prod.yaml}"
    APPS="sonarr radarr prowlarr cleanuparr qbittorrent seerr flaresolverr jellyfin arrconf configarr"

    # Fields ArgoCD injects that legitimately differ between unit Apps and the
    # umbrella render (RESEARCH §Unknown #9 — NOT regressions).
    EXCLUDE_PATTERN='argocd\.argoproj\.io|app\.kubernetes\.io/instance|helm\.sh/chart|kubectl\.kubernetes\.io/last-applied-configuration|resourceVersion|uid:|creationTimestamp'

    mkdir -p "$EVIDENCE_DIR/umbrella-rendered"

    helm template arr-stack charts/arr-stack/ \
      -f "$VALUES_FILE" \
      --namespace selfhost \
      > "$EVIDENCE_DIR/umbrella-rendered/all.yaml"

    failed=0
    for app in $APPS; do
      base="$EVIDENCE_DIR/pre-cutover-argocd/${app}.yaml"
      if [[ ! -f "$base" ]]; then
        echo "SKIP: $base not found (run Task 1.1 first)"
        continue
      fi
      diff_out=$(diff \
        <(grep -v -E "$EXCLUDE_PATTERN" "$base" | sort) \
        <(grep -v -E "$EXCLUDE_PATTERN" "$EVIDENCE_DIR/umbrella-rendered/all.yaml" \
            | awk -v app="$app" 'BEGIN{p=0} /^---/ {p=0} $0 ~ ("name: " app "([^[:alnum:]_-]|$)") {p=1} p' \
            | sort) \
        || true)
      if [[ -z "$diff_out" ]]; then
        echo "OK : $app byte-equivalent"
      else
        echo "DIFF: $app — see $EVIDENCE_DIR/byte-equivalence-${app}.diff"
        printf "%s\n" "$diff_out" > "$EVIDENCE_DIR/byte-equivalence-${app}.diff"
        failed=$((failed + 1))
      fi
    done

    if [[ $failed -gt 0 ]]; then
      echo "$failed app(s) failed byte-equivalence check"
      exit 1
    fi
    echo "All 10 apps byte-equivalent."
    ```

    Make both scripts executable: `chmod +x tools/scripts/check-renovate-annotations.sh tools/scripts/byte-equivalence-diff.sh`.

    Smoke-test the annotation checker against a temporary fixture (it MUST fail until values.yaml is created; this proves negative-path):
    ```bash
    # Negative path — file does not exist yet, so the checker exits 1.
    ./tools/scripts/check-renovate-annotations.sh charts/arr-stack/values.yaml && echo "BUG: should have failed" || echo "OK: failed as expected because values.yaml does not exist yet"

    # Negative path — repository line with NO annotation must trigger violations.
    cat > /tmp/check-renovate-test-bad.yaml <<'EOF'
    sonarr:
      controllers:
        main:
          containers:
            main:
              image:
                repository: lscr.io/linuxserver/sonarr
                tag: "4.0.17"
    EOF
    ./tools/scripts/check-renovate-annotations.sh /tmp/check-renovate-test-bad.yaml \
      && { echo "BUG: should have failed"; exit 1; } \
      || echo "OK: negative path detected missing annotation"

    # Positive path — annotation present and matching.
    cat > /tmp/check-renovate-test-good.yaml <<'EOF'
    sonarr:
      controllers:
        main:
          containers:
            main:
              image:
                # renovate: image=lscr.io/linuxserver/sonarr
                repository: lscr.io/linuxserver/sonarr
                tag: "4.0.17"
    EOF
    ./tools/scripts/check-renovate-annotations.sh /tmp/check-renovate-test-good.yaml \
      || { echo "BUG: should have passed"; exit 1; }
    echo "OK: positive path passed"
    rm -f /tmp/check-renovate-test-{bad,good}.yaml
    ```

    Do NOT commit `/tmp/check-renovate-test-*.yaml` — they are smoke fixtures only.

    No need to smoke-test `byte-equivalence-diff.sh` in this plan; Wave 6 owns the live run because the umbrella chart does not exist yet.
  </action>
  <verify>
    <automated>
      test -x tools/scripts/check-renovate-annotations.sh && \
      test -x tools/scripts/byte-equivalence-diff.sh && \
      head -1 tools/scripts/check-renovate-annotations.sh | grep -q '^#!/usr/bin/env bash' && \
      head -1 tools/scripts/byte-equivalence-diff.sh | grep -q '^#!/usr/bin/env bash' && \
      bash -n tools/scripts/check-renovate-annotations.sh && \
      bash -n tools/scripts/byte-equivalence-diff.sh
    </automated>
  </verify>
  <acceptance_criteria>
    - Both scripts have executable bit set: `test -x tools/scripts/check-renovate-annotations.sh && test -x tools/scripts/byte-equivalence-diff.sh`.
    - Both start with `#!/usr/bin/env bash`: `head -1 tools/scripts/{check-renovate-annotations,byte-equivalence-diff}.sh | grep -c '#!/usr/bin/env bash'` returns 2.
    - Both pass `bash -n` syntax check (no execution): `bash -n tools/scripts/check-renovate-annotations.sh && bash -n tools/scripts/byte-equivalence-diff.sh`.
    - check-renovate-annotations.sh smoke-tested: negative path on `/tmp/check-renovate-test-bad.yaml` exits 1, positive path on `/tmp/check-renovate-test-good.yaml` exits 0 (both runs documented in SUMMARY).
    - byte-equivalence-diff.sh includes the EXCLUDE_PATTERN regex containing `argocd.argoproj.io`, `app.kubernetes.io/instance`, AND `helm.sh/chart`: `grep -c 'argocd.argoproj.io\|app.kubernetes.io/instance\|helm.sh/chart' tools/scripts/byte-equivalence-diff.sh` returns at least 3.
  </acceptance_criteria>
  <done>
    Both helper scripts committed in tools/scripts/, syntax-clean, with the annotation checker smoke-tested on synthetic positive + negative inputs. Wave 4 chart-lint.yml will call check-renovate-annotations.sh. Wave 6 cutover will call byte-equivalence-diff.sh.
  </done>
</task>

</tasks>

<verification>
- `wc -l .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/current-image-tags.txt` >= 9
- `ls .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd/ | wc -l` == 10
- `test -x tools/scripts/check-renovate-annotations.sh && test -x tools/scripts/byte-equivalence-diff.sh`
- `bash -n tools/scripts/check-renovate-annotations.sh && bash -n tools/scripts/byte-equivalence-diff.sh`
- Anti-leak grep on `evidence/` returns no credential literals.
</verification>

<success_criteria>
Wave 0 unblocks the rest of the phase: subsequent plans can read concrete digest pins for the 3 `:latest` apps from `evidence/current-image-tags.txt`, can run byte-equivalence diff against `evidence/pre-cutover-argocd/`, and the CI workflow being authored in Wave 4 can call `tools/scripts/check-renovate-annotations.sh` without it being a forward reference.
</success_criteria>

<output>
After completion, create `.planning/phases/04-umbrella-chart-migration-des-9-apps/04-01-pre-cutover-baseline-SUMMARY.md` covering:
- `argocd` CLI availability (impacts Wave 6 cutover task wording).
- Resolved semver tags for qbittorrent / flaresolverr / cleanuparr (from operator-resolved digest → tag lookup, or "use @sha256:<digest> syntax" decision).
- Any redactions applied during anti-leak audit.
- The smoke-test output for `check-renovate-annotations.sh` (positive + negative).
</output>
