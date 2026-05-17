---
seed_id: SEED-001
title: SuggestArr — auto-suggest content based on watch history
planted_during: v0.3.0 scoping (2026-05-17)
planted_in_milestone: v0.2.0 (close-out conversation)
trigger_when:
  - "milestone target includes recommendation / discovery features"
  - "user mentions wanting more automated content discovery"
  - "Seerr usage stabilized and operator wants to reduce manual request work"
source: https://github.com/giuseppe99barchetta/SuggestArr
status: parked
target_milestone: v0.4.0 (or later)
---

# SEED-001: SuggestArr — automated content suggestions

## Idea

Add **SuggestArr** (https://github.com/giuseppe99barchetta/SuggestArr) to the arr-stack umbrella.

SuggestArr analyzes Jellyfin/Plex watch history and automatically creates Sonarr / Radarr / Jellyseerr / Overseerr requests for similar content. Reduces the manual "I just watched X, what should I watch next?" cycle to zero clicks.

## Why this is a fit for arr-stack

- **Completes the discovery layer.** Today the user opens Seerr and types titles manually. SuggestArr automates this for the multi-user homelab pattern that v0.3.0 establishes.
- **Multi-user-aware natively.** Per-user watch history → per-user suggestions → per-user Seerr requests (which already have per-user permissions in v0.3.0).
- **Per-category routing reuse.** SuggestArr can route a "new anime suggestion" request through the `animeTags` mechanism the v0.3.0 Categories model already wires up.

## When to surface

- When the user asks about automating Seerr requests, content discovery, or "what should I watch" tooling.
- When SuggestArr reaches a more mature release (currently early-stage as of 2026-05).
- When v0.3.0 categories + multi-user is shipped and stable (this seed depends on that foundation).

## Open questions for the future milestone

- Does SuggestArr run as a CronJob (like arrconf/configarr) or a persistent Deployment?
- Does it need its own SealedSecret entries (Jellyfin API key per-user? Seerr API key?), or can it reuse arrconf-env?
- Should it be a 7th declarative reconciler in arrconf (`suggestarr.py`), or kept as an opaque sidecar?
- Per-user routing: does SuggestArr respect the Categories model (anime-zoe → only zoe gets her own suggestions) or is it global?

## Notes

- Planted during v0.3.0 scoping conversation when the user clarified "j'avais cité preparr mais en fait je pensais à SuggestArr — note pour plus tard".
- The user's actual v0.3.0 focus is Categories first-class + multi-tenant — SuggestArr is the next-but-one milestone candidate.
