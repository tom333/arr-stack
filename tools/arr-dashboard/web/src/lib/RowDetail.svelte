<script lang="ts">
  import type { Row } from "../api";
  let { row }: { row: Row } = $props();
</script>

<div class="detail">
  <div><strong>key</strong> {row.key} · <strong>arr</strong> {row.arr_app ?? "—"} · <strong>quality</strong> {row.quality ?? "—"} · <strong>monitored</strong> {row.monitored} · <strong>hasFile</strong> {row.has_file}</div>
  {#if row.downloads.length}
    <div><strong>downloads:</strong>
      <ul>{#each row.downloads as d}<li>{d.name} — {d.state} {Math.round(d.progress * 100)}% [{d.category ?? "?"}] {d.infohash}</li>{/each}</ul>
    </div>
  {/if}
  {#if row.disk_paths.length}<div><strong>disque:</strong> {row.disk_paths.join(", ")}</div>{/if}
</div>

<style>.detail { font-family: "IBM Plex Mono", monospace; font-size: 0.8rem; padding: 0.5rem 1rem; color: #9ca3af; } ul { margin: 0.2rem 0; }</style>
