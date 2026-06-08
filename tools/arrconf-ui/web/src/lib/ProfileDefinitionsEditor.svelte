<script lang="ts">
  import type { ProfileDefinition } from '../types';
  import {
    ADD_PROFILE_TEXT,
    PROFILE_NAME_PLACEHOLDER,
  } from '../i18n/fr';
  import ProfileCard from './ProfileCard.svelte';

  type Props = {
    profiles: Record<string, ProfileDefinition>;
    localDefinitions: { trash_id: string; name: string }[];
    onChange: (next: Record<string, ProfileDefinition>) => void;
  };
  let { profiles, localDefinitions, onChange }: Props = $props();

  let newProfileName = $state('');
  let addError = $state<string | null>(null);

  // Infer app from profile name: profiles containing 'radarr', 'movie', 'films' → radarr;
  // 'sonarr', 'series', 'anime', 'tv' → sonarr; ambiguous → sonarr by default.
  function inferApp(profileName: string): 'sonarr' | 'radarr' {
    const lower = profileName.toLowerCase();
    if (lower.includes('radarr') || lower.includes('movie') || lower.includes('film')) {
      return 'radarr';
    }
    return 'sonarr';
  }

  function addProfile() {
    const name = newProfileName.trim();
    if (!name) { addError = 'Le nom du profil est requis.'; return; }
    if (Object.prototype.hasOwnProperty.call(profiles, name)) {
      addError = `Le profil "${name}" existe déjà.`;
      return;
    }
    addError = null;
    onChange({ ...profiles, [name]: { body: {}, custom_formats: [] } });
    newProfileName = '';
  }

  function deleteProfile(name: string) {
    const next = { ...profiles };
    delete next[name];
    onChange(next);
  }

  function updateProfile(name: string, updated: ProfileDefinition) {
    onChange({ ...profiles, [name]: updated });
  }
</script>

<div class="profile-definitions-editor">
  {#each Object.entries(profiles) as [name, profile] (name)}
    <ProfileCard
      profileName={name}
      {profile}
      app={inferApp(name)}
      {localDefinitions}
      onChange={(updated) => updateProfile(name, updated)}
      onDelete={() => deleteProfile(name)}
    />
  {/each}

  <div class="add-profile-row">
    <input
      type="text"
      class="profile-name-input"
      placeholder={PROFILE_NAME_PLACEHOLDER}
      bind:value={newProfileName}
      aria-label="Nom du nouveau profil"
      onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addProfile(); } }}
    />
    <button type="button" class="array-add" onclick={addProfile}>
      {ADD_PROFILE_TEXT}
    </button>
  </div>
  {#if addError}
    <span class="add-error">{addError}</span>
  {/if}
</div>

<style>
  .profile-definitions-editor {
    display: flex;
    flex-direction: column;
    gap: var(--space-xs);
  }

  .add-profile-row {
    display: flex;
    gap: var(--space-sm);
    align-items: center;
    margin-top: var(--space-sm);
  }

  .profile-name-input {
    flex: 1;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--ink);
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 14px;
    font-weight: 400;
    padding: var(--space-xs) var(--space-sm);
  }
  .profile-name-input:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 3px var(--accent-soft);
  }

  .array-add {
    align-self: flex-start;
    background: var(--accent-soft);
    border: 1px solid var(--accent);
    border-radius: 4px;
    color: var(--accent-fg);
    cursor: pointer;
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 14px;
    font-weight: 400;
    padding: var(--space-xs) var(--space-sm);
    white-space: nowrap;
  }
  .array-add:hover {
    background: var(--accent);
  }

  .add-error {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    color: var(--destructive);
    margin-top: var(--space-xs);
  }
</style>
