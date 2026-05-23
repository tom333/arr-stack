<script lang="ts">
  /**
   * Section-level documentation card. Renders above each top-level section
   * (categories + 6 app sections) with operator-facing explanations.
   *
   * Content lives in src/i18n/fr.ts (SECTION_DOCS keyed by section name).
   * The component is collapsed by default to keep the form dense; the operator
   * clicks the chevron to expand the documentation when needed.
   */

  import { SECTION_DOCS } from '../i18n/fr';

  type Props = {
    section: string; // "categories" | "sonarr" | "radarr" | ...
    /** Default open on first render? Useful for the categories section. */
    defaultOpen?: boolean;
  };
  let { section, defaultOpen = false }: Props = $props();

  const doc = $derived(SECTION_DOCS[section]);
  // svelte-ignore state_referenced_locally
  let isOpen = $state(defaultOpen);

  // Tiny markdown: paragraph splits on \n\n; **bold** → <strong>; `code` → <code>.
  function renderInline(text: string): string {
    // Order matters: escape HTML first so user-provided strings can't inject markup.
    const escaped = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    return escaped
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/`([^`]+)`/g, '<code>$1</code>');
  }

  const paragraphs = $derived(
    doc ? doc.body.split('\n\n').map((p) => renderInline(p.trim())) : [],
  );
</script>

{#if doc}
  <details class="section-doc" open={isOpen} ontoggle={(e) => (isOpen = (e.currentTarget as HTMLDetailsElement).open)}>
    <summary>
      <svg class="chevron" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <polyline points="9 6 15 12 9 18"/>
      </svg>
      <span class="doc-title">{doc.title}</span>
      <span class="doc-toggle-hint">{isOpen ? 'masquer' : 'à propos de cette section'}</span>
    </summary>
    <div class="doc-body">
      {#each paragraphs as p}
        <p>{@html p}</p>
      {/each}
    </div>
  </details>
{/if}

<style>
  .section-doc {
    background: var(--doc-bg);
    border-left: 3px solid var(--doc-border);
    border-top: 1px solid var(--border);
    border-right: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
    border-radius: 0 3px 3px 0;
    margin-bottom: var(--space-sm);
    padding: 0;
    transition: background-color 200ms ease-out;
  }

  summary {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    padding: var(--space-sm) var(--space-md);
    cursor: pointer;
    user-select: none;
    list-style: none;
    color: var(--ink-muted);
  }
  summary::-webkit-details-marker { display: none; }

  .chevron {
    transition: transform 200ms ease-out;
    flex-shrink: 0;
    opacity: 0.7;
  }
  details[open] .chevron { transform: rotate(90deg); }

  .doc-title {
    font-weight: 500;
    color: var(--ink);
    font-size: 13px;
    letter-spacing: 0.02em;
  }

  .doc-toggle-hint {
    margin-left: auto;
    font-size: 11px;
    color: var(--ink-faint);
    font-style: italic;
  }

  .doc-body {
    padding: 0 var(--space-md) var(--space-md) calc(var(--space-md) + 14px + var(--space-sm));
    color: var(--ink-muted);
    font-size: 13px;
    line-height: 1.65;
  }

  .doc-body p { margin: 0 0 var(--space-sm) 0; }
  .doc-body p:last-child { margin-bottom: 0; }

  .doc-body :global(strong) {
    color: var(--ink);
    font-weight: 500;
  }

  .doc-body :global(code) {
    background: var(--code-bg);
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 11.5px;
    font-family: 'IBM Plex Mono', ui-monospace, monospace;
  }
</style>
