<script lang="ts">
  import type { SaveStatus } from '../types';

  type Props = {
    filePath: string;
    diffCount: number;
    saveStatus: SaveStatus;
    onSaveClick: () => void;
  };
  let { filePath, diffCount, saveStatus, onSaveClick }: Props = $props();

  const isDisabled = $derived(diffCount === 0 || saveStatus === 'saving');
  const buttonLabel = $derived(saveStatus === 'saving' ? 'Saving…' : 'Save config');
</script>

<header class="header">
  <div class="title-wrap">
    <h1 class="title">arrconf editor</h1>
    <code class="filepath">{filePath}</code>
  </div>
  <div class="actions">
    {#if diffCount > 0}
      <span class="diff-chip">
        {diffCount} unsaved change{diffCount === 1 ? '' : 's'}
      </span>
    {/if}
    <button type="button" class="save-btn" disabled={isDisabled} onclick={onSaveClick}>
      {buttonLabel}
    </button>
  </div>
</header>

<style>
  .header {
    position: sticky;
    top: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-md) var(--space-lg);
    background: var(--color-panel);
    border-bottom: 1px solid var(--color-border);
    z-index: 10;
  }
  .title-wrap { display: flex; flex-direction: column; gap: 2px; }
  .title { margin: 0; font-size: 20px; font-weight: 600; line-height: 1.2; }
  .filepath { color: var(--color-muted); font-size: 12px; }
  .actions { display: flex; align-items: center; gap: var(--space-sm); }
  .diff-chip {
    color: var(--color-muted);
    font-size: 12px;
  }
  .save-btn {
    background: var(--color-accent);
    color: var(--color-accent-fg);
    border: none;
    padding: var(--space-sm) var(--space-md);
    border-radius: 4px;
    font-size: 14px;
  }
  .save-btn:disabled {
    background: var(--color-accent);
    /* opacity rule from app.css applies */
  }
</style>
