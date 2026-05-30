<script lang="ts">
  import type { TrashQPEntry } from '../types';
  import { getTrashQualityProfiles } from '../api';
  import {
    TRASH_COLLISION_WARNING_TEXT,
    TRASH_QP_ADD_LABEL,
  } from '../i18n/fr';
  import Spinner from './Spinner.svelte';

  type QualityProfileEntry = Record<string, unknown>;
  type Props = {
    app: 'sonarr' | 'radarr';
    existingProfiles: QualityProfileEntry[];
    onChange: (next: QualityProfileEntry[]) => void;
  };
  let { app, existingProfiles, onChange }: Props = $props();

  let catalog = $state<TrashQPEntry[]>([]);
  let loading = $state(false);
  let error = $state<string | null>(null);
  let selectedQP = $state<TrashQPEntry | null>(null);
  let nameOverride = $state('');

  $effect(() => {
    loading = true;
    error = null;
    getTrashQualityProfiles(app)
      .then((data) => { catalog = data; loading = false; })
      .catch((e) => { error = String(e); loading = false; });
  });

  const collisionName = $derived(nameOverride || (selectedQP?.name ?? ''));

  const hasCollision = $derived(
    existingProfiles.some(
      (p) => (p as { name?: string }).name === collisionName
    )
  );

  // NOTE: field mapping is MEDIUM confidence (research correction #4):
  // cutoff → upgrade.until_quality, cutoffFormatScore → upgrade.until_score,
  // items[allowed!=false] → qualities[]. Flag for human verification in Plan 04 checkpoint.
  function generateQPEntry(qp: TrashQPEntry, profileName: string): QualityProfileEntry {
    const qualities = qp.items
      .filter((item) => item.allowed !== false)
      .map((item) =>
        item.items ? { name: item.name, qualities: item.items } : { name: item.name }
      );
    return {
      name: profileName,
      language: qp.language ?? 'Any',
      reset_unmatched_scores: { enabled: true },
      upgrade: {
        allowed: qp.upgradeAllowed,
        until_quality: qp.cutoff,
        until_score: qp.cutoffFormatScore ?? 10000,
        min_format_score: 1,
      },
      min_format_score: qp.minFormatScore ?? 0,
      quality_sort: 'top',
      qualities,
    };
  }

  function confirmInsert() {
    if (!selectedQP || hasCollision) return;
    const newEntry = generateQPEntry(selectedQP, collisionName);
    onChange([...existingProfiles, newEntry]);
    selectedQP = null;
    nameOverride = '';
  }

  function descriptionAsText(desc: string): string {
    // Prefer text-render over {@html} to avoid XSS surface (T-27-10)
    return desc.replace(/<br\s*\/?>/gi, '\n');
  }
</script>

<div class="qp-picker">
  <div class="picker-header">
    <span class="picker-title">Quality profiles TRaSH</span>
  </div>

  {#if loading}
    <Spinner label="Chargement des quality profiles TRaSH…" />
  {:else if error}
    <div class="error-msg" role="alert">{error}</div>
  {:else}
    <div class="select-row">
      <select
        class="qp-select"
        onchange={(e) => {
          const val = (e.currentTarget as HTMLSelectElement).value;
          selectedQP = catalog.find((q) => q.trash_id === val) ?? null;
          nameOverride = '';
        }}
        value={selectedQP?.trash_id ?? ''}
      >
        <option value="">— Choisir un quality profile —</option>
        {#each catalog as qp}
          <option value={qp.trash_id}>{qp.name}</option>
        {/each}
      </select>
    </div>

    {#if selectedQP}
      <div class="qp-detail">
        {#if selectedQP.trash_description}
          <pre class="qp-desc">{descriptionAsText(selectedQP.trash_description)}</pre>
        {/if}
        {#if selectedQP.trash_score_set}
          <div class="qp-meta">Score set : <code>{selectedQP.trash_score_set}</code></div>
        {/if}
      </div>

      <div class="name-row">
        <label class="name-label" for="qp-name-override">Nom du profile</label>
        <input
          id="qp-name-override"
          type="text"
          class="name-input"
          bind:value={nameOverride}
          placeholder={selectedQP.name}
        />
      </div>

      {#if hasCollision}
        <div class="error-msg" role="alert">{TRASH_COLLISION_WARNING_TEXT}</div>
      {/if}

      <button
        type="button"
        class="array-add"
        onclick={confirmInsert}
        disabled={hasCollision || !selectedQP}
      >
        {TRASH_QP_ADD_LABEL}
      </button>
    {/if}
  {/if}
</div>

<style>
  .qp-picker {
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

  .select-row {
    display: flex;
    gap: var(--space-xs);
  }

  .qp-select {
    flex: 1;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--ink);
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 13px;
    padding: var(--space-xs) var(--space-sm);
  }

  .qp-select:focus {
    outline: none;
    border-color: var(--border-strong);
  }

  .qp-detail {
    background: var(--panel-alt);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: var(--space-sm);
    display: flex;
    flex-direction: column;
    gap: var(--space-xs);
  }

  .qp-desc {
    color: var(--ink-muted);
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .qp-meta {
    color: var(--ink-muted);
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 12px;
  }

  .qp-meta code {
    font-family: 'IBM Plex Mono', monospace;
  }

  .name-row {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
  }

  .name-label {
    color: var(--ink-muted);
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 12px;
    white-space: nowrap;
  }

  .name-input {
    flex: 1;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--ink);
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 13px;
    padding: var(--space-xs) var(--space-sm);
  }

  .name-input:focus {
    outline: none;
    border-color: var(--border-strong);
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
