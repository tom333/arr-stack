# Phase 30 — cross-seed Operator Runbook

**Purpose:** Documents the manual cluster prerequisites (PVC, host directory, secret keys) and
out-of-stack teardown steps required to consolidate the existing cross-seed instance into the
arr-stack umbrella Helm chart.

> arr-stack does NOT automate any of these steps. Deployment is always via my-kluster + ArgoCD.
> Never run `helm install` or `kubectl apply` directly from this repo (CLAUDE.md deployer boundary).

---

## Pre-reqs BEFORE ArgoCD sync (my-kluster side)

Complete ALL of the following before merging the arr-stack PR or triggering an ArgoCD sync.

### 1. Verify `arrconf-env` SealedSecret carries the required keys

The cross-seed initContainer and main container both mount `arrconf-env` via `envFrom`.
The following keys must exist in the SealedSecret:

| Key | Used by |
|-----|---------|
| `PROWLARR_API_KEY` | initContainer token substitution in `torznab` URL |
| `QBT_USER` | initContainer token substitution in `torrentClients` URL |
| `QBT_PASS` | initContainer token substitution in `torrentClients` URL |

**How to verify:**

```bash
# Decode the SealedSecret to inspect key names (values remain encrypted)
kubectl -n selfhost get secret arrconf-env -o jsonpath='{.data}' | python3 -c "
import json, sys
data = json.load(sys.stdin)
print('Keys present:', list(data.keys()))
"
```

If any key is missing, add it in a separate my-kluster SealedSecret PR and merge it BEFORE
the arr-stack PR (SuggestArr D-02 precedent: secret-first, then app). Do NOT merge the
arr-stack cross-seed PR until all three keys are confirmed present.

### 2. Create the `cross-seed-config` PVC in the `selfhost` namespace

The cross-seed alias mounts an `existingClaim: cross-seed-config` at `/config` (for the
SQLite DB, torrent_cache, and logs). This PVC must exist before the first ArgoCD sync —
if it is absent, the pod will stay Pending.

```bash
kubectl apply -n selfhost -f - <<'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: cross-seed-config
  namespace: selfhost
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
EOF
```

Adjust the storage class if your cluster requires a specific one:

```bash
# List available storage classes
kubectl get storageclass
# Add storageClassName: <name> under spec: if needed
```

### 3. Create the host directory for cross-seed hardlinks

The `linkDirs` config (`/data/torrents/cross-seed`) maps to the hostPath mount
`/media/data/torrents` → `/data`. The directory `/media/data/torrents/cross-seed` must
exist on the MicroK8s node BEFORE cross-seed tries to write hardlinks.

```bash
# Run on the MicroK8s node (SSH or direct access)
mkdir -p /media/data/torrents/cross-seed
```

Failure to create this directory will not prevent the pod from starting, but cross-seed will
log errors and fail to create hardlinks when it finds a match.

---

## Verify the consolidated deployment (post-sync)

After ArgoCD syncs and the cross-seed pod starts, verify the following (Success Criterion 2):

### 4. Pod reaches Running state

```bash
kubectl -n selfhost get pod -l app.kubernetes.io/name=cross-seed
# Expected: STATUS=Running, READY=1/1
# The initContainer (config-init) must have completed before the main container starts.
```

Check initContainer logs if the pod does not reach Running:

```bash
kubectl -n selfhost logs deploy/cross-seed -c config-init
# Expected: no output (the node -e inline script writes the file silently)
# If the script fails, you will see a Node.js error here.
```

### 5. cross-seed authenticates to Prowlarr torznab — no auth error

```bash
kubectl -n selfhost logs deploy/cross-seed
# Look for lines indicating torznab connection success.
# A successful startup shows cross-seed indexing or "waiting for requests".
# An auth error shows "401 Unauthorized" or "invalid apikey" — indicates
# PROWLARR_API_KEY was not resolved (check arrconf-env secret + initContainer logs).
```

### 6. Confirm no unresolved tokens in the resolved config.js (optional)

The initContainer writes the resolved config.js to the ephemeral emptyDir. The main
container reads it from there. To verify no `${...}` tokens remain unresolved:

```bash
kubectl -n selfhost exec deploy/cross-seed -- cat /config/config.js
# Verify the file contains real values (IP addresses, no dollar-brace tokens).
# IMPORTANT: this command prints the resolved secrets (API key, qBit password) to your
# terminal. Do not paste the output into any log or ticket.
```

If tokens remain unresolved, the initContainer likely failed to read the env vars. Check
that `arrconf-env` is mounted correctly and all three keys are present.

---

## Out-of-stack teardown (after consolidated instance verified)

### 7. Optionally preserve search history (config.db migration)

cross-seed stores its SQLite DB at `/config/config.db`. This DB records which torrents have
already been cross-seeded, preventing duplicate injection. If you want to preserve this
history (recommended — avoids re-scanning all torrents):

```bash
# On the MicroK8s node: find the old config.db path (e.g. Docker volume or bind mount)
# Then copy it into the new PVC via kubectl cp
kubectl -n selfhost cp /path/to/old/config.db cross-seed-<pod-id>:/config/config.db
```

This step is optional. If skipped, cross-seed will re-scan all torrents on first run.
The only consequence is extra tracker requests on the first scan — no data loss.

### 8. Stop the old out-of-stack cross-seed instance

Once the consolidated in-cluster instance is verified as healthy (step 4 + 5):

```bash
# If running as a Docker container
docker stop cross-seed

# If running via docker-compose
docker-compose down cross-seed

# If running as a systemd service
sudo systemctl stop cross-seed
sudo systemctl disable cross-seed
```

This is an operator action — arr-stack does NOT automate host-level teardown (ADR-10
deployer boundary; never deploy/teardown from this repo).

---

## Rollback

If the consolidated instance misbehaves (auth failures, pod crashloop, unexpected behavior):

1. **Scale down the in-cluster instance:**

   ```bash
   kubectl -n selfhost scale deployment cross-seed --replicas=0
   ```

2. **Restart the old out-of-stack instance** (reverse of step 8 above):

   ```bash
   docker start cross-seed
   # or
   docker-compose up -d cross-seed
   ```

3. **Investigate** via `kubectl -n selfhost logs deploy/cross-seed` and `kubectl describe pod`.

4. **No data loss:** The new PVC is dedicated to cross-seed and is not touched by the old
   instance (different mount points). The old config.db from the host is untouched unless
   you explicitly copied it in step 7.

5. After fixing the root cause, scale the deployment back to 1 to re-attempt:

   ```bash
   kubectl -n selfhost scale deployment cross-seed --replicas=1
   ```
