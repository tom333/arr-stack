<script lang="ts">
  import type { MediaCategory } from '../types';
  import CategoryRow from './CategoryRow.svelte';

  type Props = {
    categories: MediaCategory[];
    onChange: (next: MediaCategory[]) => void;
  };
  let { categories, onChange }: Props = $props();

  let newRow = $state<MediaCategory>({
    name: '',
    kind: 'series',
    profile: 'general',
    display: '',
    base_path: '',
  });

  function moveUp(idx: number) {
    if (idx === 0) return;
    const next = [...categories];
    [next[idx - 1], next[idx]] = [next[idx], next[idx - 1]];
    onChange(next);
  }
  function moveDown(idx: number) {
    if (idx === categories.length - 1) return;
    const next = [...categories];
    [next[idx], next[idx + 1]] = [next[idx + 1], next[idx]];
    onChange(next);
  }
  function deleteRow(idx: number) {
    onChange(categories.filter((_, i) => i !== idx));
  }
  function updateRow(idx: number, updated: MediaCategory) {
    const next = [...categories];
    next[idx] = updated;
    onChange(next);
  }
  function addRow() {
    if (!newRow.name.trim()) return;
    onChange([...categories, { ...newRow }]);
    newRow = { name: '', kind: 'series', profile: 'general', display: '', base_path: '' };
  }
  function resetRow() {
    newRow = { name: '', kind: 'series', profile: 'general', display: '', base_path: '' };
  }
</script>

<section class="categories">
  <h2>Catégories <span class="count">({categories.length})</span></h2>
  {#if categories.length === 0}
    <p class="empty">Aucune catégorie définie. Utilisez le formulaire ci-dessous pour en créer une.</p>
  {:else}
    <table>
      <thead>
        <tr>
          <th>Nom</th>
          <th>Type</th>
          <th>Profil</th>
          <th>Nom affiché</th>
          <th>Chemin sur disque</th>
          <th class="actions-header">Actions</th>
        </tr>
      </thead>
      <tbody>
        {#each categories as cat, idx (cat.name)}
          <CategoryRow
            category={cat}
            index={idx}
            total={categories.length}
            onMoveUp={() => moveUp(idx)}
            onMoveDown={() => moveDown(idx)}
            onDelete={() => deleteRow(idx)}
            onChange={(updated) => updateRow(idx, updated)}
          />
        {/each}
      </tbody>
    </table>
  {/if}

  <form class="add-row" onsubmit={(e) => { e.preventDefault(); addRow(); }}>
    <h3>Ajouter une catégorie</h3>
    <input
      type="text"
      class="mono"
      placeholder="nom (ex: series-zoe)"
      aria-label="Nom de la nouvelle catégorie"
      bind:value={newRow.name}
      required
    />
    <select bind:value={newRow.kind} aria-label="Type">
      <option value="series">📺 series</option>
      <option value="movies">🎬 movies</option>
    </select>
    <select bind:value={newRow.profile} aria-label="Profil">
      <option value="general">general — qualité standard</option>
      <option value="anime">anime — profile id=8 + tags</option>
      <option value="family">family — profile id=9, kids</option>
    </select>
    <input
      type="text"
      placeholder="Nom affiché (ex: Séries - Zoé)"
      aria-label="Nom affiché"
      bind:value={newRow.display}
    />
    <input
      type="text"
      class="mono"
      placeholder="/media/..."
      aria-label="Chemin sur disque"
      bind:value={newRow.base_path}
    />
    <button type="submit" class="add-btn">Ajouter</button>
    <button type="button" onclick={resetRow}>Réinitialiser</button>
  </form>
</section>

<style>
  .categories {
    padding: var(--space-lg);
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 4px;
    margin-bottom: var(--space-md);
  }
  h2 {
    font-size: 16px;
    font-weight: 600;
    margin: 0 0 var(--space-md) 0;
    display: inline-flex;
    align-items: baseline;
    gap: var(--space-xs);
  }
  .count {
    color: var(--ink-faint);
    font-weight: 400;
    font-size: 13px;
    font-family: 'IBM Plex Mono', monospace;
  }
  table {
    width: 100%;
    border-collapse: collapse;
  }
  th {
    text-align: left;
    border-bottom: 1px solid var(--border);
    padding: var(--space-sm) var(--space-md);
    font-size: 11px;
    font-weight: 500;
    color: var(--ink-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  th.actions-header { text-align: right; }
  .empty {
    color: var(--ink-faint);
    font-style: italic;
    padding: var(--space-md);
    text-align: center;
  }
  .add-row {
    display: grid;
    grid-template-columns: 1fr auto auto 1fr 1fr auto auto;
    gap: var(--space-sm);
    align-items: center;
    margin-top: var(--space-md);
    padding-top: var(--space-md);
    border-top: 1px dashed var(--border);
  }
  .add-row h3 {
    grid-column: 1 / -1;
    font-size: 13px;
    font-weight: 500;
    margin: 0;
    color: var(--ink-muted);
  }
  .add-btn {
    background: var(--accent);
    color: var(--accent-fg);
    border: 1px solid var(--accent);
    font-weight: 500;
  }
  .add-btn:hover:not(:disabled) {
    background: var(--accent);
    filter: brightness(1.08);
    border-color: var(--accent);
  }
</style>
