<script lang="ts">
  // UI-SPEC §7 — Save toast notification.
  // Copy: "Saved — run `git diff` to review, then push." (verbatim).
  // Auto-dismiss after 4s; click-to-dismiss.

  type Props = {
    onDismiss: () => void;
  };
  let { onDismiss }: Props = $props();

  $effect(() => {
    const t = setTimeout(onDismiss, 4000);
    return () => clearTimeout(t);
  });
</script>

<div class="toast-wrap" role="status" aria-live="polite">
  <button
    type="button"
    class="toast"
    onclick={onDismiss}
  >
    Saved — run <code>git diff</code> to review, then push.
  </button>
</div>

<style>
  .toast-wrap {
    position: fixed;
    right: var(--space-lg);
    bottom: var(--space-lg);
    z-index: 1000;
  }
  .toast {
    background: var(--color-panel);
    border: 1px solid var(--color-border);
    border-left: 4px solid var(--color-accent);
    border-radius: 6px;
    padding: 12px 16px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
    color: inherit;
    text-align: left;
    cursor: pointer;
    font-size: 14px;
  }
</style>
