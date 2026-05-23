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
  <h2 id="diff-panel-heading">Modifications en attente — vérifie avant d'enregistrer</h2>

  {#if changedSections.length === 0}
    <p class="empty">Aucune modification détectée.</p>
  {/if}

  {#if catChange && (catChange.added.length || catChange.modified.length || catChange.removed.length)}
    <section>
      <h3>Catégories</h3>
      <ul>
        {#each catChange.added as n}
          <li class="op-add"><span class="op">+</span> ajoutée : <code>{n}</code></li>
        {/each}
        {#each catChange.modified as n}
          <li class="op-mod"><span class="op">~</span> modifiée : <code>{n}</code></li>
        {/each}
        {#each catChange.removed as n}
          <li class="op-del"><span class="op">−</span> supprimée : <code>{n}</code></li>
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
            <li class="op-mod"><span class="op">~</span> <code>{path}</code></li>
          {/each}
        </ul>
      </section>
    {/if}
  {/each}

  <div class="actions">
    <button type="button" class="confirm-btn" onclick={onConfirm}>Confirmer et enregistrer</button>
    <button type="button" onclick={onCancel}>Continuer l'édition</button>
  </div>
</div>

<style>
  .panel {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: var(--space-lg);
    margin: var(--space-md) 0;
    box-shadow: var(--shadow-md);
  }
  h2 {
    font-size: 16px;
    font-weight: 600;
    margin: 0 0 var(--space-md) 0;
    color: var(--ink);
  }
  h3 {
    font-size: 13px;
    font-weight: 500;
    margin: var(--space-md) 0 var(--space-sm) 0;
    text-transform: lowercase;
    color: var(--ink-muted);
    letter-spacing: 0.04em;
  }
  ul {
    margin: 0;
    padding-left: 0;
    list-style: none;
  }
  li {
    padding: var(--space-xs) 0;
    font-size: 13px;
    display: flex;
    gap: var(--space-sm);
    align-items: center;
  }
  .op {
    display: inline-block;
    width: 18px;
    text-align: center;
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 600;
  }
  .op-add .op { color: #10b981; }    /* emerald — additions */
  .op-mod .op { color: var(--accent); } /* cyan — modifications */
  .op-del .op { color: var(--destructive); }
  .empty {
    color: var(--ink-faint);
    font-style: italic;
  }
  .actions {
    display: flex;
    gap: var(--space-sm);
    margin-top: var(--space-lg);
    padding-top: var(--space-md);
    border-top: 1px solid var(--border);
  }
  .confirm-btn {
    background: var(--accent);
    color: var(--accent-fg);
    border: 1px solid var(--accent);
    font-weight: 500;
  }
  .confirm-btn:hover:not(:disabled) {
    background: var(--accent);
    filter: brightness(1.08);
    border-color: var(--accent);
  }
</style>
