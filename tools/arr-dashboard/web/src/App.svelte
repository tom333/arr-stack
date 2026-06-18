<script lang="ts">
  import { getDashboard, getActions, type Snapshot, type Row } from "./api";
  import ChainPastilles from "./lib/ChainPastilles.svelte";
  import RowDetail from "./lib/RowDetail.svelte";
  import ImportButton from "./lib/ImportButton.svelte";
  import ActionsPanel from "./lib/ActionsPanel.svelte";

  let snap = $state<Snapshot | null>(null);
  let error = $state<string | null>(null);
  let problemsOnly = $state(true);
  let expanded = $state<string | null>(null);
  let activeKeys = $state<Set<string>>(new Set());

  async function refresh() {
    try { snap = await getDashboard(); error = null; }
    catch (e) { error = String(e); }
  }
  $effect(() => { refresh(); const id = setInterval(refresh, 30000); return () => clearInterval(id); });
  $effect(() => {
    const f = async () => { try { const j = await getActions(); activeKeys = new Set(j.filter((x) => x.state === "queued" || x.state === "running").map((x) => x.key)); } catch {} };
    f(); const id = setInterval(f, 3000); return () => clearInterval(id);
  });

  const visible = $derived(
    !snap ? [] : snap.rows.filter((r: Row) => !problemsOnly || !(r.flags.length === 1 && r.flags[0] === "ok")));
  const importable = (r: Row) => r.flags.includes("non-importe") || r.flags.includes("deja-possede-regrab");
</script>

<header>
  <h1>arr-dashboard</h1>
  <label><input type="checkbox" bind:checked={problemsOnly} /> Problèmes seulement</label>
  {#if snap?.stale_sources?.length}<span class="stale">⚠ sources indisponibles: {snap.stale_sources.join(", ")}</span>{/if}
</header>

<ActionsPanel />

{#if error}<p class="err">{error}</p>{/if}
{#if snap?.initializing}<p>Initialisation…</p>{/if}

<table>
  <thead><tr><th>Chaîne</th><th>Titre</th><th>Demandé</th><th>Download</th><th>Disque</th><th>Jellyfin</th><th>Flags</th><th>Action</th></tr></thead>
  <tbody>
    {#each visible as row (row.key)}
      <tr onclick={() => expanded = expanded === row.key ? null : row.key}>
        <td><ChainPastilles chain={row.chain} flags={row.flags} /></td>
        <td>{row.title}{#if row.year} ({row.year}){/if}</td>
        <td>{row.requested_by ?? "—"}</td>
        <td>{#if row.downloads.length}{row.downloads.length > 1 ? `${row.downloads.length} torrents` : `${Math.round(row.downloads[0].progress * 100)}% ${row.downloads[0].tracker ?? ""}`}{:else}—{/if}</td>
        <td>{row.disk_paths.length ? (row.disk_paths[0].startsWith("/media") ? "/media" : "/data") : "✗"}</td>
        <td>{row.in_jellyfin ? "✓" : "✗"}</td>
        <td class="flags">{row.flags.join(", ")}</td>
        <td onclick={(e) => e.stopPropagation()}>{#if importable(row)}<ImportButton {row} pending={activeKeys.has(row.key)} />{/if}</td>
      </tr>
      {#if expanded === row.key}<tr><td colspan="8"><RowDetail {row} /></td></tr>{/if}
    {/each}
  </tbody>
</table>

<style>
  :global(body) { background: #0f1115; color: #e5e7eb; font-family: "IBM Plex Sans", sans-serif; }
  header { display: flex; gap: 1.5rem; align-items: center; padding: 1rem; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 0.4rem 0.7rem; border-bottom: 1px solid #1f2430; }
  tbody tr { cursor: pointer; }
  tbody tr:hover { background: #161a22; }
  .flags { color: #fbbf24; }
  .stale { color: #f87171; }
  .err { color: #f87171; padding: 0 1rem; }
</style>
