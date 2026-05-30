<script lang="ts">
  import type { TrashCFEntry } from '../types';
  import { getTrashCustomFormats } from '../api';
  import {
    TRASH_CUSTOM_BADGE_TEXT,
    TRASH_UNKNOWN_BADGE_TEXT,
    TRASH_CF_SEARCH_PLACEHOLDER,
  } from '../i18n/fr';
  import Spinner from './Spinner.svelte';

  type CustomFormatEntry = {
    trash_ids: string[];
    assign_scores_to: { name: string; score?: number }[];
  };
  type Props = {
    app: 'sonarr' | 'radarr';
    existingCustomFormats: CustomFormatEntry[];
    localDefinitions: { trash_id: string; name: string }[];
    profileNames: string[];
    onChange: (next: CustomFormatEntry[]) => void;
  };
  let { app, existingCustomFormats, localDefinitions, profileNames, onChange }: Props = $props();

  let catalog = $state<TrashCFEntry[]>([]);
  let loading = $state(false);
  let error = $state<string | null>(null);
  let query = $state('');
  let selected = $state(new Set<string>());

  $effect(() => {
    loading = true;
    error = null;
    getTrashCustomFormats(app)
      .then((data) => { catalog = data; loading = false; })
      .catch((e) => { error = String(e); loading = false; });
  });

  const filtered = $derived(
    catalog.filter((c) => c.name.toLowerCase().includes(query.toLowerCase()))
  );

  // Entries can bundle multiple trash_ids (e.g. fr-vff/fr-vfi/fr-vfq/fr-multi).
  // Classification, dedup and the already-added check must consider every id,
  // not just trash_ids[0].
  const existingIds = $derived(
    new Set(existingCustomFormats.flatMap((e) => e.trash_ids))
  );

  function toggle(id: string) {
    const next = new Set(selected);
    if (next.has(id)) { next.delete(id); } else { next.add(id); }
    selected = next;
  }

  function classify(trashId: string): 'trash' | 'custom' | 'unknown' {
    if (catalog.some((e) => e.trash_id === trashId)) return 'trash';
    if (localDefinitions.some((d) => d.trash_id === trashId)) return 'custom';
    return 'unknown';
  }

  function labelFor(trashId: string): string {
    const catalogEntry = catalog.find((e) => e.trash_id === trashId);
    if (catalogEntry) return catalogEntry.name;
    const localEntry = localDefinitions.find((d) => d.trash_id === trashId);
    if (localEntry) return localEntry.name;
    return trashId;
  }

  function confirmAdd() {
    const newEntries: CustomFormatEntry[] = [];
    for (const id of selected) {
      if (!existingIds.has(id)) {
        newEntries.push({
          trash_ids: [id],
          assign_scores_to: profileNames.map((n) => ({ name: n })),
        });
      }
    }
    if (newEntries.length > 0) {
      onChange([...existingCustomFormats, ...newEntries]);
    }
    selected = new Set();
    query = '';
  }

  // Remove a single trash_id from an entry; drop the whole entry only when its
  // last id is removed. Preserves the other ids of a multi-id bundle verbatim.
  function removeId(entryIdx: number, idIdx: number) {
    const next = existingCustomFormats.map((e, i) => {
      if (i !== entryIdx) return e;
      return { ...e, trash_ids: e.trash_ids.filter((_, j) => j !== idIdx) };
    });
    onChange(next.filter((e) => e.trash_ids.length > 0));
  }
</script>

<div class="cf-picker">
  <div class="picker-header">
    <span class="picker-title">Formats personnalisés TRaSH</span>
  </div>

  {#if loading}
    <Spinner label="Chargement du catalogue TRaSH…" />
  {:else if error}
    <div class="error-msg" role="alert">{error}</div>
  {:else}
    <div class="existing-entries">
      {#each existingCustomFormats as entry, idx}
        {#each entry.trash_ids as id, idIdx}
          {@const cls = classify(id)}
          <div class="cf-chip">
            <span class="cf-label">{labelFor(id)}</span>
            {#if cls === 'custom'}
              <span class="badge badge-custom" title={TRASH_CUSTOM_BADGE_TEXT}>custom</span>
            {:else if cls === 'unknown'}
              <span class="badge badge-warn" title={TRASH_UNKNOWN_BADGE_TEXT}>⚠ inconnu</span>
            {/if}
            <button type="button" class="array-delete" onclick={() => removeId(idx, idIdx)} aria-label="Supprimer">✕</button>
          </div>
        {/each}
      {/each}
    </div>

    <div class="search-row">
      <input
        type="text"
        class="search-input"
        bind:value={query}
        placeholder={TRASH_CF_SEARCH_PLACEHOLDER}
      />
    </div>

    {#if query}
      <div class="catalog-list">
        {#each filtered as cf}
          {@const alreadyAdded = existingIds.has(cf.trash_id)}
          <label class="catalog-row" class:added={alreadyAdded}>
            <input
              type="checkbox"
              checked={selected.has(cf.trash_id)}
              onchange={() => toggle(cf.trash_id)}
              disabled={alreadyAdded}
            />
            <span class="cf-name">{cf.name}</span>
            <span class="cf-score" title="Score par défaut TRaSH">{cf.default_score}</span>
          </label>
        {/each}
        {#if filtered.length === 0}
          <div class="empty-msg">Aucun format trouvé pour « {query} »</div>
        {/if}
      </div>

      <button
        type="button"
        class="array-add"
        onclick={confirmAdd}
        disabled={selected.size === 0}
      >
        + Ajouter les formats sélectionnés ({selected.size})
      </button>
    {/if}
  {/if}
</div>

<style>
  .cf-picker {
    display: flex;
    flex-direction: column;
    gap: var(--space-sm);
  }

  .picker-header {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
  }

  .picker-title {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 13px;
    font-weight: 600;
    color: var(--ink);
  }

  .existing-entries {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-xs);
  }

  .cf-chip {
    display: inline-flex;
    align-items: center;
    gap: var(--space-xs);
    background: var(--panel-alt);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 2px var(--space-xs);
    font-size: 12px;
    font-family: 'IBM Plex Mono', monospace;
  }

  .cf-label {
    color: var(--ink);
  }

  .badge {
    display: inline-block;
    border-radius: 4px;
    font-size: 11px;
    padding: 1px 5px;
    cursor: help;
    user-select: none;
  }

  .badge-custom {
    background: var(--color-badge-bg);
    color: var(--color-badge-fg);
  }

  .badge-warn {
    background: var(--accent-soft);
    color: var(--destructive);
  }

  .array-delete {
    background: none;
    border: none;
    color: var(--ink-muted);
    cursor: pointer;
    font-size: 11px;
    padding: 0 2px;
    line-height: 1;
  }

  .array-delete:hover {
    color: var(--destructive);
  }

  .search-row {
    display: flex;
    gap: var(--space-xs);
  }

  .search-input {
    flex: 1;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--ink);
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 13px;
    padding: var(--space-xs) var(--space-sm);
  }

  .search-input:focus {
    outline: none;
    border-color: var(--border-strong);
  }

  .catalog-list {
    max-height: 200px;
    overflow-y: auto;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--surface);
  }

  .catalog-row {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    padding: var(--space-xs) var(--space-sm);
    cursor: pointer;
    font-size: 13px;
    font-family: 'IBM Plex Sans', sans-serif;
    color: var(--ink);
  }

  .catalog-row:hover {
    background: var(--panel-alt);
  }

  .catalog-row.added {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .cf-name {
    flex: 1;
  }

  .cf-score {
    color: var(--ink-muted);
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
  }

  .empty-msg {
    padding: var(--space-sm);
    color: var(--ink-muted);
    font-size: 13px;
    font-style: italic;
  }

  .array-add {
    align-self: flex-start;
    background: var(--accent-soft);
    border: 1px solid var(--accent);
    border-radius: 4px;
    color: var(--accent-fg);
    cursor: pointer;
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 13px;
    padding: var(--space-xs) var(--space-sm);
  }

  .array-add:hover:not(:disabled) {
    background: var(--accent);
  }

  .array-add:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .error-msg {
    color: var(--destructive);
    font-size: 12px;
    margin-top: var(--space-xs);
    font-family: 'IBM Plex Mono', monospace;
  }
</style>
