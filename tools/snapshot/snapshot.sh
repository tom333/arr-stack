#!/usr/bin/env bash
# arr-stack snapshot.sh — read-only baseline capture for 6 apps.
# See tools/snapshot/README.md for prerequisites (port-forwards, env vars).
# ADR-6 niveau 1 : Bash standalone, indépendant d'arrconf (qui arrive Phase 1).

set -euo pipefail
IFS=$'\n\t'

# ─── Globals ────────────────────────────────────────────────────────────────

readonly SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
readonly DEFAULT_DATE="2026-05-07"  # baseline date (verrouillée Phase 0)
readonly KNOWN_APPS=(sonarr radarr prowlarr qbittorrent seerr jellyfin)

# Workspace temp (cookies qBittorrent + tampons curl)
WORK_DIR=""
trap 'cleanup' EXIT INT TERM

cleanup() {
  if [[ -n "${WORK_DIR}" && -d "${WORK_DIR}" ]]; then
    rm -rf "${WORK_DIR}"
  fi
}

# ─── Refus root ─────────────────────────────────────────────────────────────

if [[ ${EUID} -eq 0 ]]; then
  echo "ERROR: do not run ${SCRIPT_NAME} as root" >&2
  exit 2
fi

# ─── Args parsing ───────────────────────────────────────────────────────────

usage() {
  cat <<EOF
Usage: ${SCRIPT_NAME} [options]

Capture un snapshot raw read-only des 6 apps arr-stack (sonarr, radarr, prowlarr,
qbittorrent, seerr, jellyfin) via leurs APIs REST.

Options:
  --apps APP1,APP2     Liste des apps à snapshotter (default: toutes les 6)
  --output PATH        Dossier output (default: snapshots/baseline-${DEFAULT_DATE})
  --dry-run            Liste les GET sans écrire les fichiers
  -h, --help           Affiche cette aide

Prérequis (voir tools/snapshot/README.md):
  - kubectl port-forward actif vers chaque service selfhost
  - Env vars : SONARR_API_KEY, RADARR_API_KEY, PROWLARR_API_KEY,
              QBT_USER, QBT_PASS, SEERR_API_KEY, JELLYFIN_API_KEY

Exit codes: 0 = succès (≥1 app OK), 1 = toutes les apps ont fail, 2 = erreur args
EOF
}

TARGET_APPS=("${KNOWN_APPS[@]}")
OUTPUT_DIR=""
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apps)
      IFS=',' read -ra TARGET_APPS <<< "$2"
      # Validation whitelist (anti command injection — ASVS V5)
      for app in "${TARGET_APPS[@]}"; do
        case "$app" in
          sonarr|radarr|prowlarr|qbittorrent|seerr|jellyfin) ;;
          *) echo "ERROR: unknown app '$app' (allowed: ${KNOWN_APPS[*]})" >&2; exit 2 ;;
        esac
      done
      shift 2 ;;
    --output)
      OUTPUT_DIR="$2"
      # Anti path-traversal : refuser '..' (ASVS V5)
      if [[ "$OUTPUT_DIR" == *..* ]]; then
        echo "ERROR: '..' not allowed in --output path" >&2; exit 2
      fi
      shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown flag '$1'" >&2; usage >&2; exit 2 ;;
  esac
done

OUTPUT_DIR="${OUTPUT_DIR:-${REPO_ROOT}/snapshots/baseline-${DEFAULT_DATE}}"

# ─── Working dir ────────────────────────────────────────────────────────────

WORK_DIR="$(mktemp -d -t arr-snapshot.XXXXXX)"

# ─── URL defaults ───────────────────────────────────────────────────────────

SONARR_URL="${SONARR_URL:-http://localhost:8989}"
RADARR_URL="${RADARR_URL:-http://localhost:7878}"
PROWLARR_URL="${PROWLARR_URL:-http://localhost:9696}"
QBT_URL="${QBT_URL:-http://localhost:8080}"
SEERR_URL="${SEERR_URL:-http://localhost:5055}"
JELLYFIN_URL="${JELLYFIN_URL:-http://localhost:8096}"

# Jellyfin auth — 10.11+ default, X-Emby-Token override possible via env
JELLYFIN_AUTH_HEADER="${JELLYFIN_AUTH_HEADER:-Authorization: MediaBrowser Token=\"${JELLYFIN_API_KEY:-}\"}"

# ─── Logging helpers ────────────────────────────────────────────────────────

log()  { echo "[$(date +%H:%M:%S)] $*"; }
warn() { echo "[$(date +%H:%M:%S)] WARN: $*" >&2; }
err()  { echo "[$(date +%H:%M:%S)] ERROR: $*" >&2; }

# ─── Core helper : snapshot_get ─────────────────────────────────────────────
#
# Usage: snapshot_get <app> <full_url> <auth_header_or_-> <output_file_relative_to_app_dir> [extra curl args...]
# Returns 0 si OK, 1 si fail (HTTP != 200 ou JSON invalide).

snapshot_get() {
  local app="$1" url="$2" auth="$3" out_rel="$4"; shift 4
  local extra_args=("$@")
  local out_dir="${OUTPUT_DIR}/${app}"
  local out_file="${out_dir}/${out_rel}"

  if (( DRY_RUN )); then
    log "  [dry-run] ${app} GET ${url} → ${out_rel}"
    return 0
  fi

  mkdir -p "$out_dir"

  local curl_args=(
    --silent --show-error
    --max-time 30
    --retry 2 --retry-delay 1
    -H "Accept: application/json"
    -w "%{http_code}"
    -o "${WORK_DIR}/raw"
  )
  if [[ "$auth" != "-" ]]; then
    curl_args+=(-H "$auth")
  fi
  curl_args+=("${extra_args[@]}" "$url")

  local http_code
  http_code=$(curl "${curl_args[@]}" || echo "000")

  if [[ "$http_code" != "200" ]]; then
    warn "  ✗ ${app} ${out_rel} → HTTP ${http_code}"
    return 1
  fi

  # JSON ? sort-keys + write. Sinon (qBit text endpoints) : write raw.
  if [[ "$out_rel" == *.json ]]; then
    if jq --sort-keys '.' "${WORK_DIR}/raw" > "$out_file" 2>/dev/null; then
      log "  ✓ ${app} ${out_rel}"
      return 0
    else
      warn "  ✗ ${app} ${out_rel} → invalid JSON, fallback raw"
      cp "${WORK_DIR}/raw" "${out_file%.json}.raw"
      return 1
    fi
  else
    cp "${WORK_DIR}/raw" "$out_file"
    log "  ✓ ${app} ${out_rel}"
    return 0
  fi
}

# ─── Per-app snapshotters ───────────────────────────────────────────────────

snapshot_arr_app() {
  local app="$1" base_url="$2" api_key="$3" api_version="$4"
  local auth="X-Api-Key: ${api_key}"
  local v="$api_version"
  local local_failures=0

  local endpoints=(
    "/api/${v}/downloadclient:downloadclient.json"
    "/api/${v}/indexer:indexer.json"
    "/api/${v}/notification:notification.json"
    "/api/${v}/rootfolder:rootfolder.json"
    "/api/${v}/tag:tag.json"
    "/api/${v}/qualityprofile:qualityprofile.json"
    "/api/${v}/customformat:customformat.json"
    "/api/${v}/config/host:config_host.json"
    "/api/${v}/config/naming:config_naming.json"
    "/api/${v}/config/mediamanagement:config_mediamanagement.json"
    "/api/${v}/config/ui:config_ui.json"
    "/api/${v}/config/indexer:config_indexer.json"
    "/api/${v}/config/downloadclient:config_downloadclient.json"
    "/api/${v}/importlist:importlist.json"
    "/api/${v}/remotepathmapping:remotepathmapping.json"
    "/api/${v}/metadata:metadata.json"
    "/api/${v}/system/status:system_status.json"
  )
  if [[ "$app" == "radarr" ]]; then
    endpoints+=("/api/${v}/config/metadata:config_metadata.json")
  fi

  log "▶ ${app} (${base_url})"
  for entry in "${endpoints[@]}"; do
    local endpoint="${entry%%:*}"
    local filename="${entry##*:}"
    snapshot_get "$app" "${base_url}${endpoint}" "$auth" "$filename" || local_failures=$((local_failures + 1))
  done

  if (( local_failures > 0 )); then
    warn "${app} : ${local_failures} endpoint(s) failed"
    return 1
  fi
  return 0
}

snapshot_prowlarr() {
  local base_url="$1" api_key="$2"
  local auth="X-Api-Key: ${api_key}"
  local local_failures=0

  local endpoints=(
    "/api/v1/indexer:indexer.json"
    "/api/v1/indexer/categories:indexer_categories.json"
    "/api/v1/indexerstats:indexerstats.json"
    "/api/v1/indexerstatus:indexerstatus.json"
    "/api/v1/indexerproxy:indexerproxy.json"
    "/api/v1/applications:applications.json"
    "/api/v1/appprofile:appprofile.json"
    "/api/v1/downloadclient:downloadclient.json"
    "/api/v1/notification:notification.json"
    "/api/v1/tag:tag.json"
    "/api/v1/config/host:config_host.json"
    "/api/v1/config/ui:config_ui.json"
    "/api/v1/config/downloadclient:config_downloadclient.json"
    "/api/v1/system/status:system_status.json"
  )

  log "▶ prowlarr (${base_url})"
  for entry in "${endpoints[@]}"; do
    local endpoint="${entry%%:*}"
    local filename="${entry##*:}"
    snapshot_get "prowlarr" "${base_url}${endpoint}" "$auth" "$filename" || local_failures=$((local_failures + 1))
  done

  (( local_failures > 0 )) && { warn "prowlarr : ${local_failures} endpoint(s) failed"; return 1; }
  return 0
}

snapshot_qbittorrent() {
  local base_url="$1" user="$2" pass="$3"
  local cookie_jar="${WORK_DIR}/qbt.cookies"
  local local_failures=0

  log "▶ qbittorrent (${base_url})"

  # Login to auth endpoint only — read-from-server, not a write to torrents.
  # curl sends a POST body automatically via --data-urlencode (no explicit method flag needed).
  if (( ! DRY_RUN )); then
    local http_code
    http_code=$(curl --silent --show-error \
      --cookie-jar "$cookie_jar" \
      -H "Referer: ${base_url}" \
      --data-urlencode "username=${user}" \
      --data-urlencode "password=${pass}" \
      -w "%{http_code}" \
      -o /dev/null \
      "${base_url}/api/v2/auth/login" || echo "000")

    if [[ "$http_code" != "200" && "$http_code" != "204" ]]; then
      warn "qbittorrent : login failed (HTTP ${http_code}) — vérifier QBT_USER/PASS et port-forward"
      return 1
    fi
  fi

  local json_endpoints=(
    "/api/v2/app/buildInfo:app_buildinfo.json"
    "/api/v2/app/preferences:app_preferences.json"
    "/api/v2/torrents/categories:torrents_categories.json"
    "/api/v2/torrents/tags:torrents_tags.json"
    "/api/v2/torrents/info:torrents_info.json"
    "/api/v2/transfer/info:transfer_info.json"
  )
  local text_endpoints=(
    "/api/v2/app/version:app_version.txt"
    "/api/v2/app/webapiVersion:app_webapi_version.txt"
    "/api/v2/app/defaultSavePath:app_default_save_path.txt"
  )

  for entry in "${json_endpoints[@]}" "${text_endpoints[@]}"; do
    local endpoint="${entry%%:*}"
    local filename="${entry##*:}"
    snapshot_get "qbittorrent" "${base_url}${endpoint}" "-" "$filename" --cookie "$cookie_jar" \
      || local_failures=$((local_failures + 1))
  done

  (( local_failures > 0 )) && { warn "qbittorrent : ${local_failures} endpoint(s) failed"; return 1; }
  return 0
}

snapshot_seerr() {
  local base_url="$1" api_key="$2"
  local auth="X-Api-Key: ${api_key}"
  local local_failures=0

  local endpoints=(
    "/api/v1/settings/main:settings_main.json"
    "/api/v1/settings/network:settings_network.json"
    "/api/v1/settings/public:settings_public.json"
    "/api/v1/settings/sonarr:settings_sonarr.json"
    "/api/v1/settings/radarr:settings_radarr.json"
    "/api/v1/settings/jellyfin:settings_jellyfin.json"
    "/api/v1/settings/plex:settings_plex.json"
    "/api/v1/settings/notifications/email:settings_notifications_email.json"
    "/api/v1/settings/notifications/discord:settings_notifications_discord.json"
    "/api/v1/settings/notifications/telegram:settings_notifications_telegram.json"
    "/api/v1/settings/notifications/webhook:settings_notifications_webhook.json"
    "/api/v1/settings/jobs:settings_jobs.json"
    "/api/v1/user:user.json"
    "/api/v1/request:request.json"
    "/api/v1/request/count:request_count.json"
    "/api/v1/status:status.json"
  )

  log "▶ seerr (${base_url})"
  for entry in "${endpoints[@]}"; do
    local endpoint="${entry%%:*}"
    local filename="${entry##*:}"
    snapshot_get "seerr" "${base_url}${endpoint}" "$auth" "$filename" || local_failures=$((local_failures + 1))
  done

  (( local_failures > 0 )) && { warn "seerr : ${local_failures} endpoint(s) failed (Q1 compat — non-bloquant Phase 0)"; return 1; }
  return 0
}

snapshot_jellyfin() {
  local base_url="$1" auth_header="$2"
  local local_failures=0

  local endpoints=(
    "/System/Info:system_info.json"
    "/System/Info/Public:system_info_public.json"
    "/System/Configuration:system_configuration.json"
    "/System/Info/Storage:system_storage.json"
    "/Library/VirtualFolders:library_virtualfolders.json"
    "/System/Configuration/MetadataOptions/Default:metadata_options_default.json"
    "/Users:users.json"
    "/Plugins:plugins.json"
    "/Devices:devices.json"
    "/ScheduledTasks:scheduled_tasks.json"
  )

  log "▶ jellyfin (${base_url})"
  for entry in "${endpoints[@]}"; do
    local endpoint="${entry%%:*}"
    local filename="${entry##*:}"
    snapshot_get "jellyfin" "${base_url}${endpoint}" "$auth_header" "$filename" || local_failures=$((local_failures + 1))
  done

  if (( local_failures > 0 )); then
    warn "jellyfin : ${local_failures} endpoint(s) failed (admin bootstrap requis ? — voir tools/snapshot/README.md)"
    return 1
  fi
  return 0
}

# ─── Main loop ──────────────────────────────────────────────────────────────

log "snapshot.sh start — output: ${OUTPUT_DIR} (dry-run=${DRY_RUN})"
log "target apps: ${TARGET_APPS[*]}"

declare -i FAILED_APPS=0
declare -i TOTAL_APPS=${#TARGET_APPS[@]}

for app in "${TARGET_APPS[@]}"; do
  case "$app" in
    sonarr)
      : "${SONARR_API_KEY:?SONARR_API_KEY env var is required (see tools/snapshot/README.md)}"
      snapshot_arr_app "sonarr" "$SONARR_URL" "$SONARR_API_KEY" "v3" || FAILED_APPS=$((FAILED_APPS + 1)) ;;
    radarr)
      : "${RADARR_API_KEY:?RADARR_API_KEY env var is required}"
      snapshot_arr_app "radarr" "$RADARR_URL" "$RADARR_API_KEY" "v3" || FAILED_APPS=$((FAILED_APPS + 1)) ;;
    prowlarr)
      : "${PROWLARR_API_KEY:?PROWLARR_API_KEY env var is required}"
      snapshot_prowlarr "$PROWLARR_URL" "$PROWLARR_API_KEY" || FAILED_APPS=$((FAILED_APPS + 1)) ;;
    qbittorrent)
      : "${QBT_USER:?QBT_USER env var is required}"
      : "${QBT_PASS:?QBT_PASS env var is required}"
      snapshot_qbittorrent "$QBT_URL" "$QBT_USER" "$QBT_PASS" || FAILED_APPS=$((FAILED_APPS + 1)) ;;
    seerr)
      : "${SEERR_API_KEY:?SEERR_API_KEY env var is required}"
      snapshot_seerr "$SEERR_URL" "$SEERR_API_KEY" || FAILED_APPS=$((FAILED_APPS + 1)) ;;
    jellyfin)
      : "${JELLYFIN_API_KEY:?JELLYFIN_API_KEY env var is required}"
      snapshot_jellyfin "$JELLYFIN_URL" "$JELLYFIN_AUTH_HEADER" || FAILED_APPS=$((FAILED_APPS + 1)) ;;
  esac
done

# ─── REQ-snapshot-redaction-harden ─────────────────────────────────────────
# Inline jq redaction: overwrite all *.json in OUTPUT_DIR with secrets blanked.
# Skipped in dry-run (no files written). Uses mv -f to avoid interactive prompts
# (Phase 10 lesson: bare mv alias prompts on overwrite → silent redaction failure).

if (( ! DRY_RUN )); then
  JQ_REDACT='walk(if type == "object" then with_entries(
    if (.key | test("(?i)apiKey|password|token|webhookUrl|sessionKey"))
       and .value != null and .value != ""
    then .value = "<redacted>"
    else . end) else . end)'

  shopt -s nullglob
  for f in "${OUTPUT_DIR}"/*/*.json; do
    if jq --sort-keys "$JQ_REDACT" "$f" > "${f}.tmp" 2>/dev/null; then
      mv -f "${f}.tmp" "$f"
    else
      rm -f "${f}.tmp"
      warn "  ✗ redaction skipped (invalid JSON?): $f"
    fi
  done
  shopt -u nullglob
  log "  ✓ redaction applied (apiKey/password/token/webhookUrl/sessionKey → <redacted>)"
fi

# ─── Final report ───────────────────────────────────────────────────────────

if (( FAILED_APPS == TOTAL_APPS )); then
  err "all ${TOTAL_APPS} app(s) failed entirely"
  exit 1
fi

local_ok=$((TOTAL_APPS - FAILED_APPS))
log "snapshot complete : ${local_ok}/${TOTAL_APPS} app(s) OK, ${FAILED_APPS} with warnings"
log "output: ${OUTPUT_DIR}"
log ""
log "next: secrets auto-redacted (see tools/snapshot/README.md § 'Audit anti-leak') — verify before commit"
exit 0
