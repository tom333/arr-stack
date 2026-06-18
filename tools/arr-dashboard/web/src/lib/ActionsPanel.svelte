<script lang="ts">
  import { getActions, postImport, type ActionJob } from "../api";
  let jobs = $state<ActionJob[]>([]);
  $effect(() => { const f = async () => { try { jobs = await getActions(); } catch {} }; f(); const id = setInterval(f, 3000); return () => clearInterval(id); });
  const active = $derived(jobs.filter((j) => j.state === "queued" || j.state === "running"));
  const failed = $derived(jobs.filter((j) => j.state === "failed"));
  async function retry(key: string) { try { await postImport(key); jobs = await getActions(); } catch {} }
</script>

{#if active.length || failed.length}
  <div class="panel">
    {#if active.length}<span>⏳ {active.length} import(s) en cours/file</span>{/if}
    {#each failed as j}<span class="f" title={j.message ?? ""} onclick={() => retry(j.key)}>✗ {j.title}</span>{/each}
  </div>
{/if}

<style>.panel { display: flex; gap: 1rem; padding: .4rem 1rem; background: #161a22; font-size: .85rem; } .f { color: #f87171; cursor: pointer; }</style>
