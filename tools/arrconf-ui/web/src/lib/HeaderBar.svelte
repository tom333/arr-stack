<script lang="ts">
  import type { SaveStatus } from '../types';
  import type { ActiveConfig } from '../constants';
  import ThemeToggle from './ThemeToggle.svelte';

  type Props = {
    filePath: string;
    diffCount: number;
    saveStatus: SaveStatus;
    onSaveClick: () => void;
    activeConfig?: ActiveConfig;
    onTabChange?: (next: ActiveConfig) => void;
  };
  let { filePath, diffCount, saveStatus, onSaveClick, activeConfig = 'arrconf', onTabChange }: Props = $props();

  const isDisabled = $derived(diffCount === 0 || saveStatus === 'saving');
  const buttonLabel = $derived(saveStatus === 'saving' ? 'Enregistrement…' : 'Enregistrer');
</script>

<header class="header">
  <div class="title-wrap">
    <h1 class="title">
      arrconf<span class="title-divider">/</span><span class="title-accent">editor</span>
    </h1>
    <code class="filepath">{filePath}</code>
    {#if onTabChange}
      <nav class="tab-bar" aria-label="Sélection du fichier de configuration">
        <button type="button" class="tab" class:tab-active={activeConfig === 'arrconf'}
          onclick={() => onTabChange('arrconf')}>arrconf.yml</button>
        <button type="button" class="tab" class:tab-active={activeConfig === 'configarr'}
          onclick={() => onTabChange('configarr')}>configarr.yml</button>
      </nav>
    {/if}
  </div>
  <div class="actions">
    {#if diffCount > 0}
      <span class="diff-chip" aria-live="polite">
        {diffCount} modification{diffCount === 1 ? '' : 's'} en attente
      </span>
    {/if}
    <ThemeToggle />
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
    background: var(--panel);
    border-bottom: 1px solid var(--border);
    box-shadow: var(--shadow-sm);
    z-index: 10;
    backdrop-filter: blur(8px);
  }
  .title-wrap {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }
  .title {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    line-height: 1.2;
    letter-spacing: -0.015em;
    color: var(--ink);
  }
  .title-divider {
    color: var(--ink-faint);
    font-weight: 400;
    margin: 0 2px;
  }
  .title-accent {
    color: var(--accent);
    font-weight: 600;
  }
  .filepath {
    color: var(--ink-muted);
    font-size: 12px;
    background: transparent;
    padding: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .actions {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
  }
  .diff-chip {
    color: var(--accent);
    background: var(--accent-soft);
    font-size: 12px;
    padding: 2px 10px;
    border-radius: 999px;
    font-weight: 500;
    font-family: 'IBM Plex Mono', monospace;
  }
  .save-btn {
    background: var(--accent);
    color: var(--accent-fg);
    border: 1px solid var(--accent);
    padding: var(--space-sm) var(--space-md);
    border-radius: 3px;
    font-size: 13px;
    font-weight: 500;
    letter-spacing: 0.01em;
  }
  .save-btn:hover:not(:disabled) {
    background: var(--accent);
    filter: brightness(1.08);
    border-color: var(--accent);
  }
  /* .save-btn:disabled inherits opacity from the generic button:disabled in app.css. */
  .tab-bar { display: flex; gap: 2px; margin-top: var(--space-xs); }
  .tab {
    font-size: 12px; font-family: 'IBM Plex Mono', monospace;
    padding: 2px 10px; border-radius: 3px; border: 1px solid var(--border);
    background: transparent; color: var(--ink-muted); cursor: pointer;
  }
  .tab-active {
    background: var(--accent-soft); color: var(--accent);
    border-color: var(--accent); font-weight: 500;
  }
</style>
