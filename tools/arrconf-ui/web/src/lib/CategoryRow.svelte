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
</script>

<tr class:alt={index % 2 === 1}>
  <td>
    <input
      type="text"
      value={category.name}
      oninput={(e) => handleField('name', (e.target as HTMLInputElement).value)}
    />
  </td>
  <td>
    <select
      value={category.kind}
      onchange={(e) => handleField('kind', (e.target as HTMLSelectElement).value as MediaCategory['kind'])}
    >
      <option value="series">series</option>
      <option value="movies">movies</option>
    </select>
  </td>
  <td>
    <select
      value={category.profile}
      onchange={(e) => handleField('profile', (e.target as HTMLSelectElement).value as MediaCategory['profile'])}
    >
      <option value="general">general</option>
      <option value="anime">anime</option>
      <option value="family">family</option>
    </select>
  </td>
  <td>
    <input
      type="text"
      value={category.display}
      oninput={(e) => handleField('display', (e.target as HTMLInputElement).value)}
    />
  </td>
  <td>
    <input
      type="text"
      value={category.base_path}
      oninput={(e) => handleField('base_path', (e.target as HTMLInputElement).value)}
    />
    <SuggestArrBadge path={`categories[${index}].base_path`} categoryName={category.name} />
  </td>
  <td class="actions">
    {#if confirmingDelete}
      <button type="button" class="confirm-del" onclick={() => { confirmingDelete = false; onDelete(); }}>
        Confirm
      </button>
      <button type="button" onclick={() => (confirmingDelete = false)}>Keep row</button>
    {:else}
      <button
        type="button"
        disabled={index === 0}
        aria-label={`Move ${category.name} up`}
        onclick={onMoveUp}
      >↑</button>
      <button
        type="button"
        disabled={index === total - 1}
        aria-label={`Move ${category.name} down`}
        onclick={onMoveDown}
      >↓</button>
      <button
        type="button"
        class="delete-btn"
        aria-label={`Delete category ${category.name}`}
        onclick={() => (confirmingDelete = true)}
      >✕</button>
    {/if}
  </td>
</tr>

<style>
  tr.alt { background: var(--color-row-alt); }
  td { padding: var(--space-sm) var(--space-md); vertical-align: middle; }
  td input[type="text"], td select { width: 100%; }
  td.actions { display: flex; gap: var(--space-xs); align-items: center; }
  td.actions button {
    min-width: 32px;
    min-height: 32px;
    padding: var(--space-xs);
    color: var(--color-muted);
  }
  td.actions .delete-btn:hover { color: var(--color-destructive); }
  td.actions .confirm-del { background: var(--color-destructive); color: var(--color-destructive-fg); border: none; }
</style>
