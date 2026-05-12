---
phase: 04-umbrella-chart-migration-des-9-apps
plan: 03
type: execute
wave: 2
depends_on: ["04-02"]
files_modified:
  - charts/arr-stack/values.yaml
autonomous: true
requirements:
  - REQ-umbrella-deployment
  - REQ-renovate-image-tracking
tags: [helm, umbrella-chart, values, media-apps]
must_haves:
  truths:
    - "values.yaml has top-level sonarr, radarr, prowlarr, qbittorrent alias keys, each populated with the verbatim helm.values block from the corresponding my-kluster unit ArgoCD Application"
    - "Every repository: line in these 4 aliases has a preceding `# renovate: image=<same-repo>` annotation — per D-04-PIN-03 (mandatory renovate annotation)"
    - "qbittorrent image is pinned to `tag: \"5.2.0\"` (RESEARCH-verified semver match for the running digest sha256:2e014842...)"
    - "Prowlarr opts out of oauth2-proxy: its ingress annotations block lists only cert-manager (commented oauth2-proxy lines from analog are NOT included)"
    - "`helm template arr-stack charts/arr-stack/ -f charts/arr-stack/values.yaml | kubeconform -strict -ignore-missing-schemas -kubernetes-version 1.33.0` exits 0"
    - "tools/scripts/check-renovate-annotations.sh exits 0 against the new values.yaml"
  artifacts:
    - path: "charts/arr-stack/values.yaml"
      provides: "Top-level keys: sonarr, radarr, prowlarr, qbittorrent (each = full helm.values block + renovate annotation on repository line)"
      contains: "sonarr:"
      contains: "qbittorrent:"
  key_links:
    - from: "charts/arr-stack/values.yaml (sonarr alias)"
      to: "charts/arr-stack/charts/app-template-4.6.2.tgz"
      via: "Helm sub-chart rendering — alias key matches dependencies[].alias in Chart.yaml"
      pattern: "sonarr:"
    - from: "charts/arr-stack/values.yaml (qbittorrent alias tag)"
      to: ".planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/current-image-tags.txt"
      via: "Wave 0 captured digest sha256:2e014842 → RESEARCH resolved to semver 5.2.0"
      pattern: 'tag: "5.2.0"'
---

<objective>
Populate four top-level alias keys in `charts/arr-stack/values.yaml` — sonarr, radarr, prowlarr, qbittorrent — by lifting each block verbatim from the matching `helm.values:` payload of the my-kluster unit ArgoCD Application, plus a `# renovate: image=<repo>` annotation on every `repository:` line. Pin `qbittorrent` away from `:latest` per D-04-PIN-01.

Purpose: D-04-CUTOVER-03 requires byte-equivalent rendering between the umbrella and the current unit Apps. Lifting verbatim is the only way to guarantee that. The Renovate annotation is the mandatory contract per CLAUDE.md ("Sans ça, Renovate ne suit pas") and is the SC#2 test target.

Output: A populated `values.yaml` (4 of 10 aliases — Plan 04 covers cleanuparr, seerr, flaresolverr, jellyfin; Plan 05 covers arrconf + configarr CronJobs).
</objective>

<executor_note>
**values.yaml is append-only across waves 2/3/4.** Plans 03 (this plan), 04, and 05 each append top-level alias blocks to `charts/arr-stack/values.yaml` in strict wave order. NO external tools (formatters, IDE auto-fixers, helm-values mutators) may rewrite this file between waves. If you find a wave-N+1 plan starts with a values.yaml whose existing wave-N blocks have moved or changed indentation, STOP and re-establish the wave-N state from git before continuing — the append-only invariant is what guarantees byte-equivalence at cutover (D-04-CUTOVER-03).
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
@CLAUDE.md

<!-- Verbatim byte-equivalence sources — read these in entirety -->
@/home/moi/projets/perso/my-kluster/argocd/argocd-apps/sonarr-app.yaml
@/home/moi/projets/perso/my-kluster/argocd/argocd-apps/radarr-app.yaml
@/home/moi/projets/perso/my-kluster/argocd/argocd-apps/prowlarr-app.yaml
@/home/moi/projets/perso/my-kluster/argocd/argocd-apps/qbittorrent-app.yaml

<!-- Wave 0 digest pin source -->
@.planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/current-image-tags.txt

<interfaces>
<!-- Pin reference table — copy these EXACTLY into the values.yaml tags. -->

App           Image                                       Tag        Source
sonarr        lscr.io/linuxserver/sonarr                  4.0.17    (sonarr-app.yaml line 25 — UNCHANGED, no `:latest`)
radarr        lscr.io/linuxserver/radarr                  6.1.1     (radarr-app.yaml line 25 — UNCHANGED)
prowlarr      lscr.io/linuxserver/prowlarr                2.3.5     (prowlarr-app.yaml line 25 — UNCHANGED)
qbittorrent   lscr.io/linuxserver/qbittorrent             5.2.0     (RESEARCH §Running Image Digests — digest sha256:2e014842 == tag 5.2.0)

<!-- Renovate annotation contract — verbatim format from CLAUDE.md -->
# renovate: image=<exact-same-repo-string>
repository: <exact-same-repo-string>
tag: "<pinned-version>"
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 3.1: Add sonarr + radarr aliases to values.yaml</name>
  <files>charts/arr-stack/values.yaml</files>
  <read_first>
    /home/moi/projets/perso/my-kluster/argocd/argocd-apps/sonarr-app.yaml (lines 18-80 — `helm.values:` block — verbatim source)
    /home/moi/projets/perso/my-kluster/argocd/argocd-apps/radarr-app.yaml (lines 18-80 — verbatim source)
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-PATTERNS.md §"values.yaml — sonarr alias" + §"values.yaml — radarr alias"
    CLAUDE.md §"Annotations Renovate (CRITIQUE)" (verbatim annotation format)
  </read_first>
  <action>
    Open `charts/arr-stack/values.yaml` (currently the placeholder comment stub from Plan 02). Keep the existing header comment, then append the following two blocks.

    Lift sonarr's `helm.values:` block (sonarr-app.yaml lines 18-80) verbatim, wrap in top-level `sonarr:` key, dedent two spaces, and insert `# renovate: image=lscr.io/linuxserver/sonarr` on the line immediately ABOVE `repository: lscr.io/linuxserver/sonarr`. STRIP the YAML comments from the source (`# Même hostPath que qBittorrent...`, `# NAS NFS — destination finale...`) — they belong in the source unit Apps, not the umbrella (PATTERNS.md "Translation notes" for sonarr).

    Expected content to append:

    ```yaml

    # ============================================================================
    # sonarr — TV series manager
    # Source: my-kluster/argocd/argocd-apps/sonarr-app.yaml helm.values block (lines 18-80)
    # ============================================================================
    sonarr:
      controllers:
        main:
          containers:
            main:
              image:
                # renovate: image=lscr.io/linuxserver/sonarr
                repository: lscr.io/linuxserver/sonarr
                tag: "4.0.17"
              env:
                TZ: "Europe/Paris"
                PUID: "1000"
                PGID: "1000"
      service:
        main:
          controller: main
          ports:
            http:
              port: 8989
      ingress:
        main:
          className: nginx
          annotations:
            cert-manager.io/cluster-issuer: "letsencrypt-prod"
            nginx.ingress.kubernetes.io/auth-url: "https://auth.tgu.ovh/oauth2/auth"
            nginx.ingress.kubernetes.io/auth-signin: "https://auth.tgu.ovh/oauth2/start?rd=https://sonarr.tgu.ovh"
          hosts:
            - host: sonarr.tgu.ovh
              paths:
                - path: /
                  pathType: Prefix
                  service:
                    identifier: main
                    port: http
          tls:
            - secretName: sonarr-tls
              hosts:
                - sonarr.tgu.ovh
      persistence:
        config:
          type: persistentVolumeClaim
          accessMode: ReadWriteOnce
          size: 2Gi
          globalMounts:
            - path: /config
        torrents:
          type: hostPath
          hostPath: /opt/media-stack/torrents
          hostPathType: DirectoryOrCreate
          globalMounts:
            - path: /data/torrents
        media:
          type: persistentVolumeClaim
          existingClaim: media-nas-pvc
          globalMounts:
            - path: /media

    # ============================================================================
    # radarr — Movie manager
    # Source: my-kluster/argocd/argocd-apps/radarr-app.yaml helm.values block (lines 18-80)
    # ============================================================================
    radarr:
      controllers:
        main:
          containers:
            main:
              image:
                # renovate: image=lscr.io/linuxserver/radarr
                repository: lscr.io/linuxserver/radarr
                tag: "6.1.1"
              env:
                TZ: "Europe/Paris"
                PUID: "1000"
                PGID: "1000"
      service:
        main:
          controller: main
          ports:
            http:
              port: 7878
      ingress:
        main:
          className: nginx
          annotations:
            cert-manager.io/cluster-issuer: "letsencrypt-prod"
            nginx.ingress.kubernetes.io/auth-url: "https://auth.tgu.ovh/oauth2/auth"
            nginx.ingress.kubernetes.io/auth-signin: "https://auth.tgu.ovh/oauth2/start?rd=https://radarr.tgu.ovh"
          hosts:
            - host: radarr.tgu.ovh
              paths:
                - path: /
                  pathType: Prefix
                  service:
                    identifier: main
                    port: http
          tls:
            - secretName: radarr-tls
              hosts:
                - radarr.tgu.ovh
      persistence:
        config:
          type: persistentVolumeClaim
          accessMode: ReadWriteOnce
          size: 2Gi
          globalMounts:
            - path: /config
        torrents:
          type: hostPath
          hostPath: /opt/media-stack/torrents
          hostPathType: DirectoryOrCreate
          globalMounts:
            - path: /data/torrents
        media:
          type: persistentVolumeClaim
          existingClaim: media-nas-pvc
          globalMounts:
            - path: /media
    ```

    Notes:
    - `tag: "4.0.17"` and `tag: "6.1.1"` are QUOTED (Helm 3 schema validation in Wave 5 will require string typing on tags).
    - Annotations are inlined verbatim, NOT via `include "arr-stack.oauth2ProxyAnnotations"` — see RESEARCH §Unknown #2 Assumption A2 (cross-alias `_helpers.tpl` include from sub-chart context is unverified; inlining is the safe path for byte-equivalence).
    - The sonarr `torrents` mount path is `/data/torrents` (NOT `/data` — qbittorrent uses `/data`, the *arr apps mount at `/data/torrents`; this is intentional, byte-equivalent to source).

    Smoke render after writing:

    ```bash
    helm lint charts/arr-stack/
    helm template arr-stack charts/arr-stack/ -f charts/arr-stack/values.yaml --namespace selfhost > /tmp/wave2-render.yaml
    grep -c 'kind: Deployment' /tmp/wave2-render.yaml         # ≥ 2 (sonarr + radarr Deployments)
    grep -c 'kind: Ingress' /tmp/wave2-render.yaml            # ≥ 2
    grep -c 'host: sonarr.tgu.ovh' /tmp/wave2-render.yaml     # exactly 2 (in ingress.spec.rules and ingress.spec.tls)
    grep -c 'host: radarr.tgu.ovh' /tmp/wave2-render.yaml     # exactly 2
    ```
  </action>
  <verify>
    <automated>
      helm lint charts/arr-stack/ && \
      grep -q '^sonarr:' charts/arr-stack/values.yaml && \
      grep -q '^radarr:' charts/arr-stack/values.yaml && \
      grep -q '# renovate: image=lscr.io/linuxserver/sonarr' charts/arr-stack/values.yaml && \
      grep -q '# renovate: image=lscr.io/linuxserver/radarr' charts/arr-stack/values.yaml && \
      [ "$(helm template arr-stack charts/arr-stack/ -f charts/arr-stack/values.yaml --namespace selfhost | grep -c 'host: sonarr.tgu.ovh')" -ge 2 ] && \
      [ "$(helm template arr-stack charts/arr-stack/ -f charts/arr-stack/values.yaml --namespace selfhost | grep -c 'host: radarr.tgu.ovh')" -ge 2 ]
    </automated>
  </verify>
  <acceptance_criteria>
    - Both top-level keys exist: `grep -c '^\(sonarr\|radarr\):$' charts/arr-stack/values.yaml` returns 2.
    - Renovate annotations present and matching repositories: `grep -c '# renovate: image=lscr.io/linuxserver/sonarr' charts/arr-stack/values.yaml` returns at least 1; same for radarr.
    - Tags are pinned (no `:latest`, no `:HEAD`): `grep -E 'tag: ["'"'"']?(latest|HEAD)' charts/arr-stack/values.yaml` returns no matches in the sonarr/radarr sections.
    - `helm lint charts/arr-stack/` exits 0.
    - Render produces Sonarr + Radarr Deployments and Ingresses: `helm template … | grep -c 'kind: Deployment'` returns at least 2 once both aliases are added; `kind: Ingress` returns at least 2.
    - `sonarr.tgu.ovh` and `radarr.tgu.ovh` hostnames each appear in the rendered Ingress (at least 2 occurrences per host — rules + tls).
    - Byte-equivalence sanity: NO YAML comments from the source survive (`grep -c 'Même hostPath' charts/arr-stack/values.yaml` returns 0; `grep -c 'NAS NFS' charts/arr-stack/values.yaml` returns 0).
  </acceptance_criteria>
  <done>
    Sonarr and Radarr aliases render correctly. The umbrella has 2 of its 10 aliases populated.
  </done>
</task>

<task type="auto">
  <name>Task 3.2: Add prowlarr + qbittorrent aliases (qbittorrent pinned to 5.2.0)</name>
  <files>charts/arr-stack/values.yaml</files>
  <read_first>
    /home/moi/projets/perso/my-kluster/argocd/argocd-apps/prowlarr-app.yaml (verbatim source — note lines 41-42 oauth2-proxy comments)
    /home/moi/projets/perso/my-kluster/argocd/argocd-apps/qbittorrent-app.yaml (verbatim source — note `tag: latest` to replace; PUID/PGID + WEBUI_PORT env, hostPath `/data` mount)
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-PATTERNS.md §"values.yaml — prowlarr alias" + §"values.yaml — qbittorrent alias"
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-RESEARCH.md §Running Image Digests (qbittorrent → 5.2.0 verified)
    .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/current-image-tags.txt (Wave 0 baseline)
  </read_first>
  <action>
    Append two more blocks to `charts/arr-stack/values.yaml` (below the radarr alias from Task 3.1).

    **prowlarr alias** — verbatim from `prowlarr-app.yaml` lines 18-67. Notes per PATTERNS.md "Translation notes":
    - Prowlarr opts OUT of oauth2-proxy. The analog source has lines 41-42 commented (`# nginx.ingress.kubernetes.io/auth-url: ...`). DO NOT preserve those comments in the umbrella — byte-equivalence means the rendered Ingress has NO oauth2-proxy annotations, so the source values block must NOT contain them at all.
    - No `torrents` or `media` persistence — only `config` PVC (1Gi).
    - cert-manager annotation IS present (Prowlarr's TLS is still cert-managed).

    ```yaml

    # ============================================================================
    # prowlarr — Indexer aggregator (NO oauth2-proxy — see prowlarr-app.yaml lines 41-42)
    # Source: my-kluster/argocd/argocd-apps/prowlarr-app.yaml helm.values block (lines 18-67)
    # ============================================================================
    prowlarr:
      controllers:
        main:
          containers:
            main:
              image:
                # renovate: image=lscr.io/linuxserver/prowlarr
                repository: lscr.io/linuxserver/prowlarr
                tag: "2.3.5"
              env:
                TZ: "Europe/Paris"
                PUID: "1000"
                PGID: "1000"
      service:
        main:
          controller: main
          ports:
            http:
              port: 9696
      ingress:
        main:
          className: nginx
          annotations:
            cert-manager.io/cluster-issuer: "letsencrypt-prod"
          hosts:
            - host: prowlarr.tgu.ovh
              paths:
                - path: /
                  pathType: Prefix
                  service:
                    identifier: main
                    port: http
          tls:
            - secretName: prowlarr-tls
              hosts:
                - prowlarr.tgu.ovh
      persistence:
        config:
          type: persistentVolumeClaim
          accessMode: ReadWriteOnce
          size: 1Gi
          globalMounts:
            - path: /config
    ```

    **qbittorrent alias** — verbatim from `qbittorrent-app.yaml` lines 18-76, with TWO mandatory deltas:
    1. Replace `tag: latest` with `tag: "5.2.0"` (RESEARCH-verified — the running digest `sha256:2e014842…` matches the linuxserver qbittorrent `5.2.0` tag exactly).
    2. Add `# renovate: image=lscr.io/linuxserver/qbittorrent` annotation.

    The hostPath mount path is `/data` (NOT `/data/torrents` — qbittorrent is the SOURCE, sonarr/radarr mount the same hostPath at `/data/torrents` to consume).

    ```yaml

    # ============================================================================
    # qbittorrent — Torrent client (pinned away from :latest per D-04-PIN-01,
    # RESEARCH-confirmed: running digest sha256:2e014842 == tag 5.2.0)
    # Source: my-kluster/argocd/argocd-apps/qbittorrent-app.yaml helm.values block (lines 18-76)
    # ============================================================================
    qbittorrent:
      controllers:
        main:
          containers:
            main:
              image:
                # renovate: image=lscr.io/linuxserver/qbittorrent
                repository: lscr.io/linuxserver/qbittorrent
                tag: "5.2.0"
              env:
                TZ: "Europe/Paris"
                PUID: "1000"
                PGID: "1000"
                WEBUI_PORT: "8080"
      service:
        main:
          controller: main
          ports:
            http:
              port: 8080
      ingress:
        main:
          className: nginx
          annotations:
            cert-manager.io/cluster-issuer: "letsencrypt-prod"
            nginx.ingress.kubernetes.io/auth-url: "https://auth.tgu.ovh/oauth2/auth"
            nginx.ingress.kubernetes.io/auth-signin: "https://auth.tgu.ovh/oauth2/start?rd=https://qbittorrent.tgu.ovh"
          hosts:
            - host: qbittorrent.tgu.ovh
              paths:
                - path: /
                  pathType: Prefix
                  service:
                    identifier: main
                    port: http
          tls:
            - secretName: qbittorrent-tls
              hosts:
                - qbittorrent.tgu.ovh
      persistence:
        config:
          type: persistentVolumeClaim
          accessMode: ReadWriteOnce
          size: 1Gi
          globalMounts:
            - path: /config
        torrents:
          type: hostPath
          hostPath: /opt/media-stack/torrents
          hostPathType: DirectoryOrCreate
          globalMounts:
            - path: /data
    ```

    Run `tools/scripts/check-renovate-annotations.sh charts/arr-stack/values.yaml` — must exit 0 against all 4 aliases (sonarr, radarr, prowlarr, qbittorrent).

    Smoke render:
    ```bash
    helm lint charts/arr-stack/
    helm template arr-stack charts/arr-stack/ -f charts/arr-stack/values.yaml --namespace selfhost > /tmp/wave2-render-4.yaml
    grep -c 'host: prowlarr.tgu.ovh' /tmp/wave2-render-4.yaml      # ≥ 2
    grep -c 'host: qbittorrent.tgu.ovh' /tmp/wave2-render-4.yaml   # ≥ 2
    # Prowlarr has NO oauth2-proxy annotations:
    awk '/^  name: prowlarr/,/^---/' /tmp/wave2-render-4.yaml | grep -c 'oauth2'  # must be 0
    # qbittorrent NOT on :latest:
    awk '/^  name: qbittorrent/,/^---/' /tmp/wave2-render-4.yaml | grep -c 'qbittorrent:latest'  # must be 0
    awk '/^  name: qbittorrent/,/^---/' /tmp/wave2-render-4.yaml | grep -c 'qbittorrent:5.2.0'   # ≥ 1
    ```
  </action>
  <verify>
    <automated>
      helm lint charts/arr-stack/ && \
      tools/scripts/check-renovate-annotations.sh charts/arr-stack/values.yaml && \
      grep -q '^prowlarr:' charts/arr-stack/values.yaml && \
      grep -q '^qbittorrent:' charts/arr-stack/values.yaml && \
      grep -q 'tag: "5.2.0"' charts/arr-stack/values.yaml && \
      ! helm template arr-stack charts/arr-stack/ -f charts/arr-stack/values.yaml --namespace selfhost | grep -q 'qbittorrent:latest' && \
      [ "$(helm template arr-stack charts/arr-stack/ -f charts/arr-stack/values.yaml --namespace selfhost | grep -c 'host: qbittorrent.tgu.ovh')" -ge 2 ]
    </automated>
  </verify>
  <acceptance_criteria>
    - All 4 top-level keys present: `grep -cE '^(sonarr|radarr|prowlarr|qbittorrent):$' charts/arr-stack/values.yaml` returns 4.
    - All 4 Renovate annotations present: `grep -c '# renovate: image=lscr.io/linuxserver/' charts/arr-stack/values.yaml` returns at least 4 (sonarr, radarr, prowlarr, qbittorrent — all lscr.io/linuxserver/*).
    - `tools/scripts/check-renovate-annotations.sh charts/arr-stack/values.yaml` exits 0.
    - qbittorrent pinned to 5.2.0: `grep -c 'tag: "5.2.0"' charts/arr-stack/values.yaml` returns at least 1.
    - No `:latest` tags survived in any of these 4 alias sections: `helm template arr-stack charts/arr-stack/ -f charts/arr-stack/values.yaml --namespace selfhost | grep -cE 'lscr.io/linuxserver/(sonarr|radarr|prowlarr|qbittorrent):latest'` returns 0.
    - Prowlarr ingress has NO oauth2-proxy: the rendered Prowlarr Ingress contains no `auth-url` or `auth-signin` annotations. Verify with the awk + grep block above.
    - Render produces all 4 hostnames: rendered output contains `host: sonarr.tgu.ovh`, `host: radarr.tgu.ovh`, `host: prowlarr.tgu.ovh`, `host: qbittorrent.tgu.ovh` (each at least twice — Ingress rules + tls).
    - `helm lint charts/arr-stack/` exits 0.
  </acceptance_criteria>
  <done>
    4 of 10 aliases populated. The remaining 6 (cleanuparr/seerr/flaresolverr/jellyfin + arrconf+configarr CronJobs) come in Plans 04 and 05. CI in Plan 06 will gate on annotation correctness for all of them via tools/scripts/check-renovate-annotations.sh.
  </done>
</task>

</tasks>

<verification>
- `helm lint charts/arr-stack/` exits 0.
- All 4 top-level keys exist in values.yaml (sonarr, radarr, prowlarr, qbittorrent).
- `tools/scripts/check-renovate-annotations.sh charts/arr-stack/values.yaml` exits 0.
- qbittorrent pinned to 5.2.0; no `:latest` in any of these 4 sections.
- Prowlarr Ingress has NO oauth2-proxy annotations.
</verification>

<success_criteria>
The 4 most-traffic media apps (Sonarr/Radarr/Prowlarr/qBittorrent) render byte-equivalent to their current unit-App outputs at this stage. Plan 04 handles the remaining 4 media apps.
</success_criteria>

<output>
After completion, create `.planning/phases/04-umbrella-chart-migration-des-9-apps/04-03-media-aliases-arr-SUMMARY.md`.
</output>
