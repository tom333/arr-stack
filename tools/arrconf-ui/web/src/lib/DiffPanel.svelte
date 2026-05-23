<script lang="ts">
  import type { SemanticDiff } from '../types';

  type Props = {
    diff: SemanticDiff;
    onConfirm: () => void;
    onCancel: () => void;
  };
  let { diff, onConfirm, onCancel }: Props = $props();

  const catChange = $derived(diff.categories as { added: string[]; modified: string[]; removed: string[] } | undefined);

  const changedSections = $derived(
    Object.entries(diff)
      .filter(([k, v]) => {
        if (k === 'categories') {
          const c = v as { added: string[]; modified: string[]; removed: string[] };
          return c.added.length + c.modified.length + c.removed.length > 0;
        }
        return (v as { changed_fields: string[] }).changed_fields.length > 0;
      }),
  );
</script>

<div class="panel" role="dialog" aria-labelledby="diff-panel-heading" aria-modal="true">
  <h2 id="diff-panel-heading">Pending changes — review before saving</h2>

  {#if changedSections.length === 0}
    <p class="empty">No pending changes detected.</p>
  {/if}

  {#if catChange && (catChange.added.length || catChange.modified.length || catChange.removed.length)}
    <section>
      <h3>Categories</h3>
      <ul>
        {#each catChange.added as n}
          <li>+ added: <code>{n}</code></li>
        {/each}
        {#each catChange.modified as n}
          <li>~ modified: <code>{n}</code></li>
        {/each}
        {#each catChange.removed as n}
          <li>- removed: <code>{n}</code></li>
        {/each}
      </ul>
    </section>
  {/if}

  {#each changedSections.filter(([k]) => k !== 'categories') as [sectionKey, sectionDiff]}
    {@const fields = (sectionDiff as { changed_fields: string[] }).changed_fields}
    {#if fields.length > 0}
      <section>
        <h3>{sectionKey}</h3>
        <ul>
          {#each fields as path}
            <li>~ <code>{path}</code></li>
          {/each}
        </ul>
      </section>
    {/if}
  {/each}

  <div class="actions">
    <button type="button" class="confirm-btn" onclick={onConfirm}>Confirm & Save</button>
    <button type="button" onclick={onCancel}>Keep editing</button>
  </div>
</div>

<style>
  .panel {
    background: var(--color-panel);
    border: 1px solid var(--color-border);
    border-radius: 4px;
    padding: var(--space-lg);
    margin: var(--space-md) var(--space-lg);
  }
  h2 { font-size: 16px; font-weight: 600; margin: 0 0 var(--space-md) 0; }
  h3 { font-size: 14px; font-weight: 600; margin: var(--space-md) 0 var(--space-sm) 0; }
  ul { margin: 0; padding-left: var(--space-md); }
  li { padding: var(--space-xs) 0; font-size: 14px; }
  .empty { color: var(--color-muted); }
  .actions { display: flex; gap: var(--space-sm); margin-top: var(--space-md); }
  .confirm-btn { background: var(--color-accent); color: var(--color-accent-fg); border: none; }
</style>
