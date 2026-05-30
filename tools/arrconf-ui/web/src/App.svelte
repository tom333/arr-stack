<script lang="ts">
  import { onMount } from 'svelte';
  import type { ConfigPayload, MediaCategory, PydanticErrorEntry, RootSchema, SaveStatus, SemanticDiff } from './types';
  import { APP_SECTIONS, CONFIG_FILE_PATHS } from './constants';
  import type { ActiveConfig } from './constants';
  import * as api from './api';
  import { ApiError } from './api';
  import { UNSAVED_SWITCH_MESSAGE } from './i18n/fr';
  import HeaderBar from './lib/HeaderBar.svelte';
  import CategoriesEditor from './lib/CategoriesEditor.svelte';
  import AppSection from './lib/AppSection.svelte';
  import DiffPanel from './lib/DiffPanel.svelte';
  import SaveToast from './lib/SaveToast.svelte';
  import ValidationBanner from './lib/ValidationBanner.svelte';
  import Spinner from './lib/Spinner.svelte';
  import SectionDoc from './lib/SectionDoc.svelte';

  // State (Svelte 5 runes per UI-SPEC).
  let schema = $state<RootSchema | null>(null);
  let configState = $state<ConfigPayload | null>(null);
  let savedConfig = $state<ConfigPayload | null>(null);
  let validationErrors = $state<PydanticErrorEntry[]>([]);
  let saveStatus = $state<SaveStatus>('idle');
  let loadError = $state<string | null>(null);

  // Diff panel + toast visibility.
  let showDiffPanel = $state(false);
  let pendingDiff = $state<SemanticDiff | null>(null);
  let showSaveToast = $state(false);

  // Active config selector state (Phase 26 D-01/D-04).
  let activeConfig = $state<ActiveConfig>('arrconf');
  let confirmSwitchOpen = $state(false);
  let pendingSwitch = $state<ActiveConfig | null>(null);

  // Derived: diff count for HeaderBar chip.
  const diffCount = $derived(
    configState && savedConfig
      ? (JSON.stringify(configState) === JSON.stringify(savedConfig) ? 0 : 1)
      : 0
  );

  async function loadForConfig(cfg: ActiveConfig) {
    schema = null; configState = null;
    try {
      const [s, c] = cfg === 'arrconf'
        ? await Promise.all([api.getSchema(), api.getConfig()])
        : await Promise.all([api.getConfigarrSchema(), api.getConfigarrConfig()]);
      schema = s;
      configState = c as ConfigPayload;
      savedConfig = JSON.parse(JSON.stringify(c)) as ConfigPayload;
      loadError = null;
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    }
  }

  onMount(async () => {
    await loadForConfig('arrconf');
  });

  function updateCategories(next: MediaCategory[]) {
    if (!configState) return;
    configState = { ...configState, categories: next };
  }

  function updateAppSection(name: string, next: Record<string, unknown>) {
    if (!configState) return;
    configState = { ...configState, [name]: next } as ConfigPayload;
  }

  async function openDiffPanel() {
    if (!configState) return;
    try {
      const resp = activeConfig === 'arrconf'
        ? await api.postDiff(configState)
        : await api.postConfigarrDiff(configState as Record<string, unknown>);
      pendingDiff = resp.diff;
      showDiffPanel = true;
    } catch (e) {
      console.error('diff preview failed', e);
      // Fall back to opening with an empty diff — operator still can confirm.
      pendingDiff = {} as SemanticDiff;
      showDiffPanel = true;
    }
  }

  async function confirmSave() {
    if (!configState) return;
    saveStatus = 'saving';
    showDiffPanel = false;
    try {
      const resp = activeConfig === 'arrconf'
        ? await api.putConfig(configState)
        : await api.putConfigarrConfig(configState as Record<string, unknown>);
      savedConfig = JSON.parse(JSON.stringify(configState)) as ConfigPayload;
      validationErrors = [];
      saveStatus = 'saved';
      showSaveToast = true;
      pendingDiff = resp.diff;
    } catch (e) {
      saveStatus = 'error';
      if (e instanceof ApiError && Array.isArray(e.detail)) {
        validationErrors = e.detail as PydanticErrorEntry[];
      } else {
        console.error('save failed', e);
      }
    }
  }

  function cancelDiffPanel() {
    showDiffPanel = false;
  }

  // Tab switch + confirm gate (D-04).
  function requestTabChange(next: ActiveConfig) {
    if (next === activeConfig) return;
    if (diffCount > 0) { pendingSwitch = next; confirmSwitchOpen = true; return; }
    void doSwitch(next);
  }
  async function doSwitch(next: ActiveConfig) {
    activeConfig = next; confirmSwitchOpen = false; pendingSwitch = null;
    await loadForConfig(next);
  }
  function cancelSwitch() { confirmSwitchOpen = false; pendingSwitch = null; }
</script>

<HeaderBar
  filePath={CONFIG_FILE_PATHS[activeConfig]}
  {diffCount}
  {saveStatus}
  onSaveClick={openDiffPanel}
  {activeConfig}
  onTabChange={requestTabChange}
/>

{#if confirmSwitchOpen}
  <div class="confirm-overlay" role="dialog" aria-modal="true">
    <div class="confirm-dialog">
      <p class="confirm-message">{UNSAVED_SWITCH_MESSAGE}</p>
      <div class="confirm-actions">
        <button type="button" class="confirm-btn confirm-btn-cancel" onclick={cancelSwitch}>Annuler</button>
        <button type="button" class="confirm-btn confirm-btn-change" onclick={() => pendingSwitch && void doSwitch(pendingSwitch)}>Changer</button>
      </div>
    </div>
  </div>
{/if}

{#if loadError}
  <div class="load-error" role="alert">
    Impossible de charger {CONFIG_FILE_PATHS[activeConfig]} — {loadError}. Vérifie le chemin du fichier puis réessaie.
  </div>
{:else if !configState || !schema}
  <Spinner label="Chargement de {CONFIG_FILE_PATHS[activeConfig]}…" />
{:else}
  <main class="page">
    <ValidationBanner errors={validationErrors} onDismiss={() => (validationErrors = [])} />

    {#if showDiffPanel && pendingDiff}
      <DiffPanel diff={pendingDiff} onConfirm={confirmSave} onCancel={cancelDiffPanel} />
    {/if}

    {#if activeConfig === 'arrconf'}
      <SectionDoc section="categories" defaultOpen={false} />
      <CategoriesEditor categories={configState.categories} onChange={updateCategories} />
      {#each APP_SECTIONS as sectionName}
        {@const sectionSchema = schema.properties[sectionName]}
        {#if sectionSchema}
          <SectionDoc section={sectionName} />
          <AppSection
            {sectionName}
            {sectionSchema}
            root={schema}
            value={(configState as Record<string, unknown>)[sectionName] as Record<string, unknown>}
            onChange={(next) => updateAppSection(sectionName, next)}
            errors={validationErrors}
          />
        {/if}
      {/each}
    {:else}
      <SectionDoc section="configarr" defaultOpen={true} />
      {#each Object.keys(schema!.properties).filter(
        (k) => (schema!.properties[k] as { additionalProperties?: unknown }).additionalProperties != null
      ) as sectionName}
        {@const sectionSchema = schema!.properties[sectionName]}
        {#if sectionSchema}
          <SectionDoc section={`configarr.${sectionName}`} />
          <AppSection
            {sectionName}
            {sectionSchema}
            root={schema}
            value={(configState as Record<string, unknown>)[sectionName] as Record<string, unknown>}
            onChange={(next) => updateAppSection(sectionName, next)}
            errors={validationErrors}
          />
        {/if}
      {/each}
    {/if}
  </main>
{/if}

{#if showSaveToast}
  <SaveToast onDismiss={() => (showSaveToast = false)} />
{/if}

<style>
  .page {
    max-width: 960px;
    margin: var(--space-lg) auto;
    padding: 0 var(--space-lg);
  }
  .load-error {
    margin: var(--space-lg);
    padding: var(--space-md);
    background: var(--color-error-bg);
    border-left: 4px solid var(--color-destructive);
    border-radius: 4px;
    color: var(--color-destructive);
  }
  .confirm-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.4);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 100;
  }
  .confirm-dialog {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: var(--space-lg);
    max-width: 420px;
    box-shadow: var(--shadow-sm);
  }
  .confirm-message {
    margin: 0 0 var(--space-md);
    color: var(--ink);
    font-size: 14px;
  }
  .confirm-actions {
    display: flex;
    gap: var(--space-sm);
    justify-content: flex-end;
  }
  .confirm-btn {
    padding: var(--space-sm) var(--space-md);
    border-radius: 3px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
  }
  .confirm-btn-cancel {
    background: transparent;
    border: 1px solid var(--border);
    color: var(--ink-muted);
  }
  .confirm-btn-change {
    background: var(--accent);
    border: 1px solid var(--accent);
    color: var(--accent-fg);
  }
</style>
