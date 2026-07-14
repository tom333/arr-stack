<script lang="ts">
  let { title, detail, warn = "⚠ copie NFS — peut ralentir Jellyfin", onConfirm, onCancel }:
    { title: string; detail: string; warn?: string; onConfirm: () => void; onCancel: () => void } = $props();
  function onKeydown(e: KeyboardEvent) { if (e.key === "Escape") onCancel(); }
</script>

<svelte:window onkeydown={onKeydown} />

<div class="overlay" onclick={onCancel} role="presentation">
  <div class="box" tabindex="-1" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-labelledby="confirm-title">
    <h3 id="confirm-title">{title}</h3>
    <p class="detail mono">{detail}</p>
    <p class="warn">{warn}</p>
    <div class="btns">
      <button class="btn btn-secondary" onclick={onCancel}>Annuler</button>
      <button class="btn btn-primary" onclick={onConfirm}>Confirmer</button>
    </div>
  </div>
</div>

<style>
  .overlay { position: fixed; inset: 0; background: rgba(0,0,0,.6); display: grid; place-items: center; z-index: 60; }
  .box { background: var(--surface-2); border: 1px solid var(--border); padding: 1.2rem 1.4rem; border-radius: var(--radius); max-width: 480px; }
  .box h3 { margin: 0 0 .5rem; }
  .warn { color: var(--warn); }
  .detail { color: var(--text-muted); font-size: .8rem; }
  .btns { display: flex; gap: .6rem; justify-content: flex-end; margin-top: 1rem; }
</style>
