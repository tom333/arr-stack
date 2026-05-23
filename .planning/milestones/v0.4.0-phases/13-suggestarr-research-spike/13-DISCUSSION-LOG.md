---
phase: 13-suggestarr-research-spike
type: DISCUSSION-LOG
captured: 2026-05-22
participant: operator
---

# Phase 13 — Discussion log

Reference: `13-CONTEXT.md` for the final decisions. This log captures the question-by-question flow.

## Question 1 — Architectural lean

**Asked:** Tu as un lean architectural avant que le spike démarre ?

Options presented:
- A — Helm sidecar (Recommended)
- B — Reconciler dans arrconf
- C — CronJob standalone
- Pas d'avis — recherche ouverte

**User answered:** **A — Helm sidecar**

Note: pattern déjà utilisé 10 fois dans le chart, daemon Docker s'enferme proprement dans son alias, pas de couplage Python avec arrconf.

## Question 2 — Categories-aware routing requirement

**Asked:** Categories-aware routing est must-have ou nice-to-have ?

Options presented:
- Must-have — architecture doit le supporter
- Must-have — fallback acceptable via Seerr default tags (Recommended)
- Nice-to-have — Phase 14 peut basculer si pas natif

**User answered:** **Must-have — architecture doit le supporter** (strict variant — rejected the Seerr-side-fallback option)

This created an explicit tension with Q1 (A — sidecar) that drove Q4.

## Question 3 — Spike depth

**Asked:** Profondeur du spike — desk research ou hands-on POC ?

Options presented:
- Desk research only (Recommended)
- Desk + hands-on POC
- Wait-and-see — spike super-light

**User answered:** **Desk research only**

## Question 4 — Routing fallback (tension surfaced after Q1+Q2)

**Asked:** Si le researcher découvre que SuggestArr n'a PAS de tag-based routing natif, comment je procède ?

Options presented:
- Bascule l'archi vers B (Recommended)
- Reste sur A et accepte le routing via Seerr en aval
- Spike s'arrête avec 'pas mature', recommande wait-and-see
- Décide à la lecture du RESEARCH

**User answered:** **Bascule l'archi vers B**

Resolution: D-01 in CONTEXT now encodes a decision tree (default A, fallback B; C eliminated upfront).

## Question 5 — Secrets model

**Asked:** Modèle secrets pour SuggestArr ?

Options presented:
- Étendre arrconf-env existant (Recommended)
- Nouvelle SealedSecret suggestarr-env
- Décide en Phase 14 selon archi locked

**User answered:** **Étendre arrconf-env existant**

## Question 6 — Operator workflow

**Asked:** SuggestArr auto-submit vers Seerr, ou review humain entre les deux ?

Options presented:
- Auto-submit (Recommended)
- Review queue dans Seerr
- Dépend de la fonctionnalité SuggestArr

**User answered:** **Auto-submit**

## Total

6 questions answered. CONTEXT.md captures the 7 decisions (D-01 through D-07) + Claude's discretion list.
