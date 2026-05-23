<script lang="ts">
  type Props = { label?: string };
  let { label = 'Loading…' }: Props = $props();
</script>

<div class="spinner-wrap" role="status" aria-live="polite">
  <div class="spinner" aria-hidden="true"></div>
  <div class="spinner-label">{label}</div>
</div>

<style>
  .spinner-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-md);
    padding: var(--space-2xl);
  }
  .spinner {
    width: 32px;
    height: 32px;
    border: 3px solid var(--color-border);
    border-top-color: var(--color-accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  .spinner-label {
    color: var(--color-muted);
    font-size: 14px;
  }
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
