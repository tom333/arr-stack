<script lang="ts">
  import type { ProfileDefinition, CustomFormatRef } from '../types';
  import {
    PROFILE_BODY_LABEL,
    SCORE_OVERRIDE_PLACEHOLDER,
  } from '../i18n/fr';
  import TrashCFPicker from './TrashCFPicker.svelte';
  import TrashQPPicker from './TrashQPPicker.svelte';

  type CustomFormatEntry = {
    trash_ids: string[];
    assign_scores_to: { name: string; score?: number }[];
  };

  type Props = {
    profileName: string;
    profile: ProfileDefinition;
    app: 'sonarr' | 'radarr';
    localDefinitions: { trash_id: string; name: string }[];
    onChange: (next: ProfileDefinition) => void;
    onDelete: () => void;
  };
  let { profileName, profile, app, localDefinitions, onChange, onDelete }: Props = $props();

  // svelte-ignore state_referenced_locally
  let isOpen = $state(false);
  let confirmDelete = $state(false);

  // Body textarea: serialize body to JSON (no YAML lib bundled).
  let bodyRaw = $state(JSON.stringify(profile.body, null, 2));
  let bodyParseError = $state<string | null>(null);

  function handleBodyInput(e: Event) {
    const text = (e.currentTarget as HTMLTextAreaElement).value;
    bodyRaw = text;
    try {
      const parsed = JSON.parse(text) as Record<string, unknown>;
      bodyParseError = null;
      onChange({ ...profile, body: parsed });
    } catch {
      bodyParseError = 'JSON invalide — les modifications ne seront pas enregistrées.';
    }
  }

  // CF chip: label resolution.
  function labelFor(trashId: string): string {
    const local = localDefinitions.find((d) => d.trash_id === trashId);
    if (local) return local.name;
    return trashId;
  }

  // Remove a ref by index.
  function removeCFRef(idx: number) {
    const next = profile.custom_formats.filter((_, i) => i !== idx);
    onChange({ ...profile, custom_formats: next });
  }

  // Update score for a ref by index.
  function updateScore(idx: number, raw: string) {
    const parsed = raw === '' ? null : Number(raw);
    const next = profile.custom_formats.map((r, i) =>
      i === idx ? { ...r, score: parsed } : r
    );
    onChange({ ...profile, custom_formats: next });
  }

  // Transform CustomFormatRef[] → CustomFormatEntry[] for TrashCFPicker.
  const pickerCFs = $derived(
    profile.custom_formats.map((ref) => ({
      trash_ids: ref.trash_ids,
      assign_scores_to: [{ name: profileName, ...(ref.score !== null ? { score: ref.score } : {}) }],
    }))
  );

  function handleCFChange(next: CustomFormatEntry[]) {
    const refs: CustomFormatRef[] = next.map((e) => ({
      trash_ids: e.trash_ids,
      score: e.assign_scores_to[0]?.score ?? null,
    }));
    onChange({ ...profile, custom_formats: refs });
  }

  // TrashQPPicker: merge selected QP fields into profile.body.
  const qpProfiles = $derived(
    profile.body && typeof profile.body === 'object' ? [profile.body] : []
  );

  function handleQPChange(next: Record<string, unknown>[]) {
    if (next.length > 0) {
      const merged = { ...profile.body, ...next[next.length - 1] };
      onChange({ ...profile, body: merged });
      bodyRaw = JSON.stringify(merged, null, 2);
    }
  }
</script>

<details
  class="profile-card"
  open={isOpen}
  ontoggle={(e) => (isOpen = (e.currentTarget as HTMLDetailsElement).open)}
>
  <summary class="card-summary">
    <svg class="chevron" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <polyline points="9 6 15 12 9 18"/>
    </svg>
    <span class="profile-name">profil : {profileName}</span>

    {#if confirmDelete}
      <span class="delete-confirm-inline" role="group">
        <span class="delete-question">Supprimer {profileName} ?</span>
        <button
          type="button"
          class="btn-cancel-delete"
          onclick={(e) => { e.preventDefault(); confirmDelete = false; }}
        >Annuler la suppression</button>
        <button
          type="button"
          class="btn-confirm-delete"
          onclick={(e) => { e.preventDefault(); onDelete(); }}
        >Supprimer le profil</button>
      </span>
    {:else}
      <button
        type="button"
        class="btn-delete"
        onclick={(e) => { e.preventDefault(); confirmDelete = true; }}
        aria-label="Supprimer le profil {profileName}"
      >✕</button>
    {/if}
  </summary>

  <div class="card-body">
    <!-- Body textarea -->
    <div class="field-group">
      <label class="field-label" for="body-{profileName}">{PROFILE_BODY_LABEL}</label>
      <textarea
        id="body-{profileName}"
        class="raw-editor"
        value={bodyRaw}
        oninput={handleBodyInput}
        rows={8}
        spellcheck="false"
      ></textarea>
      {#if bodyParseError}
        <span class="parse-error">{bodyParseError}</span>
      {/if}
    </div>

    <!-- CF chips -->
    <div class="field-group">
      <span class="field-label">custom_formats</span>
      <div class="cf-chips">
        {#each profile.custom_formats as ref, idx}
          {#each ref.trash_ids as id}
            <div class="cf-chip">
              <span class="cf-label">{labelFor(id)}</span>
              <input
                type="number"
                class="score-input"
                value={ref.score ?? ''}
                placeholder={SCORE_OVERRIDE_PLACEHOLDER}
                aria-label="Score pour {labelFor(id)}"
                oninput={(e) => updateScore(idx, (e.currentTarget as HTMLInputElement).value)}
              />
              <button
                type="button"
                class="chip-delete"
                onclick={() => removeCFRef(idx)}
                aria-label="Retirer le format {labelFor(id)}"
              >✕</button>
            </div>
          {/each}
        {/each}
      </div>
    </div>

    <!-- TrashCFPicker: per-profile -->
    <TrashCFPicker
      {app}
      existingCustomFormats={pickerCFs}
      {localDefinitions}
      profileNames={[profileName]}
      onChange={handleCFChange}
    />

    <!-- TrashQPPicker: feeds into profile body -->
    <TrashQPPicker
      {app}
      existingProfiles={qpProfiles}
      onChange={handleQPChange}
    />
  </div>
</details>

<style>
  .profile-card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 4px;
    margin-bottom: var(--space-sm);
  }

  .card-summary {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    padding: var(--space-sm) var(--space-md);
    cursor: pointer;
    user-select: none;
    list-style: none;
    color: var(--ink-muted);
  }
  .card-summary::-webkit-details-marker { display: none; }

  .chevron {
    transition: transform 200ms ease-out;
    flex-shrink: 0;
    opacity: 0.7;
  }
  details[open] .chevron { transform: rotate(90deg); }

  .profile-name {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    font-weight: 400;
    color: var(--ink);
    flex: 1;
  }

  .btn-delete {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--ink-muted);
    font-size: 12px;
    padding: 2px var(--space-xs);
    line-height: 1;
    margin-left: auto;
    flex-shrink: 0;
  }
  .btn-delete:hover {
    color: var(--destructive);
  }

  .delete-confirm-inline {
    display: inline-flex;
    align-items: center;
    gap: var(--space-xs);
    margin-left: auto;
    flex-shrink: 0;
  }

  .delete-question {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 12px;
    font-weight: 400;
    color: var(--destructive);
  }

  .btn-cancel-delete {
    background: none;
    border: 1px solid var(--border);
    border-radius: 3px;
    cursor: pointer;
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 12px;
    font-weight: 400;
    color: var(--ink-muted);
    padding: 2px var(--space-xs);
  }
  .btn-cancel-delete:hover {
    border-color: var(--border-strong);
  }

  .btn-confirm-delete {
    background: none;
    border: 1px solid var(--destructive);
    border-radius: 3px;
    cursor: pointer;
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 12px;
    font-weight: 400;
    color: var(--destructive);
    padding: 2px var(--space-xs);
  }
  .btn-confirm-delete:hover {
    background: var(--destructive);
    color: var(--panel);
  }

  .card-body {
    padding: var(--space-md);
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
    border-top: 1px solid var(--border);
  }

  .field-group {
    display: flex;
    flex-direction: column;
    gap: var(--space-xs);
  }

  .field-label {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 14px;
    font-weight: 600;
    color: var(--ink);
  }

  .raw-editor {
    width: 100%;
    min-height: 120px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    background: var(--code-bg);
    border: 1px solid var(--border);
    border-radius: 3px;
    padding: var(--space-sm) var(--space-md);
    color: var(--ink);
    resize: vertical;
    box-sizing: border-box;
  }
  .raw-editor:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 3px var(--accent-soft);
  }

  .parse-error {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    color: var(--destructive);
  }

  .cf-chips {
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

  .score-input {
    width: 5em;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 3px;
    color: var(--ink);
    padding: 1px var(--space-xs);
    text-align: right;
  }
  .score-input:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 2px var(--accent-soft);
  }

  .chip-delete {
    background: none;
    border: none;
    color: var(--ink-muted);
    cursor: pointer;
    font-size: 11px;
    padding: 0 2px;
    line-height: 1;
  }
  .chip-delete:hover {
    color: var(--destructive);
  }
</style>
