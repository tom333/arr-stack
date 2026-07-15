<script lang="ts">
  import { onMount } from "svelte";
  import {
    getReleases, refreshReleases, grabRelease, getCategories,
    type ScoredRelease, type Release, type MovieCategory,
  } from "../api";
  import { markSeen, seenSnapshot } from "./seen";

  let items = $state<ScoredRelease[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let profile = $state("MULTi.VF");
  let hideInLibrary = $state(true);
  let acceptedOnly = $state(true);
  let hideSeen = $state(true);
  let seenSet = $state<Set<string>>(seenSnapshot());
  let tracker = $state("");
  let genre = $state("");

  // category picker (popup on Récupérer)
  let categories = $state<MovieCategory[]>([]);
  let grabbing = $state<Release | null>(null);   // release awaiting category choice
  let grabCategory = $state("");                  // selected category name
  let grabBusy = $state(false);
  let grabError = $state<string | null>(null);

  const PROFILES = ["MULTi.VF", "Anime", "Family"];
  const DEFAULT_CATEGORY = "nouveaux-films";      // new downloads default here (not "films")

  function ageLabel(iso: string): string {
    const d = Date.parse(iso);
    if (Number.isNaN(d)) return "—";
    const h = (Date.now() - d) / 3.6e6;
    if (h < 24) return `${Math.round(h)}h`;
    return `${Math.round(h / 24)}j`;
  }
  function gb(bytes: number): string {
    return bytes ? `${(bytes / 1e9).toFixed(1)} Go` : "—";
  }

  async function load() {
    loading = true;
    error = null;
    try {
      items = await getReleases(profile);
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      loading = false;
    }
    seenSet = seenSnapshot();
  }

  async function forceRefresh() {
    await refreshReleases();
    await load();
  }

  function openGrab(r: Release) {
    if (r.tmdb_id == null) {
      error = `Pas de TMDB résolu pour ${r.title}`;
      return;
    }
    grabError = null;
    const names = categories.map((c) => c.name);
    grabCategory = names.includes(DEFAULT_CATEGORY) ? DEFAULT_CATEGORY : (names[0] ?? "");
    grabbing = r;
  }

  async function confirmGrab() {
    const r = grabbing;
    if (!r || r.tmdb_id == null || !grabCategory) return;
    grabBusy = true;
    grabError = null;
    try {
      await grabRelease({
        info_hash: r.info_hash, tmdb_id: r.tmdb_id, title: r.title,
        year: r.year, category: grabCategory,
      });
      grabbing = null;
      await load();
    } catch (e) {
      grabError = e instanceof Error ? e.message : String(e);
    } finally {
      grabBusy = false;
    }
  }

  const trackers = $derived(
    [...new Set(items.map((sr) => sr.release.indexer_name))].sort()
  );

  const genres = $derived(
    [...new Set(items.flatMap((sr) => sr.release.genres))].sort()
  );

  const visible = $derived(
    items.filter((sr) => {
      if (hideInLibrary && sr.release.in_library) return false;
      if (acceptedOnly && !sr.accepted) return false;
      if (hideSeen && seenSet.has(sr.release.info_hash)) return false;
      if (tracker && sr.release.indexer_name !== tracker) return false;
      if (genre && !sr.release.genres.includes(genre)) return false;
      return true;
    })
  );

  $effect(() => { profile; load(); });

  onMount(async () => {
    try { categories = await getCategories(); } catch { categories = []; }
  });
</script>

<div class="releases">
  <div class="controls">
    <label>Profil
      <select bind:value={profile}>
        {#each PROFILES as p}<option value={p}>{p}</option>{/each}
      </select>
    </label>
    <label><input type="checkbox" bind:checked={hideInLibrary} /> Masquer déjà en biblio</label>
    <label><input type="checkbox" bind:checked={acceptedOnly} /> Accepté par le profil</label>
    <label><input type="checkbox" bind:checked={hideSeen} onchange={() => (seenSet = seenSnapshot())} /> Masquer les vus</label>
    <label>Tracker
      <select bind:value={tracker}>
        <option value="">Tous les trackers</option>
        {#each trackers as t}<option value={t}>{t}</option>{/each}
      </select>
    </label>
    <label>Genre
      <select bind:value={genre}>
        <option value="">Tous genres</option>
        {#each genres as g}<option value={g}>{g}</option>{/each}
      </select>
    </label>
    <button class="btn btn-secondary" onclick={forceRefresh}>Rafraîchir</button>
  </div>

  {#if error}<p class="error">{error}</p>{/if}
  {#if loading}
    <p>Chargement…</p>
  {:else}
    <table>
      <thead><tr><th>Poster</th><th>Titre</th><th>Année</th><th>Genre</th><th>Qualité</th><th>Score</th><th>Seed/Leech</th><th>Âge · Taille</th><th>Tracker</th><th>Langue</th><th></th></tr></thead>
      <tbody>
        {#each visible as sr (sr.release.info_hash)}
          <tr
            class:in-library={sr.release.in_library}
            class:rejected={!sr.accepted}
            class:seen={seenSet.has(sr.release.info_hash)}
            onmouseenter={() => markSeen(sr.release.info_hash)}
          >
            <td>
              {#if sr.release.poster_url}<img src={sr.release.poster_url} alt="" class="poster" loading="lazy" />{/if}
            </td>
            <td>{sr.release.title}</td>
            <td class="mono">{sr.release.year ?? "—"}</td>
            <td>
              {#if sr.release.genres.includes("Animation")}
                <span class="chip chip-info">Animation</span> {sr.release.genres.join(", ") || "—"}
              {:else}
                {sr.release.genres.join(", ") || "—"}
              {/if}
            </td>
            <td>{sr.release.resolution ?? "?"} {sr.release.source ?? ""} {sr.release.codec ?? ""}</td>
            <td class="mono" title={sr.reasons.join(", ")}>{sr.score}</td>
            <td class="mono" class:dead={sr.release.seeders === 0}>{sr.release.seeders ?? "?"}/{sr.release.leechers ?? "?"}</td>
            <td class="mono">{ageLabel(sr.release.publish_date)} · {gb(sr.release.size)}</td>
            <td>{sr.release.indexer_name}</td>
            <td>{sr.release.language ?? "—"}</td>
            <td>
              {#if sr.release.in_library}<span class="badge">en biblio</span>
              {:else}<button class="btn btn-primary" onclick={() => openGrab(sr.release)} disabled={sr.release.tmdb_id == null}>Récupérer</button>{/if}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
    {#if visible.length === 0}<p>Aucune sortie récente.</p>{/if}
  {/if}
</div>

{#if grabbing}
  <div class="modal-backdrop" onclick={() => (grabbing = null)} role="presentation">
    <div class="modal" onclick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
      <h3>Récupérer</h3>
      <p class="modal-title">{grabbing.title}</p>
      <label>Catégorie
        <select bind:value={grabCategory}>
          {#each categories as c}<option value={c.name}>{c.display}</option>{/each}
        </select>
      </label>
      {#if categories.length === 0}<p class="error">Catégories indisponibles (intent non monté)</p>{/if}
      {#if grabError}<p class="error">{grabError}</p>{/if}
      <div class="modal-actions">
        <button class="btn btn-secondary" onclick={() => (grabbing = null)} disabled={grabBusy}>Annuler</button>
        <button class="btn btn-primary" onclick={confirmGrab} disabled={grabBusy || !grabCategory}>
          {grabBusy ? "…" : "Récupérer"}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .controls { display: flex; gap: 1rem; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; padding: 1rem 1.25rem; }
  .controls label { display: flex; align-items: center; gap: 0.35rem; color: var(--text-muted); font-size: 0.85rem; }
  .controls select {
    background: var(--surface-2); color: var(--text); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 0.3rem 0.5rem; font-family: var(--font-sans);
  }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 0.5rem 0.7rem; border-bottom: 1px solid var(--border-subtle); vertical-align: middle; }
  th { color: var(--text-muted); text-transform: uppercase; font-size: 0.72rem; letter-spacing: 0.04em; font-weight: 500; }
  tbody tr:hover { background: var(--surface-2); }
  tr.in-library { opacity: 0.55; }
  tr.rejected { opacity: 0.4; }
  tr.seen { opacity: 0.6; }
  .badge { font-size: 0.8em; padding: 0.15rem 0.5rem; border: 1px solid var(--accent); border-radius: var(--radius-sm); color: var(--accent); }
  .chip { display: inline-block; font-size: 0.7em; padding: 0.1rem 0.4rem; border-radius: var(--radius-sm); font-weight: 600; margin-right: 0.3rem; }
  .chip-info { background: var(--info); color: var(--bg); }
  .error { color: var(--danger); padding: 0 1.25rem; }
  .poster { width: 105px; height: 158px; object-fit: cover; border-radius: var(--radius); border: 1px solid var(--border-subtle); display: block; }
  td.dead { color: var(--danger); }
  .modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,.6); display: flex; align-items: center; justify-content: center; z-index: 50; }
  .modal { background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.2rem 1.5rem; min-width: 320px; max-width: 90vw; }
  .modal h3 { margin: 0 0 .3rem; }
  .modal-title { color: var(--text-muted); margin: 0 0 1rem; }
  .modal label { display: block; margin-bottom: 1rem; }
  .modal select {
    display: block; margin-top: .3rem; width: 100%; padding: .4rem; background: var(--bg); color: var(--text);
    border: 1px solid var(--border); border-radius: var(--radius-sm); font-family: var(--font-sans);
  }
  .modal-actions { display: flex; gap: .5rem; justify-content: flex-end; }
</style>
