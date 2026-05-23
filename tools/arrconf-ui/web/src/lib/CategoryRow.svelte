<script lang="ts">
  import type { MediaCategory } from '../types';
  import SuggestArrBadge from './SuggestArrBadge.svelte';

  type Props = {
    category: MediaCategory;
    index: number;
    total: number;
    onMoveUp: () => void;
    onMoveDown: () => void;
    onDelete: () => void;
    onChange: (next: MediaCategory) => void;
  };
  let { category, index, total, onMoveUp, onMoveDown, onDelete, onChange }: Props = $props();

  let confirmingDelete = $state(false);

  function handleField<K extends keyof MediaCategory>(key: K, value: MediaCategory[K]) {
    onChange({ ...category, [key]: value });
  }

  // Hover hints on the dropdowns (rendered as native title= tooltips).
  const KIND_HINTS: Record<MediaCategory['kind'], string> = {
    series: 'Géré par Sonarr — tag, root folder, download client',
    movies: 'Géré par Radarr — tag, root folder, download client',
  };
  const PROFILE_HINTS: Record<MediaCategory['profile'], string> = {
    general: 'Qualité standard (HD-720p/1080p, default profileId=6)',
    anime: 'Profile anime (id=8) + animeTags Seerr',
    family: 'Profile family (id=9), kids-safe content',
  };
</script>

<tr class:alt={index % 2 === 1}>
  <td class="cell-name">
    <input
      type="text"
      class="mono"
      value={category.name}
      aria-label="Nom de la catégorie"
      oninput={(e) => handleField('name', (e.target as HTMLInputElement).value)}
    />
  </td>
  <td class="cell-kind">
    <select
      value={category.kind}
      aria-label="Type (series ou movies)"
      title={KIND_HINTS[category.kind]}
      onchange={(e) => handleField('kind', (e.target as HTMLSelectElement).value as MediaCategory['kind'])}
    >
      <option value="series">📺 series</option>
      <option value="movies">🎬 movies</option>
    </select>
  </td>
  <td class="cell-profile">
    <select
      value={category.profile}
      aria-label="Profil qualité (general, anime, family)"
      title={PROFILE_HINTS[category.profile]}
      onchange={(e) => handleField('profile', (e.target as HTMLSelectElement).value as MediaCategory['profile'])}
    >
      <option value="general">general — qualité standard</option>
      <option value="anime">anime — profile id=8 + tags</option>
      <option value="family">family — profile id=9, kids</option>
    </select>
  </td>
  <td class="cell-display">
    <input
      type="text"
      value={category.display}
      aria-label="Nom affiché"
      oninput={(e) => handleField('display', (e.target as HTMLInputElement).value)}
    />
  </td>
  <td class="cell-base-path">
    <div class="base-path-wrap">
      <input
        type="text"
        class="mono"
        value={category.base_path}
        aria-label="Chemin sur disque"
        oninput={(e) => handleField('base_path', (e.target as HTMLInputElement).value)}
      />
      <SuggestArrBadge path={`categories[${index}].base_path`} categoryName={category.name} />
    </div>
  </td>
  <td class="actions">
    {#if confirmingDelete}
      <button
        type="button"
        class="confirm-del"
        onclick={() => {
          confirmingDelete = false;
          onDelete();
        }}
      >Confirmer</button>
      <button type="button" onclick={() => (confirmingDelete = false)}>Annuler</button>
    {:else}
      <button
        type="button"
        disabled={index === 0}
        aria-label={`Monter ${category.name}`}
        title={`Monter ${category.name}`}
        onclick={onMoveUp}
      >↑</button>
      <button
        type="button"
        disabled={index === total - 1}
        aria-label={`Descendre ${category.name}`}
        title={`Descendre ${category.name}`}
        onclick={onMoveDown}
      >↓</button>
      <button
        type="button"
        class="delete-btn"
        aria-label={`Supprimer la catégorie ${category.name}`}
        title={`Supprimer ${category.name}`}
        onclick={() => (confirmingDelete = true)}
      >✕</button>
    {/if}
  </td>
</tr>

<style>
  tr.alt { background: var(--panel-alt); }
  td {
    padding: var(--space-sm) var(--space-md);
    vertical-align: middle;
    border-bottom: 1px solid var(--border);
  }
  td input[type="text"],
  td select {
    width: 100%;
  }

  /* Per-column width hints — dropdowns wide enough to show full text. */
  .cell-name { min-width: 140px; }
  .cell-kind { min-width: 140px; }
  .cell-kind select { min-width: 130px; }
  .cell-profile { min-width: 240px; }
  .cell-profile select { min-width: 230px; }
  .cell-display { min-width: 180px; }
  .cell-base-path { min-width: 240px; }

  .base-path-wrap {
    display: flex;
    align-items: center;
    gap: var(--space-xs);
  }

  td.actions {
    display: flex;
    gap: var(--space-xs);
    align-items: center;
    justify-content: flex-end;
  }
  td.actions button {
    min-width: 32px;
    min-height: 32px;
    padding: 0 var(--space-xs);
    color: var(--ink-muted);
  }
  td.actions button:hover:not(:disabled) {
    color: var(--ink);
  }
  td.actions .delete-btn:hover {
    color: var(--destructive);
  }
  td.actions .confirm-del {
    background: var(--destructive);
    color: var(--destructive-fg);
    border-color: var(--destructive);
  }
  td.actions .confirm-del:hover:not(:disabled) {
    background: var(--destructive);
    filter: brightness(0.92);
    border-color: var(--destructive);
  }
</style>
