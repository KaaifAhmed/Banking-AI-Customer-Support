# UX Guide — CWA Ship Karachi 2026

**Purpose:** The frontend's only job is to serve the SRS — get the user to their goal in the fewest, clearest steps possible. UX is designed before a single screen is built. This document locks the *process*, since the actual journey can't be designed until the theme is known.

## Core Principle

Every design decision is judged against one question: **does this get the user to their goal faster and more clearly?** Not "does this look interesting" — that's the UI guide's job, and it comes second.

## The UX Process

Run this during Phase 2 of the SDLC (Solution Design), immediately after the SRS exists — budget ~10–15 minutes:

1. **Extract the primary journey.** One sentence from the SRS: who the user is, what they want, and the minimum sequence to get it.
2. **List every screen/step** required to complete that journey, start to finish. Nothing extra, nothing speculative.
3. **Cut ruthlessly.** For each step ask: *can this be removed, merged into another step, or defaulted automatically?* Same rule as the coding guidelines — every step must fight for its place, same as every line of code.
4. **Order the flow.** Entry point → each remaining screen → goal completion.
5. **One primary action per screen.** If a screen has two competing "main" actions, it isn't finished — pick one and demote the other.
6. **Lock it before UI starts.** No screens get visually designed before this flow is written down and agreed on.

## Principles (locked, apply to any theme)

- **Fewest clicks to value.** Every additional step must justify itself against the cost of an extra click.
- **Progressive disclosure.** Show what's needed for the current step only — don't front-load every option onto one screen.
- **Always show state.** Every action gets visible feedback: loading, success, or error, using the standard response envelope from `architecture.md`. No silent failures, no dead clicks.
- **Forgiving.** Users can go back or undo wherever the flow reasonably allows it.
- **Accessible by default.** Sufficient contrast, adequately sized tap targets, logical tab/focus order — this is a baseline requirement, not a stretch goal.

## What This Phase Produces

A short journey map — a numbered list of screens and the transitions between them, with each screen's single primary action named. That's the artifact. It's what Phase 3 (component design) and the UI guide both build from, and it's the proof, if judges ask, that UX was actually designed rather than improvised screen-by-screen.
