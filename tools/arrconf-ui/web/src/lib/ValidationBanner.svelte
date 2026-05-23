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
    <span class="icon" aria-hidden="true">⚠</span>
    <span class="msg">
      {errors.length} erreur{errors.length === 1 ? '' : 's'} de validation — corrige les champs en rouge avant d'enregistrer.
    </span>
    <button
      type="button"
      class="dismiss"
      onclick={onDismiss}
      aria-label="Fermer la bannière d'erreurs"
    >✕</button>
  </div>
{/if}

<style>
  .banner {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    background: var(--error-bg);
    border: 1px solid var(--destructive);
    border-left: 4px solid var(--destructive);
    padding: var(--space-sm) var(--space-md);
    margin-bottom: var(--space-md);
    border-radius: 4px;
    color: var(--destructive);
  }
  .icon {
    font-size: 16px;
    line-height: 1;
  }
  .msg {
    flex: 1;
    font-size: 13px;
    font-weight: 500;
  }
  .dismiss {
    background: transparent;
    border: 1px solid transparent;
    color: var(--destructive);
    cursor: pointer;
    padding: 4px 8px;
    font-size: 14px;
  }
  .dismiss:hover {
    background: var(--destructive-soft);
    border-color: var(--destructive);
  }
</style>
