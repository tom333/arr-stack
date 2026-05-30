<script lang="ts">
  // RecyclarrReferencePicker.svelte — Phase 27 CFGUI-06
  // Read-only reference dropdown for Recyclarr config-templates (D-12/D-13).
  // Research correction #1: includes.json has NO label or subtitle beyond {id, template} — id is used verbatim.
  // The id string is used verbatim as the display label (e.g. "sonarr-v4-quality-profile-bluray-web-1080p-french-multi-vf").
  // NEVER writes any config key — clipboard copy only (D-13).
  import type { RecyclarrTemplateEntry } from '../types';
  import { getRecyclarrTemplates } from '../api';
  import { RECYCLARR_REFERENCE_LABEL } from '../i18n/fr';
  import Spinner from './Spinner.svelte';

  type Props = {
    app: 'sonarr' | 'radarr';
  };
  let { app }: Props = $props();

  let templates = $state<RecyclarrTemplateEntry[]>([]);
  let selected = $state<RecyclarrTemplateEntry | null>(null);
  let loading = $state(false);
  let error = $state<string | null>(null);
  let copied = $state(false);

  $effect(() => {
    loading = true;
    error = null;
    selected = null;
    getRecyclarrTemplates(app)
      .then((data) => { templates = data; loading = false; })
      .catch((e) => { error = String(e); loading = false; });
  });

  async function copyId(id: string) {
    await navigator.clipboard.writeText(id);
    copied = true;
    setTimeout(() => { copied = false; }, 1500);
  }
</script>

<div class="recyclarr-picker">
  <div class="reference-header">
    <span class="picker-title">Référence Recyclarr</span>
    <span class="lock-badge" title={RECYCLARR_REFERENCE_LABEL}>🔒</span>
    <span class="reference-label">{RECYCLARR_REFERENCE_LABEL}</span>
  </div>

  {#if loading}
    <Spinner label="Chargement des templates Recyclarr…" />
  {:else if error}
    <div class="error-msg" role="alert">{error}</div>
  {:else}
    <div class="select-row">
      <select
        class="template-select"
        onchange={(e) => {
          const val = (e.currentTarget as HTMLSelectElement).value;
          selected = templates.find((t) => t.id === val) ?? null;
        }}
        value={selected?.id ?? ''}
      >
        <option value="">— Choisir un template —</option>
        {#each templates as tmpl}
          <option value={tmpl.id}>{tmpl.id}</option>
        {/each}
      </select>
    </div>

    {#if selected}
      <div class="template-detail">
        <code class="template-id">{selected.id}</code>
        <span class="template-path" title="Chemin dans recyclarr/config-templates">{selected.template}</span>
        <button
          type="button"
          class="copy-btn"
          onclick={() => copyId(selected!.id)}
        >
          {copied ? '✓ Copié' : 'Copier le nom'}
        </button>
      </div>
    {/if}
  {/if}
</div>

<style>
  .recyclarr-picker {
    display: flex;
    flex-direction: column;
    gap: var(--space-sm);
  }

  .reference-header {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    flex-wrap: wrap;
  }

  .picker-title {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 13px;
    font-weight: 600;
    color: var(--ink);
  }

  .lock-badge {
    font-size: 11px;
    opacity: 0.7;
    cursor: help;
    user-select: none;
  }

  .reference-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: var(--ink-muted);
    font-style: italic;
  }

  .select-row {
    display: flex;
    gap: var(--space-xs);
  }

  .template-select {
    flex: 1;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--ink);
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    padding: var(--space-xs) var(--space-sm);
  }

  .template-select:focus {
    outline: none;
    border-color: var(--border-strong);
  }

  .template-detail {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    background: var(--panel-alt);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: var(--space-sm);
    flex-wrap: wrap;
  }

  .template-id {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    color: var(--ink);
    word-break: break-all;
    flex: 1;
  }

  .template-path {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    color: var(--ink-muted);
    opacity: 0.7;
    word-break: break-all;
  }

  .copy-btn {
    background: var(--accent-soft);
    border: 1px solid var(--accent);
    border-radius: 4px;
    color: var(--accent-fg);
    cursor: pointer;
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 12px;
    padding: var(--space-xs) var(--space-sm);
    white-space: nowrap;
  }

  .copy-btn:hover {
    background: var(--accent);
  }

  .error-msg {
    color: var(--destructive);
    font-size: 12px;
    margin-top: var(--space-xs);
    font-family: 'IBM Plex Mono', monospace;
  }
</style>
