<script lang="ts">
  import type { ChainHealth } from "../api";
  let { chain, flags }: { chain: ChainHealth; flags: string[] } = $props();
  const steps = $derived([
    { on: chain.requested, label: "demandé" },
    { on: chain.grabbed, label: "grab" },
    { on: chain.downloaded, label: "download" },
    { on: chain.imported, label: "importé" },
    { on: chain.in_jellyfin, label: "jellyfin" },
  ]);
  const broken = $derived(flags.length > 0 && !flags.includes("ok"));
</script>

<span class="chain" class:broken>
  {#each steps as s}
    <span class="dot" class:on={s.on} title={s.label}>{s.on ? "✓" : "○"}</span>
  {/each}
</span>

<style>
  .chain { font-family: "IBM Plex Mono", monospace; letter-spacing: 1px; }
  .dot { opacity: 0.4; }
  .dot.on { opacity: 1; color: #4ade80; }
  .broken .dot:not(.on) { color: #f87171; opacity: 0.9; }
</style>
