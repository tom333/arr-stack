---
phase: 04-umbrella-chart-migration-des-9-apps
plan: 04
type: execute
wave: 3
depends_on: ["04-03"]
files_modified:
  - charts/arr-stack/values.yaml
autonomous: true
requirements:
  - REQ-umbrella-deployment
  - REQ-renovate-image-tracking
tags: [helm, umbrella-chart, values, media-apps]
must_haves:
  truths:
    - "values.yaml gains 4 more top-level aliases: cleanuparr, seerr, flaresolverr, jellyfin"
    - "cleanuparr and flaresolverr are pinned away from `:latest` using the digest captured in evidence/current-image-tags.txt (or a registry-resolved semver tag the operator confirmed in Plan 01 SUMMARY)"
    - "flaresolverr has NO ingress block (internal-only service per PATTERNS Pitfall 10)"
    - "jellyfin ingress has NO oauth2-proxy annotations and KEEPS `nginx.ingress.kubernetes.io/proxy-body-size: \"0\"`"
    - "tools/scripts/check-renovate-annotations.sh exits 0 with all 8 media-app annotations present"
    - "`helm template … | kubeconform -strict -ignore-missing-schemas -kubernetes-version 1.33.0` exits 0"
  artifacts:
    - path: "charts/arr-stack/values.yaml"
      provides: "8 media-app aliases populated (sonarr, radarr, prowlarr, qbittorrent + cleanuparr, seerr, flaresolverr, jellyfin)"
      contains: "cleanuparr:"
      contains: "jellyfin:"
  key_links:
    - from: "charts/arr-stack/values.yaml (cleanuparr + flaresolverr tag fields)"
      to: ".planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/current-image-tags.txt"
      via: "Wave 0 captured the running digests; Plan 01 SUMMARY resolved them to semver or @sha256: pins"
      pattern: 'tag:'
    - from: "charts/arr-stack/values.yaml (flaresolverr alias)"
      to: "rendered flaresolverr Service"
      via: "no ingress block; flaresolverr is internal-only per PATTERNS Pitfall 10"
      pattern: "flaresolverr:"
---

<objective>
Populate the remaining 4 media-app aliases — cleanuparr, seerr, flaresolverr, jellyfin — in `charts/arr-stack/values.yaml`. Three of them have non-trivial deltas: cleanuparr is on `:latest` and needs pinning, flaresolverr has no ingress, and jellyfin opts out of oauth2-proxy and keeps a non-standard `proxy-body-size` annotation.

Purpose: Completes the byte-equivalent port of all 8 media apps. After this plan, only the 2 CronJob aliases (arrconf + configarr — Plan 05) remain.

Output: `values.yaml` with all 8 media aliases, ready for the CronJob plan.
</objective>

<executor_note>
**values.yaml is append-only across waves 2/3/4.** Plans 03, 04 (this plan), and 05 each append top-level alias blocks to `charts/arr-stack/values.yaml` in strict wave order. NO external tools (formatters, IDE auto-fixers, helm-values mutators) may rewrite this file between waves. If you find this plan starts with a values.yaml whose existing wave-2 (Plan 03) blocks have moved or changed indentation, STOP and re-establish the wave-2 state from git before continuing — the append-only invariant is what guarantees byte-equivalence at cutover (D-04-CUTOVER-03).
</executor_note>

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
@.planning/phases/04-umbrella-chart-migration-des-9-apps/04-01-pre-cutover-baseline-SUMMARY.md

<!-- Verbatim sources -->
@/home/moi/projets/perso/my-kluster/argocd/argocd-apps/cleanuparr-app.yaml
@/home/moi/projets/perso/my-kluster/argocd/argocd-apps/seerr-app.yaml
@/home/moi/projets/perso/my-kluster/argocd/argocd-apps/flaresolverr-app.yaml
@/home/moi/projets/perso/my-kluster/argocd/argocd-apps/jellyfin-app.yaml

@.planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/current-image-tags.txt

<interfaces>
<!-- Image pinning policy for the 3 :latest apps -->

cleanuparr   ghcr.io/cleanuparr/cleanuparr   Use the resolution recorded in 04-01-SUMMARY.md.
                                              Acceptable forms (in order of preference):
                                              1. `tag: "<semver>"` if operator confirmed a tag whose
                                                 digest matches `sha256:9b8f7a5f740c6cdc8f799a1d4b367ea560c0ce60799100afc3e14b6e3468cb5e`
                                              2. `tag: "latest@sha256:9b8f7a5f740c6cdc8f799a1d4b367ea560c0ce60799100afc3e14b6e3468cb5e"`
                                                 (digest pin — Renovate WILL still bump because the customManagers
                                                 regex matches the `tag:` line; ensure it parses, may need quoting)
                                              3. `tag: "2.3.3"` (latest available semver, RESEARCH-listed) + accept
                                                 Renovate will immediately propose a bump — that satisfies D-04-PIN-04
                                                 SC#2 E2E test target.

flaresolverr ghcr.io/flaresolverr/flaresolverr   Same options, digest = sha256:7962759d99d7e125e108e0f5e7f3cdbcd36161776d058d1d9b7153b92ef1af9e
                                                  Latest semver per RESEARCH: v3.4.6

The arrconf alias (Plan 05) is NOT in scope here.

<!-- jellyfin-specific delta -->
Jellyfin: NO oauth2-proxy (handles its own auth) BUT keeps `nginx.ingress.kubernetes.io/proxy-body-size: "0"` annotation.

<!-- flaresolverr-specific delta -->
Flaresolverr: NO ingress block AT ALL (internal-only). Only `service.main` + image + env. RESEARCH Pitfall 10.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 4.1: Add cleanuparr + seerr aliases (cleanuparr pinned)</name>
  <files>charts/arr-stack/values.yaml</files>
  <read_first>
    /home/moi/projets/perso/my-kluster/argocd/argocd-apps/cleanuparr-app.yaml (verbatim source — `tag: latest` MUST be replaced)
    /home/moi/projets/perso/my-kluster/argocd/argocd-apps/seerr-app.yaml (verbatim source — `tag: v3.2.0` already pinned, just add annotation)
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-PATTERNS.md §"values.yaml — cleanuparr alias" + §"values.yaml — seerr alias"
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-01-pre-cutover-baseline-SUMMARY.md (Plan 01 SUMMARY documents the resolved cleanuparr tag/digest — read it before writing this task's tag value)
  </read_first>
  <action>
    Append two blocks to `charts/arr-stack/values.yaml` after the qbittorrent alias (from Plan 03 Task 3.2).

    **cleanuparr alias** — verbatim from cleanuparr-app.yaml lines 18-65, with two mandatory deltas:
    1. Replace `tag: latest` with the pinned value from Plan 01 SUMMARY (`<semver>` if the operator resolved one, otherwise `latest@sha256:9b8f7a5f740c6cdc8f799a1d4b367ea560c0ce60799100afc3e14b6e3468cb5e`, otherwise `2.3.3` as the latest-known semver from RESEARCH §Running Image Digests). Whatever value is used MUST be quoted.
    2. Add `# renovate: image=ghcr.io/cleanuparr/cleanuparr` annotation.

    Cleanuparr has NO `PUID`/`PGID` (only `TZ`).

    ```yaml

    # ============================================================================
    # cleanuparr — Torrent cleanup automation (pinned away from :latest per D-04-PIN-01)
    # Source: my-kluster/argocd/argocd-apps/cleanuparr-app.yaml helm.values block (lines 18-65)
    # Tag pin: see Plan 01 SUMMARY — running digest sha256:9b8f7a5f... resolved
    #          to <semver or @sha256:> per operator pre-plan checkpoint.
    # ============================================================================
    cleanuparr:
      controllers:
        main:
          containers:
            main:
              image:
                # renovate: image=ghcr.io/cleanuparr/cleanuparr
                repository: ghcr.io/cleanuparr/cleanuparr
                tag: "2.3.3"  # RESEARCH §"Running Image Digests" fallback semver. If Plan 01 SUMMARY resolved a different value (e.g. exact digest match), prefer that — document substitution in this task's commit message.
              env:
                TZ: "Europe/Paris"
      service:
        main:
          controller: main
          ports:
            http:
              port: 11011
      ingress:
        main:
          className: nginx
          annotations:
            cert-manager.io/cluster-issuer: "letsencrypt-prod"
            nginx.ingress.kubernetes.io/auth-url: "https://auth.tgu.ovh/oauth2/auth"
            nginx.ingress.kubernetes.io/auth-signin: "https://auth.tgu.ovh/oauth2/start?rd=https://cleanuparr.tgu.ovh"
          hosts:
            - host: cleanuparr.tgu.ovh
              paths:
                - path: /
                  pathType: Prefix
                  service:
                    identifier: main
                    port: http
          tls:
            - secretName: cleanuparr-tls
              hosts:
                - cleanuparr.tgu.ovh
      persistence:
        config:
          type: persistentVolumeClaim
          accessMode: ReadWriteOnce
          size: 1Gi
          globalMounts:
            - path: /config
    ```

    **CRITICAL — tag substitution policy.** The YAML above ships with the concrete fallback `tag: "2.3.3"` (RESEARCH §"Running Image Digests" — latest available semver for cleanuparr at the time the plan was authored). BEFORE committing, READ `04-01-pre-cutover-baseline-SUMMARY.md` AND `evidence/current-image-tags.txt`. If Plan 01 SUMMARY resolved the running digest `sha256:9b8f7a5f…` to a DIFFERENT semver tag (e.g. cluster was upgraded between RESEARCH capture and Plan 01 execution), OR documented that NO semver tag matches the running digest, prefer Plan 01's resolved value:
    - Different semver: replace `2.3.3` with `<plan-01-semver>` and note the substitution in the commit message body (`Substituting cleanuparr 2.3.3 → X.Y.Z per Plan 01 SUMMARY (digest <hash> matched X.Y.Z, not 2.3.3)`).
    - No matching semver: replace with the digest form `tag: "latest@sha256:9b8f7a5f740c6cdc8f799a1d4b367ea560c0ce60799100afc3e14b6e3468cb5e"` — Renovate's customManagers regex still matches the `tag:` line.

    The placeholder-detection grep below (`! grep -q 'PIN_FROM_PLAN_01_SUMMARY' …`) remains as defense-in-depth — it catches a regression where someone re-introduces a `<PIN_FROM_PLAN_01_SUMMARY>` literal in the future.

    **seerr alias** — verbatim from seerr-app.yaml lines 18-65. No tag change (already `v3.2.0`). Add annotation. Seerr has no `PUID`/`PGID` (only `TZ`). Config path is `/app/config` (not `/config`).

    ```yaml

    # ============================================================================
    # seerr — Request manager (Overseerr fork, v3.2.0 already pinned upstream)
    # Source: my-kluster/argocd/argocd-apps/seerr-app.yaml helm.values block (lines 18-65)
    # ============================================================================
    seerr:
      controllers:
        main:
          containers:
            main:
              image:
                # renovate: image=ghcr.io/seerr-team/seerr
                repository: ghcr.io/seerr-team/seerr
                tag: "v3.2.0"
              env:
                TZ: "Europe/Paris"
      service:
        main:
          controller: main
          ports:
            http:
              port: 5055
      ingress:
        main:
          className: nginx
          annotations:
            cert-manager.io/cluster-issuer: "letsencrypt-prod"
            nginx.ingress.kubernetes.io/auth-url: "https://auth.tgu.ovh/oauth2/auth"
            nginx.ingress.kubernetes.io/auth-signin: "https://auth.tgu.ovh/oauth2/start?rd=https://seerr.tgu.ovh"
          hosts:
            - host: seerr.tgu.ovh
              paths:
                - path: /
                  pathType: Prefix
                  service:
                    identifier: main
                    port: http
          tls:
            - secretName: seerr-tls
              hosts:
                - seerr.tgu.ovh
      persistence:
        config:
          type: persistentVolumeClaim
          accessMode: ReadWriteOnce
          size: 2Gi
          globalMounts:
            - path: /app/config
    ```

    Smoke render:
    ```bash
    # Verify NO unreplaced placeholder remains:
    ! grep -q 'PIN_FROM_PLAN_01_SUMMARY' charts/arr-stack/values.yaml
    helm lint charts/arr-stack/
    tools/scripts/check-renovate-annotations.sh charts/arr-stack/values.yaml
    helm template arr-stack charts/arr-stack/ -f charts/arr-stack/values.yaml --namespace selfhost > /tmp/wave2-render-6.yaml
    grep -c 'host: cleanuparr.tgu.ovh' /tmp/wave2-render-6.yaml  # ≥ 2
    grep -c 'host: seerr.tgu.ovh' /tmp/wave2-render-6.yaml       # ≥ 2
    grep -c 'cleanuparr:latest' /tmp/wave2-render-6.yaml         # 0 (must be pinned)
    ```
  </action>
  <verify>
    <automated>
      helm lint charts/arr-stack/ && \
      tools/scripts/check-renovate-annotations.sh charts/arr-stack/values.yaml && \
      grep -q '^cleanuparr:' charts/arr-stack/values.yaml && \
      grep -q '^seerr:' charts/arr-stack/values.yaml && \
      ! grep -q 'PIN_FROM_PLAN_01_SUMMARY' charts/arr-stack/values.yaml && \
      ! helm template arr-stack charts/arr-stack/ -f charts/arr-stack/values.yaml --namespace selfhost | grep -q 'cleanuparr/cleanuparr:latest$' && \
      [ "$(helm template arr-stack charts/arr-stack/ -f charts/arr-stack/values.yaml --namespace selfhost | grep -c 'host: cleanuparr.tgu.ovh')" -ge 2 ]
    </automated>
  </verify>
  <acceptance_criteria>
    - Both new top-level keys present: `grep -cE '^(cleanuparr|seerr):$' charts/arr-stack/values.yaml` returns 2.
    - No `<PIN_FROM_PLAN_01_SUMMARY>` literal in values.yaml (defense-in-depth — the YAML embedded in this plan ships with concrete fallback values, so this grep is a regression guard): `grep -c 'PIN_FROM_PLAN_01_SUMMARY' charts/arr-stack/values.yaml` returns 0.
    - cleanuparr tag is NOT `latest`: the rendered Deployment image MUST NOT end in `:latest` (verify with `helm template … | grep -E 'image: .*cleanuparr/cleanuparr:[^l]'` returning a match, OR `grep cleanuparr/cleanuparr:latest$` returning 0).
    - All renovate annotations present: `tools/scripts/check-renovate-annotations.sh charts/arr-stack/values.yaml` exits 0.
    - Both hostnames rendered: `helm template … | grep -c 'host: cleanuparr.tgu.ovh'` >= 2; `grep -c 'host: seerr.tgu.ovh'` >= 2.
    - seerr config path: `helm template … | grep -E 'mountPath: /app/config'` returns at least 1 (vs `/config` for the *arr apps).
  </acceptance_criteria>
  <done>
    cleanuparr + seerr aliases populated. cleanuparr is no longer on `:latest`. 6 of 10 aliases complete.
  </done>
</task>

<task type="auto">
  <name>Task 4.2: Add flaresolverr (no ingress) + jellyfin (no oauth2-proxy, keeps proxy-body-size) aliases</name>
  <files>charts/arr-stack/values.yaml</files>
  <read_first>
    /home/moi/projets/perso/my-kluster/argocd/argocd-apps/flaresolverr-app.yaml (verbatim source — NO ingress block in source, line 35-36 comments confirm internal-only)
    /home/moi/projets/perso/my-kluster/argocd/argocd-apps/jellyfin-app.yaml (verbatim source — line 41-42 comments confirm Jellyfin handles own auth)
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-PATTERNS.md §"values.yaml — flaresolverr alias" + §"values.yaml — jellyfin alias"
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-RESEARCH.md §Pitfall 10 (flaresolverr no-ingress)
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-01-pre-cutover-baseline-SUMMARY.md (Plan 01 SUMMARY tag resolution for flaresolverr)
  </read_first>
  <action>
    Append two more blocks to `charts/arr-stack/values.yaml`.

    **flaresolverr alias** — verbatim from flaresolverr-app.yaml lines 18-36, with two deltas:
    1. Replace `tag: latest` with Plan 01 SUMMARY's resolved value (`v3.4.6` is the RESEARCH-listed latest semver; if the operator's digest resolves differently, prefer that).
    2. Add `# renovate: image=ghcr.io/flaresolverr/flaresolverr` annotation.
    3. **DO NOT add an `ingress:` block.** Flaresolverr is internal-only. RESEARCH Pitfall 10. The source unit App has comments (`# Pas d'ingress : accès interne uniquement`) — DO NOT preserve those comments in the umbrella.

    ```yaml

    # ============================================================================
    # flaresolverr — Cloudflare bypass for Prowlarr (internal-only, NO ingress)
    # Source: my-kluster/argocd/argocd-apps/flaresolverr-app.yaml helm.values block (lines 18-36)
    # Tag pin: see Plan 01 SUMMARY — running digest sha256:7962759d... resolved.
    # ============================================================================
    flaresolverr:
      controllers:
        main:
          containers:
            main:
              image:
                # renovate: image=ghcr.io/flaresolverr/flaresolverr
                repository: ghcr.io/flaresolverr/flaresolverr
                tag: "v3.4.6"  # RESEARCH §"Running Image Digests" fallback semver. If Plan 01 SUMMARY resolved a different value (e.g. exact digest match), prefer that — document substitution in this task's commit message.
              env:
                TZ: "Europe/Paris"
                LOG_LEVEL: "info"
      service:
        main:
          controller: main
          ports:
            http:
              port: 8191
      # NO ingress block — internal-only service (Prowlarr/qBit reach it via cluster DNS).
    ```

    **CRITICAL — tag substitution policy (same shape as Task 4.1).** The YAML above ships with the concrete fallback `tag: "v3.4.6"` (RESEARCH §"Running Image Digests" — latest available semver for flaresolverr). Prefer Plan 01 SUMMARY's resolved value if it differs (operator may have resolved a different semver or chosen the `@sha256:7962759d…` digest form). Document any substitution in this task's commit message. The placeholder-detection grep remains as defense-in-depth.

    **jellyfin alias** — verbatim from jellyfin-app.yaml lines 18-75. Deltas vs the *arr aliases:
    1. NO oauth2-proxy annotations (Jellyfin manages own auth — comment `# Pas d'oauth2-proxy ...` in source).
    2. KEEPS `nginx.ingress.kubernetes.io/proxy-body-size: "0"` annotation.
    3. NO `torrents` mount (Jellyfin does not download).
    4. Config PVC is `10Gi` (not 2Gi).
    5. DO NOT preserve the source comments (`# Pas d'oauth2-proxy ...`, `# Créer le compte admin immédiatement ...`, `# Stockage local : BDD SQLite ...`, `# NAS NFS — bibliothèque ...`) — they belong in the source unit App, not the umbrella.

    ```yaml

    # ============================================================================
    # jellyfin — Media server (NO oauth2-proxy — handles own auth; keeps proxy-body-size)
    # Source: my-kluster/argocd/argocd-apps/jellyfin-app.yaml helm.values block (lines 18-75)
    # ============================================================================
    jellyfin:
      controllers:
        main:
          containers:
            main:
              image:
                # renovate: image=lscr.io/linuxserver/jellyfin
                repository: lscr.io/linuxserver/jellyfin
                tag: "10.11.8"
              env:
                TZ: "Europe/Paris"
                PUID: "1000"
                PGID: "1000"
      service:
        main:
          controller: main
          ports:
            http:
              port: 8096
      ingress:
        main:
          className: nginx
          annotations:
            cert-manager.io/cluster-issuer: "letsencrypt-prod"
            nginx.ingress.kubernetes.io/proxy-body-size: "0"
          hosts:
            - host: jellyfin.tgu.ovh
              paths:
                - path: /
                  pathType: Prefix
                  service:
                    identifier: main
                    port: http
          tls:
            - secretName: jellyfin-tls
              hosts:
                - jellyfin.tgu.ovh
      persistence:
        config:
          type: persistentVolumeClaim
          accessMode: ReadWriteOnce
          size: 10Gi
          globalMounts:
            - path: /config
        media:
          type: persistentVolumeClaim
          existingClaim: media-nas-pvc
          globalMounts:
            - path: /media
    ```

    Smoke render and gate:
    ```bash
    ! grep -q 'PIN_FROM_PLAN_01_SUMMARY' charts/arr-stack/values.yaml
    helm lint charts/arr-stack/
    tools/scripts/check-renovate-annotations.sh charts/arr-stack/values.yaml

    helm template arr-stack charts/arr-stack/ -f charts/arr-stack/values.yaml --namespace selfhost > /tmp/wave2-final.yaml

    # flaresolverr has NO ingress (rendered):
    awk '/^  name: flaresolverr/,/^---/' /tmp/wave2-final.yaml | grep -c 'kind: Ingress'   # must be 0
    # jellyfin has NO oauth2-proxy annotations:
    awk '/^  name: jellyfin/,/^---/' /tmp/wave2-final.yaml | grep -c 'oauth2-proxy\|auth-url\|auth-signin'  # must be 0
    # jellyfin KEEPS proxy-body-size:
    awk '/^  name: jellyfin/,/^---/' /tmp/wave2-final.yaml | grep -c 'proxy-body-size'  # ≥ 1
    # No :latest images anywhere in the 8 media-app aliases:
    grep -cE 'image: .+:latest$' /tmp/wave2-final.yaml  # must be 0

    # All 8 media aliases produced a Service:
    grep -c '^kind: Service$' /tmp/wave2-final.yaml      # ≥ 8

    # Full kubeconform pass on rendered output:
    if command -v kubeconform >/dev/null 2>&1; then
      helm template arr-stack charts/arr-stack/ -f charts/arr-stack/values.yaml --namespace selfhost \
        | kubeconform -strict -ignore-missing-schemas -kubernetes-version 1.33.0
    else
      echo "kubeconform not installed locally — Plan 06 CI will run it. Skipping local pass."
    fi
    ```
  </action>
  <verify>
    <automated>
      helm lint charts/arr-stack/ && \
      tools/scripts/check-renovate-annotations.sh charts/arr-stack/values.yaml && \
      grep -q '^flaresolverr:' charts/arr-stack/values.yaml && \
      grep -q '^jellyfin:' charts/arr-stack/values.yaml && \
      ! grep -q 'PIN_FROM_PLAN_01_SUMMARY' charts/arr-stack/values.yaml && \
      [ "$(helm template arr-stack charts/arr-stack/ -f charts/arr-stack/values.yaml --namespace selfhost | awk '/name: flaresolverr/,/^---/' | grep -c 'kind: Ingress')" = "0" ] && \
      [ "$(helm template arr-stack charts/arr-stack/ -f charts/arr-stack/values.yaml --namespace selfhost | awk '/name: jellyfin/,/^---/' | grep -c 'oauth2-proxy\|auth-url\|auth-signin')" = "0" ] && \
      helm template arr-stack charts/arr-stack/ -f charts/arr-stack/values.yaml --namespace selfhost | awk '/name: jellyfin/,/^---/' | grep -q 'proxy-body-size' && \
      [ "$(grep -cE '^(sonarr|radarr|prowlarr|cleanuparr|qbittorrent|seerr|flaresolverr|jellyfin):$' charts/arr-stack/values.yaml)" -ge 8 ]
    </automated>
  </verify>
  <acceptance_criteria>
    - All 8 media aliases present: `grep -cE '^(sonarr|radarr|prowlarr|cleanuparr|qbittorrent|seerr|flaresolverr|jellyfin):$' charts/arr-stack/values.yaml` returns 8.
    - `tools/scripts/check-renovate-annotations.sh charts/arr-stack/values.yaml` exits 0.
    - Annotation count for media apps: `grep -c '^[[:space:]]*# renovate: image=' charts/arr-stack/values.yaml` returns at least 8.
    - No `:latest` survives in rendered output: `helm template … | grep -cE 'image: .+:latest$'` returns 0.
    - Flaresolverr has NO Ingress in rendered output (block-based grep above returns 0).
    - Jellyfin Ingress has NO oauth2-proxy annotations (block-based grep returns 0) AND keeps `proxy-body-size` (block-based grep returns at least 1).
    - All 8 media apps produce at least one rendered Service: `helm template … | grep -c '^kind: Service$'` >= 8.
    - `helm lint charts/arr-stack/` exits 0.
  </acceptance_criteria>
  <done>
    All 8 media-app aliases populated and byte-equivalent (modulo intentional cleanups: no PUID for cleanuparr/seerr/flaresolverr; no ingress for flaresolverr; no oauth2-proxy for prowlarr/jellyfin). Plan 05 will add the 2 CronJob aliases.
  </done>
</task>

</tasks>

<verification>
- `helm lint charts/arr-stack/` exits 0.
- All 8 media-app top-level keys exist in values.yaml.
- `tools/scripts/check-renovate-annotations.sh charts/arr-stack/values.yaml` exits 0.
- No `:latest` survives anywhere in the rendered output.
- Flaresolverr renders no Ingress; Jellyfin renders no oauth2-proxy annotations.
</verification>

<success_criteria>
The 8 media apps are fully ported. Plan 05 adds the arrconf + configarr CronJob aliases — the chart will then have all 10 aliases populated and is ready for CI gating (Plan 06).
</success_criteria>

<output>
After completion, create `.planning/phases/04-umbrella-chart-migration-des-9-apps/04-04-media-aliases-misc-SUMMARY.md`.
</output>
