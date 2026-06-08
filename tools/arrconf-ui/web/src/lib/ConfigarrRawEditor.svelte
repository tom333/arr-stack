<script lang="ts">
  import {
    CONFIGARR_RAW_LABEL,
    CONFIGARR_RAW_HELPER,
  } from '../i18n/fr';

  type Props = {
    value: Record<string, unknown>;
    onChange: (next: Record<string, unknown>) => void;
  };
  let { value, onChange }: Props = $props();

  // Serialize to JSON (no YAML lib bundled — JSON.stringify is the minimal representation).
  let rawText = $state(JSON.stringify(value, null, 2));
  let parseError = $state<string | null>(null);

  function handleInput(e: Event) {
    const text = (e.currentTarget as HTMLTextAreaElement).value;
    rawText = text;
    try {
      const parsed = JSON.parse(text) as Record<string, unknown>;
      parseError = null;
      onChange(parsed);
    } catch {
      parseError = 'JSON invalide — les modifications ne seront pas enregistrées.';
    }
  }
</script>

<!-- pass-through: this block is emitted verbatim to configarr.yml -->
<div class="configarr-raw-editor">
  <label class="field-label" for="configarr-raw">{CONFIGARR_RAW_LABEL}</label>
  <textarea
    id="configarr-raw"
    class="raw-editor"
    value={rawText}
    oninput={handleInput}
    rows={12}
    spellcheck="false"
    aria-label={CONFIGARR_RAW_LABEL}
  ></textarea>
  {#if parseError}
    <span class="parse-error">{parseError}</span>
  {/if}
  <code class="helper-text">{CONFIGARR_RAW_HELPER}</code>
</div>

<style>
  .configarr-raw-editor {
    display: flex;
    flex-direction: column;
    gap: var(--space-xs);
  }

  .field-label {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 14px;
    font-weight: 600;
    color: var(--ink);
  }

  .raw-editor {
    width: 100%;
    min-height: 200px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    background: var(--code-bg);
    border: 1px solid var(--border);
    border-radius: 3px;
    padding: var(--space-sm) var(--space-md);
    color: var(--ink);
    resize: vertical;
    box-sizing: border-box;
  }
  .raw-editor:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 3px var(--accent-soft);
  }

  .parse-error {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    color: var(--destructive);
  }

  .helper-text {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 12px;
    font-weight: 400;
    color: var(--ink-faint);
    font-style: italic;
    background: none;
    padding: 0;
    border: none;
  }
</style>
