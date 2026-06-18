<script lang="ts">
  import { getActions, postImport, type ActionJob } from "../api";

  const NAS_MBPS = 3; // measured NAS write throughput; ETA = size / NAS_MBPS

  let jobs = $state<ActionJob[]>([]);
  let now = $state(Date.now());
  $effect(() => { const f = async () => { try { jobs = await getActions(); } catch {} }; f(); const id = setInterval(f, 3000); return () => clearInterval(id); });
  $effect(() => { const id = setInterval(() => (now = Date.now()), 1000); return () => clearInterval(id); });

  const active = $derived(jobs.filter((j) => j.state === "queued" || j.state === "running"));
  const failed = $derived(jobs.filter((j) => j.state === "failed"));

  function pct(j: ActionJob): number | null {
    if (j.state !== "running" || !j.started_at || !j.size_bytes) return null;
    const estSec = j.size_bytes / (NAS_MBPS * 1e6);
    const elapsed = (now - Date.parse(j.started_at)) / 1000;
    return Math.min(99, Math.max(1, (elapsed / estSec) * 100));
  }
  function remaining(j: ActionJob): string {
    if (!j.started_at || !j.size_bytes) return "";
    const estSec = j.size_bytes / (NAS_MBPS * 1e6);
    const left = Math.max(0, estSec - (now - Date.parse(j.started_at)) / 1000);
    return `~${Math.ceil(left / 60)} min`;
  }
  async function retry(key: string) { try { await postImport(key); jobs = await getActions(); } catch {} }
</script>

{#if active.length || failed.length}
  <div class="panel">
    {#each active as j (j.key)}
      <div class="job">
        <span class="t">{j.state === "running" ? "⏳" : "•"} {j.title}</span>
        {#if pct(j) !== null}
          <span class="bar"><span class="fill" style="width:{pct(j)}%"></span></span>
          <span class="eta">{Math.round(pct(j) ?? 0)}% · {remaining(j)}</span>
        {:else}
          <span class="eta">{j.state === "running" ? "import…" : "en file"}</span>
        {/if}
      </div>
    {/each}
    {#each failed as j (j.key)}
      <span class="f" title={j.message ?? ""} onclick={() => retry(j.key)}>✗ {j.title} (réessayer)</span>
    {/each}
  </div>
{/if}

<style>
  .panel { display: flex; flex-direction: column; gap: .35rem; padding: .5rem 1rem; background: #161a22; font-size: .85rem; }
  .job { display: flex; align-items: center; gap: .6rem; }
  .t { min-width: 16rem; }
  .bar { flex: 1; max-width: 14rem; height: 8px; background: #0f1115; border-radius: 4px; overflow: hidden; }
  .fill { display: block; height: 100%; background: #4ade80; transition: width 1s linear; }
  .eta { color: #9ca3af; font-family: "IBM Plex Mono", monospace; min-width: 8rem; }
  .f { color: #f87171; cursor: pointer; }
</style>
