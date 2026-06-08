<script lang="ts">
  type Props = {
    content: string | null;
    filePath: string;
    loadError: string | null;
  };
  let { content, filePath, loadError }: Props = $props();
</script>

<div class="inspector-wrap">
  <div class="file-label">
    <code class="filepath">{filePath}</code>
    <span class="readonly-badge">généré — lecture seule</span>
  </div>

  {#if loadError}
    <div class="load-error" role="alert">
      Impossible de charger {filePath} — {loadError}. Vérifie le chemin du fichier puis réessaie.
    </div>
  {:else if content === null}
    <pre class="inspector">Chargement…</pre>
  {:else}
    <pre class="inspector">{content}</pre>
  {/if}
</div>

<style>
  .inspector-wrap {
    margin: var(--space-md) 0;
  }
  .file-label {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    margin-bottom: var(--space-sm);
  }
  .filepath {
    color: var(--ink-muted);
    font-size: 12px;
    background: transparent;
    padding: 0;
  }
  .readonly-badge {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    font-weight: 400;
    color: var(--ink-muted);
    background: var(--panel-alt);
    padding: 2px 10px;
    border-radius: 999px;
    white-space: nowrap;
  }
  pre.inspector {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    font-weight: 400;
    background: var(--code-bg);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: var(--space-lg);
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-all;
    margin: 0;
    color: var(--ink-muted);
  }
  .load-error {
    margin: var(--space-md) 0;
    padding: var(--space-md);
    background: var(--color-error-bg);
    border-left: 4px solid var(--color-destructive);
    border-radius: 4px;
    color: var(--color-destructive);
  }
</style>
