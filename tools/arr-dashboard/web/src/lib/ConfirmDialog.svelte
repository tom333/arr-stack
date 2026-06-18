<script lang="ts">
  let { title, detail, onConfirm, onCancel }: { title: string; detail: string; onConfirm: () => void; onCancel: () => void } = $props();
</script>

<div class="overlay" onclick={onCancel}>
  <div class="box" onclick={(e) => e.stopPropagation()}>
    <h3>{title}</h3>
    <p class="detail">{detail}</p>
    <p class="warn">⚠ copie NFS — peut ralentir Jellyfin</p>
    <div class="btns"><button onclick={onCancel}>Annuler</button><button class="go" onclick={onConfirm}>Confirmer</button></div>
  </div>
</div>

<style>
  .overlay { position: fixed; inset: 0; background: #000a; display: grid; place-items: center; }
  .box { background: #161a22; padding: 1.2rem; border-radius: 8px; max-width: 480px; }
  .warn { color: #fbbf24; } .detail { color: #9ca3af; font-family: "IBM Plex Mono", monospace; font-size: .8rem; }
  .btns { display: flex; gap: .6rem; justify-content: flex-end; margin-top: 1rem; }
  .go { background: #4ade80; color: #06281a; border: 0; padding: .4rem .9rem; border-radius: 4px; }
</style>
