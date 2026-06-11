<script lang="ts">
  import { onMount } from 'svelte';
  import type { IntentPayload, MaterializationDiffResponse, PydanticErrorEntry, RootSchema, SaveStatus } from './types';
  import { CONFIG_FILE_PATHS } from './constants';
  import type { ActiveConfig } from './constants';
  import * as api from './api';
  import { ApiError } from './api';
  import { UNSAVED_SWITCH_MESSAGE } from './i18n/fr';
  import HeaderBar from './lib/HeaderBar.svelte';
  import MaterializationDiffPanel from './lib/MaterializationDiffPanel.svelte';
  import ReadOnlyInspector from './lib/ReadOnlyInspector.svelte';
  import SaveToast from './lib/SaveToast.svelte';
  import ValidationBanner from './lib/ValidationBanner.svelte';
  import Spinner from './lib/Spinner.svelte';
  import SectionDoc from './lib/SectionDoc.svelte';
  import CategoriesEditor from './lib/CategoriesEditor.svelte';
  import AppSection from './lib/AppSection.svelte';
  import ProfileDefinitionsEditor from './lib/ProfileDefinitionsEditor.svelte';
  import ConfigarrRawEditor from './lib/ConfigarrRawEditor.svelte';
  import type { MediaCategory } from './types';

  // Intent tab state.
  let schema = $state<RootSchema | null>(null);
  let intentState = $state<IntentPayload | null>(null);
  let savedIntent = $state<IntentPayload | null>(null);
  let validationErrors = $state<PydanticErrorEntry[]>([]);
  let saveStatus = $state<SaveStatus>('idle');
  let loadError = $state<string | null>(null);

  // Inspector tab state (raw file content for arrconf/configarr tabs).
  let inspectorContent = $state<string | null>(null);

  // Materialization diff panel state.
  let showDiffPanel = $state(false);
  let pendingMatDiff = $state<MaterializationDiffResponse | null>(null);
  let pendingSaveSnapshot = $state<IntentPayload | null>(null);
  let showSaveToast = $state(false);

  // Active config selector state (Phase 34 three-tab).
  let activeConfig = $state<ActiveConfig>('intent');
  let confirmSwitchOpen = $state(false);
  let pendingSwitch = $state<ActiveConfig | null>(null);

  // Bumped on each fresh intent load — {#key loadEpoch} remounts the form so
  // init-from-prop $state in section editors resyncs (WR-02).
  let loadEpoch = $state(0);

  // Derived: diff count for HeaderBar chip.
  // Only meaningful on the intent tab — shows 1 if in-memory intent differs from last-saved.
  const diffCount = $derived(
    activeConfig === 'intent' && intentState && savedIntent
      ? (JSON.stringify(intentState) === JSON.stringify(savedIntent) ? 0 : 1)
      : 0
  );

  async function loadForConfig(cfg: ActiveConfig) {
    loadError = null;
    if (cfg === 'intent') {
      schema = null;
      intentState = null;
      savedIntent = null;
      try {
        const [s, intent] = await Promise.all([api.getIntentSchema(), api.getIntent()]);
        schema = s;
        intentState = intent;
        savedIntent = JSON.parse(JSON.stringify(intent)) as IntentPayload;
        loadEpoch += 1;
      } catch (e) {
        loadError = e instanceof Error ? e.message : String(e);
      }
    } else if (cfg === 'arrconf') {
      inspectorContent = null;
      try {
        // getConfig returns ConfigPayload (object); stringify for inspector display.
        const raw = await api.getConfig();
        inspectorContent = typeof raw === 'string' ? raw : JSON.stringify(raw, null, 2);
      } catch (e) {
        loadError = e instanceof Error ? e.message : String(e);
      }
    } else {
      // configarr
      inspectorContent = null;
      try {
        const raw = await api.getConfigarrConfig();
        inspectorContent = typeof raw === 'string' ? raw : JSON.stringify(raw, null, 2);
      } catch (e) {
        loadError = e instanceof Error ? e.message : String(e);
      }
    }
  }

  onMount(async () => {
    await loadForConfig('intent');
  });

  async function openDiffPanel() {
    if (!intentState) return;
    // WR-04: snapshot what the operator will review — confirmSave saves THIS,
    // not whatever intentState becomes while the panel is open.
    const snapshot = JSON.parse(JSON.stringify(intentState)) as IntentPayload;
    try {
      const r = await api.postIntentDiff(snapshot);
      pendingSaveSnapshot = snapshot;
      pendingMatDiff = r;
      showDiffPanel = true;
    } catch (e) {
      // IN-04: do NOT show an empty diff on failure — surface the error instead.
      console.error('diff preview failed', e);
      loadError = e instanceof Error ? e.message : String(e);
    }
  }

  async function confirmSave() {
    if (!pendingSaveSnapshot) return;
    const toSave = pendingSaveSnapshot;
    saveStatus = 'saving';
    showDiffPanel = false;
    try {
      await api.putIntent(toSave);
      savedIntent = JSON.parse(JSON.stringify(toSave)) as IntentPayload;
      validationErrors = [];
      saveStatus = 'saved';
      showSaveToast = true;
    } catch (e) {
      saveStatus = 'error';
      if (e instanceof ApiError && Array.isArray(e.detail)) {
        validationErrors = e.detail as PydanticErrorEntry[];
      } else {
        console.error('save failed', e);
      }
    } finally {
      pendingSaveSnapshot = null;
    }
  }

  function cancelDiffPanel() {
    showDiffPanel = false;
    pendingSaveSnapshot = null;
  }

  // Update a single key in the intent state — drives diffCount and save button.
  function updateIntent<K extends keyof IntentPayload>(key: K, val: IntentPayload[K]) {
    intentState = { ...intentState!, [key]: val };
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

{#if activeConfig === 'intent'}
  {#if loadError}
    <div class="load-error" role="alert">
      Impossible de charger {CONFIG_FILE_PATHS.intent} — {loadError}. Vérifie le chemin du fichier puis réessaie.
    </div>
  {:else if !intentState || !schema}
    <Spinner label="Chargement de intent.yml…" />
  {:else}
    <main class="page">
      <ValidationBanner errors={validationErrors} onDismiss={() => (validationErrors = [])} />

      {#if showDiffPanel && pendingMatDiff}
        <MaterializationDiffPanel
          arrconfDiff={pendingMatDiff.arrconf_diff}
          configarrDiff={pendingMatDiff.configarr_diff}
          onConfirm={confirmSave}
          onCancel={cancelDiffPanel}
        />
      {/if}

      {#key loadEpoch}
      <!-- 1. categories -->
      <SectionDoc section="intent.categories" />
      <CategoriesEditor
        categories={intentState.categories}
        onChange={(c: MediaCategory[]) => updateIntent('categories', c)}
      />

      <!-- 2. sagas -->
      <SectionDoc section="intent.sagas" />
      {#if schema?.properties?.sagas}
        <AppSection
          sectionName="sagas"
          sectionSchema={schema.properties.sagas}
          root={schema}
          value={Array.isArray(intentState.sagas) ? { items: intentState.sagas } : (intentState.sagas as Record<string, unknown>)}
          onChange={(v: Record<string, unknown>) => updateIntent('sagas', (Array.isArray(v.items) ? v.items : Object.values(v)) as Record<string, unknown>[])}
          errors={validationErrors.filter(e => e.loc[0] === 'sagas')}
        />
      {:else}
        <div class="section-fallback">
          <pre class="section-raw">{JSON.stringify(intentState.sagas, null, 2)}</pre>
        </div>
      {/if}

      <!-- 3. apps -->
      <SectionDoc section="intent.apps" />
      {#if schema?.properties?.apps}
        <AppSection
          sectionName="apps"
          sectionSchema={schema.properties.apps}
          root={schema}
          value={intentState.apps as Record<string, unknown>}
          onChange={(v: Record<string, unknown>) => updateIntent('apps', v)}
          errors={validationErrors.filter(e => e.loc[0] === 'apps')}
        />
      {:else}
        <div class="section-fallback">
          <pre class="section-raw">{JSON.stringify(intentState.apps, null, 2)}</pre>
        </div>
      {/if}

      <!-- 4. tools -->
      <SectionDoc section="intent.tools" />
      {#if schema?.properties?.tools}
        <AppSection
          sectionName="tools"
          sectionSchema={schema.properties.tools}
          root={schema}
          value={intentState.tools as Record<string, unknown>}
          onChange={(v: Record<string, unknown>) => updateIntent('tools', v)}
          errors={validationErrors.filter(e => e.loc[0] === 'tools')}
        />
      {:else}
        <div class="section-fallback">
          <pre class="section-raw">{JSON.stringify(intentState.tools, null, 2)}</pre>
        </div>
      {/if}

      <!-- 5. profile_definitions -->
      <SectionDoc section="intent.profile_definitions" />
      <ProfileDefinitionsEditor
        profiles={intentState.profile_definitions}
        localDefinitions={[]}
        onChange={(p) => updateIntent('profile_definitions', p)}
      />

      <!-- 6. configarr -->
      <SectionDoc section="intent.configarr" />
      <ConfigarrRawEditor
        value={intentState.configarr}
        onChange={(c) => updateIntent('configarr', c)}
      />
      {/key}
    </main>
  {/if}
{:else if activeConfig === 'arrconf'}
  <main class="page">
    <ReadOnlyInspector
      content={inspectorContent}
      filePath={CONFIG_FILE_PATHS.arrconf}
      {loadError}
    />
  </main>
{:else}
  <main class="page">
    <ReadOnlyInspector
      content={inspectorContent}
      filePath={CONFIG_FILE_PATHS.configarr}
      {loadError}
    />
  </main>
{/if}

{#if showSaveToast}
  <SaveToast onDismiss={() => (showSaveToast = false)} />
{/if}

<style>
  .page {
    max-width: 1280px;
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
  .section-fallback {
    margin-bottom: var(--space-md);
  }
  .section-raw {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    background: var(--code-bg);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: var(--space-md);
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-all;
    color: var(--ink-muted);
  }
</style>
