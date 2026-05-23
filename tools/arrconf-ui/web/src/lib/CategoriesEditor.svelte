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
  <h2>Categories</h2>
  {#if categories.length === 0}
    <p class="empty">No categories defined. Use the form below to add one.</p>
  {:else}
    <table>
      <thead>
        <tr>
          <th>Name</th>
          <th>Kind</th>
          <th>Profile</th>
          <th>Display</th>
          <th>Base path</th>
          <th>Actions</th>
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
    <h3>Add category</h3>
    <input
      type="text"
      placeholder="name (e.g., series-zoe)"
      bind:value={newRow.name}
      required
    />
    <select bind:value={newRow.kind}>
      <option value="series">series</option>
      <option value="movies">movies</option>
    </select>
    <select bind:value={newRow.profile}>
      <option value="general">general</option>
      <option value="anime">anime</option>
      <option value="family">family</option>
    </select>
    <input type="text" placeholder="display" bind:value={newRow.display} />
    <input type="text" placeholder="/media/..." bind:value={newRow.base_path} />
    <button type="submit" class="add-btn">Add</button>
    <button type="button" onclick={resetRow}>Reset</button>
  </form>
</section>

<style>
  .categories { padding: var(--space-lg); }
  h2 { font-size: 16px; font-weight: 600; margin: 0 0 var(--space-md) 0; }
  table { width: 100%; border-collapse: collapse; }
  th {
    text-align: left;
    border-bottom: 1px solid var(--color-border);
    padding: var(--space-sm) var(--space-md);
    font-size: 14px;
    font-weight: 600;
    font-size: 12px;
    color: var(--color-muted);
  }
  .empty { color: var(--color-muted); padding: var(--space-md); }
  .add-row {
    display: grid;
    grid-template-columns: 1fr auto auto 1fr 1fr auto auto;
    gap: var(--space-sm);
    align-items: center;
    margin-top: var(--space-md);
    padding-top: var(--space-md);
    border-top: 1px solid var(--color-border);
  }
  .add-row h3 { grid-column: 1 / -1; font-size: 14px; font-weight: 600; margin: 0; }
  .add-btn { background: var(--color-accent); color: var(--color-accent-fg); border: none; }
</style>
