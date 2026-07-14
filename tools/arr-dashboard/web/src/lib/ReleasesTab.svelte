<script lang="ts">
  import { getReleases, refreshReleases, grabRelease, type ScoredRelease, type Release } from "../api";

  let items = $state<ScoredRelease[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let profile = $state("MULTi.VF");
  let hideInLibrary = $state(true);
  let acceptedOnly = $state(true);

  const PROFILES = ["MULTi.VF", "Anime", "Family"];

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
  }

  async function forceRefresh() {
    await refreshReleases();
    await load();
  }

  async function grab(r: Release) {
    if (r.tmdb_id == null) {
      error = `Pas de TMDB résolu pour ${r.title}`;
      return;
    }
    try {
      await grabRelease({
        info_hash: r.info_hash, tmdb_id: r.tmdb_id, title: r.title,
        year: r.year, profile,
      });
      await load();
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
  }

  const visible = $derived(
    items.filter((sr) => {
      if (hideInLibrary && sr.release.in_library) return false;
      if (acceptedOnly && !sr.accepted) return false;
      return true;
    })
  );

  $effect(() => { profile; load(); });
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
    <button onclick={forceRefresh}>Rafraîchir</button>
  </div>

  {#if error}<p class="error">{error}</p>{/if}
  {#if loading}
    <p>Chargement…</p>
  {:else}
    <table>
      <thead><tr><th>Titre</th><th>Année</th><th>Qualité</th><th>Score</th><th>Tracker</th><th>Langue</th><th></th></tr></thead>
      <tbody>
        {#each visible as sr (sr.release.info_hash)}
          <tr class:in-library={sr.release.in_library} class:rejected={!sr.accepted}>
            <td>{sr.release.title}</td>
            <td>{sr.release.year ?? "—"}</td>
            <td>{sr.release.resolution ?? "?"} {sr.release.source ?? ""} {sr.release.codec ?? ""}</td>
            <td title={sr.reasons.join(", ")}>{sr.score}</td>
            <td>{sr.release.indexer_name}</td>
            <td>{sr.release.language ?? "—"}</td>
            <td>
              {#if sr.release.in_library}<span class="badge">en biblio</span>
              {:else}<button onclick={() => grab(sr.release)} disabled={sr.release.tmdb_id == null}>Récupérer</button>{/if}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
    {#if visible.length === 0}<p>Aucune sortie récente.</p>{/if}
  {/if}
</div>

<style>
  .controls { display: flex; gap: 1rem; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; padding: 0 1rem; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 0.4rem 0.7rem; border-bottom: 1px solid #1f2430; }
  tr.in-library { opacity: 0.55; }
  tr.rejected { opacity: 0.4; }
  .badge { font-size: 0.8em; padding: 0.1rem 0.4rem; border: 1px solid #4ade80; border-radius: 4px; color: #4ade80; }
  .error { color: #f87171; padding: 0 1rem; }
  button { background: #374151; color: #e5e7eb; border: 0; padding: .2rem .5rem; border-radius: 4px; cursor: pointer; font-size: .8rem; }
</style>
