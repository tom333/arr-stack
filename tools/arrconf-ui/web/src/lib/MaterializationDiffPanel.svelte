<script lang="ts">
  type DiffLine = {
    text: string;
    cls: string;
    color: string;
    bg: string;
  };

  type Props = {
    arrconfDiff: string;
    configarrDiff: string;
    onConfirm: () => void;
    onCancel: () => void;
  };
  let { arrconfDiff, configarrDiff, onConfirm, onCancel }: Props = $props();

  function parseLines(diff: string): DiffLine[] {
    if (!diff) return [];
    return diff.split('\n').map((line) => {
      if (line.startsWith('+')) {
        return { text: line, cls: 'line-add', color: '#10b981', bg: 'rgba(16,185,129,0.08)' };
      } else if (line.startsWith('-')) {
        return { text: line, cls: 'line-del', color: 'var(--destructive)', bg: 'rgba(248,113,113,0.08)' };
      } else if (line.startsWith('@@')) {
        return { text: line, cls: 'line-hunk', color: 'var(--accent)', bg: 'var(--accent-soft)' };
      } else {
        return { text: line, cls: 'line-ctx', color: 'var(--ink-muted)', bg: 'transparent' };
      }
    });
  }

  const arrconfLines = $derived(parseLines(arrconfDiff));
  const configarrLines = $derived(parseLines(configarrDiff));
</script>

<div class="panel" role="dialog" aria-labelledby="mat-diff-heading" aria-modal="true">
  <h2 id="mat-diff-heading">Matérialisation — vérifier avant d'enregistrer</h2>

  <div class="file-section">
    <code class="file-label">arrconf.yml</code>
    {#if arrconfLines.length === 0}
      <pre class="diff-block"><em class="no-changes">Aucune modification</em></pre>
    {:else}
      <pre class="diff-block">{#each arrconfLines as line}<span class="diff-line" style="color:{line.color};background:{line.bg}">{line.text}
</span>{/each}</pre>
    {/if}
  </div>

  <div class="file-section">
    <code class="file-label">configarr.yml</code>
    {#if configarrLines.length === 0}
      <pre class="diff-block"><em class="no-changes">Aucune modification</em></pre>
    {:else}
      <pre class="diff-block">{#each configarrLines as line}<span class="diff-line" style="color:{line.color};background:{line.bg}">{line.text}
</span>{/each}</pre>
    {/if}
  </div>

  <div class="actions">
    <button type="button" onclick={onCancel}>Continuer l'édition</button>
    <button type="button" class="confirm-btn" onclick={onConfirm}>Confirmer et enregistrer</button>
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
  .file-section {
    margin-top: var(--space-md);
  }
  .file-label {
    display: block;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    font-weight: 400;
    color: var(--ink-muted);
    border-top: 1px solid var(--border);
    padding-top: var(--space-sm);
    margin: var(--space-md) 0 var(--space-sm) 0;
  }
  .diff-block {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    font-weight: 400;
    background: var(--code-bg);
    border: 1px solid var(--border);
    border-radius: 3px;
    padding: var(--space-sm) var(--space-md);
    overflow-y: auto;
    max-height: 300px;
    margin: 0;
    white-space: pre-wrap;
    word-break: break-all;
  }
  .diff-line {
    display: block;
  }
  .no-changes {
    color: var(--ink-faint);
    font-style: italic;
  }
  .actions {
    display: flex;
    gap: var(--space-sm);
    margin-top: var(--space-lg);
    padding-top: var(--space-md);
    border-top: 1px solid var(--border);
    justify-content: flex-end;
  }
  .confirm-btn {
    background: var(--accent);
    color: var(--accent-fg);
    border: 1px solid var(--accent);
    font-weight: 600;
  }
  .confirm-btn:hover:not(:disabled) {
    background: var(--accent);
    filter: brightness(1.08);
    border-color: var(--accent);
  }
</style>
