<script lang="ts">
  import {
    SUGGESTARR_COUPLED_PATHS,
    SUGGESTARR_COUPLED_CATEGORY_NAMES,
    SUGGESTARR_TOOLTIP_TEXT,
  } from '../constants';

  // D-09 — informational badge for 7 fields coupled to Phase 14 SuggestArr
  // routing config. Field remains editable; this is a visual hint only.

  type Props = {
    /** Dotted path of the field. */
    path: string;
    /** For categories[].base_path rendering: the category name (e.g., "films-zoe"). */
    categoryName?: string;
  };
  let { path, categoryName }: Props = $props();

  const isCoupled = $derived(
    SUGGESTARR_COUPLED_PATHS.has(path) ||
      (path.endsWith('.base_path') &&
        !!categoryName &&
        SUGGESTARR_COUPLED_CATEGORY_NAMES.has(categoryName)),
  );
</script>

{#if isCoupled}
  <span class="badge" title={SUGGESTARR_TOOLTIP_TEXT} aria-label={SUGGESTARR_TOOLTIP_TEXT}>
    ↗ SuggestArr
  </span>
{/if}

<style>
  .badge {
    display: inline-block;
    background: var(--color-badge-bg);
    color: var(--color-badge-fg);
    border-radius: 4px;
    font-size: 12px;
    padding: 2px 6px;
    margin-left: var(--space-xs);
    cursor: help;
    user-select: none;
  }
</style>
