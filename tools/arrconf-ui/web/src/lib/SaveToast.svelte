<script lang="ts">
  // UI-SPEC §7 — Save toast notification.
  // Copy FR : "Enregistré — vérifie avec `git diff`, puis push."
  // Auto-dismiss après 4s ; click-to-dismiss.

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
    aria-label="Fermer la notification"
    onclick={onDismiss}
  >
    <span class="check" aria-hidden="true">✓</span>
    <span>
      Enregistré — vérifie avec <code>git diff</code>, puis push.
    </span>
  </button>
</div>

<style>
  .toast-wrap {
    position: fixed;
    right: var(--space-lg);
    bottom: var(--space-lg);
    z-index: 1000;
    animation: slideIn 240ms ease-out;
  }
  @keyframes slideIn {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  .toast {
    display: inline-flex;
    align-items: center;
    gap: var(--space-sm);
    background: var(--panel);
    border: 1px solid var(--border);
    border-left: 4px solid var(--accent);
    border-radius: 4px;
    padding: 10px 16px;
    box-shadow: var(--shadow-md);
    color: var(--ink);
    text-align: left;
    cursor: pointer;
    font-size: 13px;
  }
  .toast:hover {
    background: var(--panel-alt);
  }
  .check {
    color: var(--accent);
    font-weight: 700;
    font-size: 16px;
  }
</style>
