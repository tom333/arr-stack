<script lang="ts">
  import { getDashboard, getActions, removeStuck, jellyfinScan, type Snapshot, type Row } from "./api";
  import ChainPastilles from "./lib/ChainPastilles.svelte";
  import RowDetail from "./lib/RowDetail.svelte";
  import ImportButton from "./lib/ImportButton.svelte";
  import ActionsPanel from "./lib/ActionsPanel.svelte";
  import ConfirmDialog from "./lib/ConfirmDialog.svelte";
  import ReleasesTab from "./lib/ReleasesTab.svelte";
  import SeriesTab from "./lib/SeriesTab.svelte";

  let tab = $state<"dashboard" | "releases" | "series">("releases");
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
  <div class="brand">
    <svg class="logo-mark" viewBox="0 0 24 24" width="26" height="26" fill="none" aria-hidden="true">
      <path d="M2 17 A5 5 0 0 1 7 22" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
      <path d="M2 11.5 A10.5 10.5 0 0 1 12.5 22" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" opacity="0.7" />
      <path d="M2 6 A16 16 0 0 1 18 22" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" opacity="0.4" />
      <circle cx="2" cy="22" r="1.6" fill="currentColor" />
    </svg>
    <div class="brand-text">
      <span class="wordmark">Arrkestra</span>
      <span class="subtitle">media pipeline control</span>
    </div>
  </div>
  <div class="header-controls">
    <label class="toggle"><input type="checkbox" bind:checked={problemsOnly} /> Problèmes seulement</label>
    {#if snap?.stale_sources?.length}<span class="stale">⚠ sources indisponibles: {snap.stale_sources.join(", ")}</span>{/if}
  </div>
</header>

<nav class="tabs">
  <button class:active={tab === "dashboard"} onclick={() => (tab = "dashboard")}>Suivi</button>
  <button class:active={tab === "releases"} onclick={() => (tab = "releases")}>Sorties</button>
  <button class:active={tab === "series"} onclick={() => (tab = "series")}>Séries</button>
</nav>

{#if tab === "dashboard"}
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
          <td class="mono">{#if row.downloads.length}{row.downloads.length > 1 ? `${row.downloads.length} torrents` : `${Math.round(row.downloads[0].progress * 100)}% ${row.downloads[0].tracker ?? ""}`}{:else}—{/if}</td>
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
{:else if tab === "series"}
  <SeriesTab />
{:else}
  <ReleasesTab />
{/if}

<style>
  header {
    display: flex; justify-content: space-between; align-items: center;
    gap: 1.5rem; padding: 0.9rem 1.25rem;
    background: var(--surface); border-bottom: 1px solid var(--border-subtle);
  }
  .brand { display: flex; align-items: center; gap: 0.65rem; }
  .logo-mark { color: var(--accent); flex-shrink: 0; }
  .brand-text { display: flex; flex-direction: column; line-height: 1.2; }
  .wordmark { font-weight: 600; font-size: 1.15rem; letter-spacing: 0.02em; }
  .subtitle { font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; }
  .header-controls { display: flex; align-items: center; gap: 1rem; }
  .toggle { display: flex; align-items: center; gap: 0.35rem; color: var(--text-muted); font-size: 0.85rem; cursor: pointer; }

  nav.tabs { display: flex; gap: 1.25rem; padding: 0 1.25rem; border-bottom: 1px solid var(--border-subtle); background: var(--surface); }
  nav.tabs button {
    background: transparent; color: var(--text-muted); border: 0; border-bottom: 2px solid transparent;
    padding: 0.6rem 0.1rem; cursor: pointer; font-size: 0.9rem; font-weight: 500;
    transition: color var(--dur) ease, border-color var(--dur) ease;
  }
  nav.tabs button:hover { color: var(--text); }
  nav.tabs button.active { color: var(--accent); border-bottom-color: var(--accent); }

  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 0.5rem 0.7rem; border-bottom: 1px solid var(--border-subtle); }
  th { color: var(--text-muted); text-transform: uppercase; font-size: 0.72rem; letter-spacing: 0.04em; font-weight: 500; }
  tbody tr { cursor: pointer; }
  tbody tr:hover { background: var(--surface-2); }
  .flags { color: var(--warn); }
  .stale { color: var(--danger); font-size: 0.85rem; }
  .err { color: var(--danger); padding: 0 1.25rem; }
  .act { background: var(--surface-2); color: var(--text); border: 0; padding: .3rem .6rem; border-radius: var(--radius-sm); cursor: pointer; margin-left: .3rem; font-size: .75rem; }
  .act:hover { background: var(--border); }
  .act.warn { background: var(--danger); color: var(--text); }
  .diag { display: inline-block; margin-left: .4rem; padding: .05rem .45rem; border-radius: var(--radius-sm);
    font-size: .72rem; background: var(--warn); color: var(--bg); }
  .diag.dead { background: var(--danger); color: var(--text); }
</style>
