<script lang="ts">
  import type { PydanticErrorEntry } from '../types';

  type Props = {
    errors: PydanticErrorEntry[];
    onDismiss: () => void;
  };
  let { errors, onDismiss }: Props = $props();
</script>

{#if errors.length > 0}
  <div class="banner" role="alert">
    <span class="msg">
      {errors.length} validation error{errors.length === 1 ? '' : 's'} — fix the highlighted fields before saving.
    </span>
    <button type="button" class="dismiss" onclick={onDismiss} aria-label="Dismiss error banner">✕</button>
  </div>
{/if}

<style>
  .banner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: var(--color-error-bg);
    border-left: 4px solid var(--color-destructive);
    padding: var(--space-sm) var(--space-md);
    margin-bottom: var(--space-md);
    border-radius: 4px;
  }
  .msg {
    color: var(--color-destructive);
    font-size: 14px;
  }
  .dismiss {
    background: transparent;
    border: none;
    color: var(--color-destructive);
    cursor: pointer;
    padding: var(--space-xs);
  }
</style>
