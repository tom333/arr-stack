<script lang="ts">
  import type { Row, Download } from "../api";
  import { deleteDownload, reannounce, recheck } from "../api";
  import ConfirmDialog from "./ConfirmDialog.svelte";
  let { row }: { row: Row } = $props();
  let confirming = $state<Download | null>(null);
  async function doDelete() {
    const d = confirming; confirming = null;
    if (d) await deleteDownload(row.key, d.infohash);
  }
  let rechecking = $state<Download | null>(null);
  async function doRecheck() {
    const d = rechecking; rechecking = null;
    if (d) await recheck(row.key, d.infohash);
  }
  const fmtSpeed = (b: number | null) => (b == null ? "—" : b === 0 ? "0 B/s" : `${(b / 1e6).toFixed(2)} MB/s`);
  const fmtEta = (s: number | null) => (s == null || s >= 8640000 ? "∞" : s < 3600 ? `${Math.round(s / 60)} min` : `${(s / 3600).toFixed(1)} h`);
  const fmtAge = (epoch: number | null) => {
    if (!epoch) return "—";
    const h = (Date.now() / 1000 - epoch) / 3600;
    return h < 24 ? `${Math.round(h)}h` : `${Math.round(h / 24)}j`;
  };
</script>

<div class="detail">
  <div><strong>key</strong> {row.key} · <strong>arr</strong> {row.arr_app ?? "—"} · <strong>quality</strong> {row.quality ?? "—"} · <strong>monitored</strong> {row.monitored} · <strong>hasFile</strong> {row.has_file}</div>
  {#if row.downloads.length}
    <div><strong>downloads:</strong>
      <ul>{#each row.downloads as d}
        <li>{d.name} — {d.state} {Math.round(d.progress * 100)}% [{d.category ?? "?"}] {d.infohash}
          <button class="del" onclick={() => (confirming = d)}>Supprimer</button>
          <button class="act2" onclick={() => reannounce(row.key, d.infohash)}>Re-announce</button>
          <button class="act2" onclick={() => (rechecking = d)}>Re-check</button>
          {#if d.diagnosis?.cause === "tracker-refused"}<span class="hint">ne débloque qu'après remontée du ratio</span>{/if}
          {#if d.dl_speed != null}
            <div class="stats">
              {fmtSpeed(d.dl_speed)} · seeds {d.num_complete ?? "?"} / peers {d.num_leechs ?? "?"}
              · ETA {fmtEta(d.eta)} · ratio {d.ratio?.toFixed(2) ?? "?"} · âge {fmtAge(d.added_on)}
              {#if d.tracker_status != null}
                <br />tracker: {d.tracker_status === 4 ? "ne répond pas" : "ok"}
                {#if d.tracker_msg}· "{d.tracker_msg}"{/if}{#if d.tracker_host} · {d.tracker_host}{/if}
              {/if}
            </div>
          {/if}
        </li>{/each}</ul>
    </div>
  {/if}
  {#if row.disk_paths.length}<div><strong>disque:</strong> {row.disk_paths.join(", ")}</div>{/if}
</div>

{#if confirming}
  <ConfirmDialog title={`Supprimer ce torrent`} detail={`${confirming.name} — ${confirming.infohash}`}
    warn="⚠ supprime le torrent ET ses fichiers sur le disque"
    onConfirm={doDelete} onCancel={() => (confirming = null)} />
{/if}

{#if rechecking}
  <ConfirmDialog title={`Re-check ce torrent`} detail={`${rechecking.name} — ${rechecking.infohash}`}
    warn="⚠ re-vérifie les pièces — relit les données depuis le NAS"
    onConfirm={doRecheck} onCancel={() => (rechecking = null)} />
{/if}

<style>
  .detail { font-family: "IBM Plex Mono", monospace; font-size: 0.8rem; padding: 0.5rem 1rem; color: #9ca3af; }
  ul { margin: 0.2rem 0; }
  .del { background: #b91c1c; color: #fff; border: 0; padding: .1rem .4rem; border-radius: 3px; cursor: pointer; margin-left: .4rem; font-size: .7rem; }
  .stats { color: #6b7280; font-size: .72rem; margin: .1rem 0 .3rem .4rem; }
  .act2 { background: #374151; color: #e5e7eb; border: 0; padding: .1rem .4rem; border-radius: 3px; cursor: pointer; margin-left: .3rem; font-size: .7rem; }
  .hint { color: #fbbf24; font-size: .68rem; margin-left: .4rem; }
</style>
