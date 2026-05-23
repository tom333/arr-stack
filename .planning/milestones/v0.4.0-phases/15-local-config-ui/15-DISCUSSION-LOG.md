---
phase: 15-local-config-ui
type: DISCUSSION-LOG
captured: 2026-05-23
participant: operator
---

# Phase 15 — Discussion log

Reference: `15-CONTEXT.md` for 12 final decisions (D-01..D-12) + Claude's Discretion items.

## Question 1 — Frontend framework

**Asked:** HTMX + Jinja / Svelte + Vite / React + Vite / Plain JS ?

Options presented:
- HTMX + Jinja (Recommended)
- Svelte + Vite + FastAPI API JSON
- React + Vite + FastAPI API JSON
- Plain HTML + vanilla JS

**User answered:** **Svelte + Vite + FastAPI API JSON**

(Operator chose the moderately heavier SPA option over the lighter HTMX. Implies preference for a "proper SPA" feel + reusable typed form components over the leanest server-rendered fragment approach.)

## Question 2 — Plan split

**Asked:** Split 15-A backend / 15-B frontend, or single integrated plan?

Options presented:
- Split 15-A / 15-B (Recommended)
- Single plan
- Split 15-A / 15-B / 15-C packaging+docs

**User answered:** **Split 15-A / 15-B** → D-03.

## Question 3 — Auth model

**Asked:** Bind 127.0.0.1 only with no auth, basic auth via env var, or token-based ?

Options presented:
- Bind 127.0.0.1 only, no auth (Recommended)
- Basic auth optional via ARRCONF_UI_PASSWORD env var
- Token-based via ARRCONF_UI_TOKEN

**User answered:** **Bind 127.0.0.1 only, no auth** → D-04.

## Question 4 — Diff preview format

**Asked:** Unified diff (git-style), side-by-side, or semantic summary?

Options presented:
- Unified diff git-style (Recommended)
- Side-by-side
- Semantic summary

**User answered:** **Semantic summary** ("3 categories added, 2 modified, 1 removed") → D-07.

(Operator chose the heaviest option for diff UX over the recommended quick-win. Implies they want the better operator experience even at the cost of more diff comparator code.)

## Question 5 — Svelte flavor

**Asked:** Svelte 5 vanilla + Vite, SvelteKit, or Svelte 4?

Options presented:
- Svelte 5 vanilla + Vite (Recommended)
- SvelteKit (SSR + routing)
- Svelte 4 (legacy)

**User answered:** **Svelte 5 vanilla + Vite** → D-01.

## Question 6 — Validation timing

**Asked:** On Save only, live per-field, or debounced batch?

Options presented:
- Save only (Recommended)
- Live per-field
- Live but debounced

**User answered:** **Save only** → D-06.

## Question 7 — Save semantics

**Asked:** Direct overwrite, backup .bak + overwrite, or write-temp + atomic rename?

Options presented:
- Direct overwrite via ruyaml round-trip (Recommended)
- Backup .bak + overwrite
- Write-temp + atomic rename

**User answered:** **Direct overwrite via ruyaml round-trip** → D-05.

(Note: D-05 instructs the planner to STILL use atomic write internally — write-temp + os.replace — as an implementation detail, while presenting "direct overwrite" semantics to the user. No .bak.)

## Question 8 — Categories reorder UX

**Asked:** Up/down arrows + delete, drag-and-drop native HTML5, or drag-and-drop with lib?

Options presented:
- Up/down arrows + delete (Recommended)
- Drag-and-drop native HTML5
- Drag-and-drop with svelte-dnd-action lib

**User answered:** **Up/down arrows + delete** → D-08.

## Total

8 questions answered. 4 of 8 took the "Recommended" option. 4 of 8 went heavier than recommended:
- Q1 (frontend framework — Svelte > HTMX)
- Q4 (diff preview — semantic > unified)
- Plus the inherent choices D-02 (3 API endpoints, single backend), D-09 (SuggestArr coupling indicator), D-12 (packaging launch UX)

12 decisions captured in CONTEXT (D-01..D-12) + 7 Claude's Discretion items deferred to planner.
