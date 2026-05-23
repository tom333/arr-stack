<script lang="ts">
  import { onMount } from 'svelte';
  import type { ConfigPayload, MediaCategory, PydanticErrorEntry, RootSchema, SaveStatus, SemanticDiff } from './types';
  import { APP_SECTIONS } from './constants';
  import * as api from './api';
  import { ApiError } from './api';
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

  // Derived: diff count for HeaderBar chip.
  const diffCount = $derived(
    configState && savedConfig
      ? (JSON.stringify(configState) === JSON.stringify(savedConfig) ? 0 : 1)
      : 0
  );

  onMount(async () => {
    try {
      const [s, c] = await Promise.all([api.getSchema(), api.getConfig()]);
      schema = s;
      configState = c;
      savedConfig = JSON.parse(JSON.stringify(c)) as ConfigPayload;
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    }
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
      const resp = await api.postDiff(configState);
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
      const resp = await api.putConfig(configState);
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
</script>

<HeaderBar
  filePath="charts/arr-stack/files/arrconf.yml"
  {diffCount}
  {saveStatus}
  onSaveClick={openDiffPanel}
/>

{#if loadError}
  <div class="load-error" role="alert">
    Could not load arrconf.yml — {loadError}. Check the file path and try again.
  </div>
{:else if !configState || !schema}
  <Spinner label="Loading arrconf.yml…" />
{:else}
  <main class="page">
    <ValidationBanner errors={validationErrors} onDismiss={() => (validationErrors = [])} />

    {#if showDiffPanel && pendingDiff}
      <DiffPanel diff={pendingDiff} onConfirm={confirmSave} onCancel={cancelDiffPanel} />
    {/if}

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
          value={configState[sectionName] as Record<string, unknown>}
          onChange={(next) => updateAppSection(sectionName, next)}
          errors={validationErrors}
        />
      {/if}
    {/each}
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
</style>
