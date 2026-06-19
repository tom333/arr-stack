<script lang="ts">
  import { getDashboard, getActions, removeStuck, jellyfinScan, type Snapshot, type Row } from "./api";
  import ChainPastilles from "./lib/ChainPastilles.svelte";
  import RowDetail from "./lib/RowDetail.svelte";
  import ImportButton from "./lib/ImportButton.svelte";
  import ActionsPanel from "./lib/ActionsPanel.svelte";
  import ConfirmDialog from "./lib/ConfirmDialog.svelte";

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
  // Import needs a file on disk: a completed download (progress 1.0) or an existing
  // disk path. Without this, a 0%-progress download trips deja-possede-regrab and the
  // button is offered, but perform_import has nothing to scan ("no matching file").
  const hasReadyFile = (r: Row) => r.disk_paths.length > 0 || r.downloads.some((d) => d.progress >= 1);
  const importable = (r: Row) =>
    (r.flags.includes("non-importe") || r.flags.includes("deja-possede-regrab")) && hasReadyFile(r);
  let removing = $state<Row | null>(null);
  async function doRemove() { const r = removing; removing = null; if (r) await removeStuck(r.key); }
  async function doScan(r: Row) { await jellyfinScan(r.key); }
  const isStuck = (r: Row) => r.flags.includes("bloque");
  // disk_paths is only populated for movie rows (correlate.py) → a scan needs a path,
  // so series rows (always empty disk_paths) would 409. Gate the button on having a path.
  const notInJf = (r: Row) => r.flags.includes("pas-dans-jellyfin") && r.disk_paths.length > 0;
  const worstDiag = (r: Row) => {
    const diags = r.downloads.map((d) => d.diagnosis).filter((x): x is NonNullable<typeof x> => !!x);
    if (!diags.length) return null;
    return diags.find((d) => !d.recoverable) ?? diags[0];
  };
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
        <td class="flags">
          {row.flags.join(", ")}
          {#if worstDiag(row)}
            {@const wd = worstDiag(row)}
            <span class="diag" class:dead={!wd!.recoverable}>
              {wd!.label}{#if wd!.host} ({wd!.host}){/if}
            </span>
          {/if}
        </td>
        <td onclick={(e) => e.stopPropagation()}>
          {#if importable(row)}<ImportButton {row} pending={activeKeys.has(row.key)} />{/if}
          {#if isStuck(row)}<button class="act warn" onclick={() => (removing = row)}>Suppr bloqué</button>{/if}
          {#if notInJf(row)}<button class="act" onclick={() => doScan(row)}>Scan JF</button>{/if}
        </td>
      </tr>
      {#if expanded === row.key}<tr><td colspan="8"><RowDetail {row} /></td></tr>{/if}
    {/each}
  </tbody>
</table>

{#if removing}
  <ConfirmDialog title={`Supprimer le téléchargement bloqué`} detail={`${removing.title}`}
    warn="⚠ supprime le(s) torrent(s) bloqué(s) ET leurs fichiers"
    onConfirm={doRemove} onCancel={() => (removing = null)} />
{/if}

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
  .act { background: #374151; color: #e5e7eb; border: 0; padding: .2rem .5rem; border-radius: 4px; cursor: pointer; margin-left: .3rem; font-size: .75rem; }
  .act.warn { background: #b91c1c; color: #fff; }
  .diag { display: inline-block; margin-left: .4rem; padding: .05rem .4rem; border-radius: 3px;
    font-size: .72rem; background: #78350f; color: #fde68a; }
  .diag.dead { background: #7f1d1d; color: #fecaca; }
</style>
