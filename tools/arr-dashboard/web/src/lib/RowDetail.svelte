<script lang="ts">
  import type { Row, Download } from "../api";
  import { deleteDownload } from "../api";
  import ConfirmDialog from "./ConfirmDialog.svelte";
  let { row }: { row: Row } = $props();
  let confirming = $state<Download | null>(null);
  async function doDelete() {
    const d = confirming; confirming = null;
    if (d) await deleteDownload(row.key, d.infohash);
  }
</script>

<div class="detail">
  <div><strong>key</strong> {row.key} · <strong>arr</strong> {row.arr_app ?? "—"} · <strong>quality</strong> {row.quality ?? "—"} · <strong>monitored</strong> {row.monitored} · <strong>hasFile</strong> {row.has_file}</div>
  {#if row.downloads.length}
    <div><strong>downloads:</strong>
      <ul>{#each row.downloads as d}
        <li>{d.name} — {d.state} {Math.round(d.progress * 100)}% [{d.category ?? "?"}] {d.infohash}
          <button class="del" onclick={() => (confirming = d)}>Supprimer</button>
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

<style>
  .detail { font-family: "IBM Plex Mono", monospace; font-size: 0.8rem; padding: 0.5rem 1rem; color: #9ca3af; }
  ul { margin: 0.2rem 0; }
  .del { background: #b91c1c; color: #fff; border: 0; padding: .1rem .4rem; border-radius: 3px; cursor: pointer; margin-left: .4rem; font-size: .7rem; }
</style>
