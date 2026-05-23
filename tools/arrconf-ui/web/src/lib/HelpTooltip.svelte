<script lang="ts">
  // D-14 — surfaces pydantic Field(description=...) verbatim from JSON Schema.
  // Implementation: native `title` attribute on a small (i) span. Touch + focus
  // accessible (browsers handle title-on-focus + screen-reader announcement).
  // Empty descriptions: the parent component should not render this widget
  // (FieldInput.svelte guards via `{#if description}` block).

  type Props = { text: string };
  let { text }: Props = $props();
</script>

<span class="help-icon" title={text} aria-label={`Help: ${text}`}>ⓘ</span>

<style>
  .help-icon {
    display: inline-block;
    color: var(--color-muted);
    cursor: help;
    user-select: none;
    margin-left: var(--space-xs);
    font-size: 12px;
  }
  .help-icon:hover,
  .help-icon:focus-visible {
    color: var(--color-accent);
  }
</style>
