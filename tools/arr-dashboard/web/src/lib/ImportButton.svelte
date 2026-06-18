<script lang="ts">
  import type { Row } from "../api";
  import ConfirmDialog from "./ConfirmDialog.svelte";
  import { postImport } from "../api";
  let { row, pending }: { row: Row; pending: boolean } = $props();
  let open = $state(false);
  const size = $derived(row.downloads[0]?.size);
  const sizeGB = $derived(size ? (size / 1e9).toFixed(2) : "?");
  async function confirm() { open = false; await postImport(row.key); }
</script>

{#if pending}
  <span class="badge">import…</span>
{:else}
  <button onclick={() => (open = true)}>Importer</button>
{/if}
{#if open}
  <ConfirmDialog title={`Importer ${row.title}`} detail={`${row.downloads[0]?.name ?? ""} — ${sizeGB} GB`}
    onConfirm={confirm} onCancel={() => (open = false)} />
{/if}

<style>.badge { color: #60a5fa; } button { background: #2563eb; color: #fff; border: 0; padding: .25rem .6rem; border-radius: 4px; cursor: pointer; }</style>
