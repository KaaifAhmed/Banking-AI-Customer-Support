# Coding Guidelines — CWA Ship Karachi 2026

**Purpose:** Production-grade code, written fast, by AI agents directed by us. These rules exist to keep every component simple, readable, and safely swappable — not to add process for its own sake.

## Core Philosophy

1. **Simple and monolithic within a component.** Don't split a component into files/folders it doesn't need. One clear `models.py`, one clear `views.py`, one clear `serializers.py` beats ten files of "organization" nobody asked for. Split only when a file is genuinely doing two unrelated jobs — not preemptively.
2. **Every line fights for its place.** No speculative abstractions, no "might need this later" code, no unused imports/functions/config. If it's not needed for the current contract, it doesn't get written.
3. **Self-explanatory over clever.** Someone should be able to read a function and know what it does without a comment. Clear names and straight-line logic beat clever one-liners.
4. **Follow the framework's own conventions.** Django/DRF has an idiomatic way to do almost everything (model validation, serializers, class-based views, migrations, settings via env vars). Use it. Don't invent a custom pattern where Django already has a standard one — that's both extra code and extra cognitive load for no benefit.
5. **Build to the contract, not past it.** Every component was given a locked input/output contract in the design phase. Implement exactly that. Nothing outside the contract is anyone else's business — and nothing inside the contract should be missing.

## Boundaries & Encapsulation

- A component's internals (model fields beyond what the contract exposes, helper functions, internal logic) can change freely without needing anyone else's sign-off — **as long as the contract's inputs/outputs stay identical.**
- Never let one component reach into another's database or internals. All cross-component interaction goes through the defined API, full stop.
- Validate everything at the boundary (serializers/DRF validation). Once data is inside the component, trust it — don't re-validate defensively everywhere.

## Error Handling

- Every endpoint returns the standard response envelope defined in `architecture.md` (`success`, `data`, `error`) — no ad hoc response shapes.
- Handle the errors that can actually happen (bad input, not found, auth failure) with the right status code. Don't wrap every line in defensive try/except "just in case" — that hides real bugs instead of preventing them.

## Comments

- Comment *why*, not *what*. If a comment just restates the line below it, delete the comment.
- No commented-out code. No leftover `TODO`s at submission time — either do it or don't write it.

## Incremental, Modular Development

- Component design breaks each component into a small ordered list of modules/steps (e.g., "user model → registration endpoint → login endpoint → JWT issuance").
- Implement one module fully — working and passing its own test — before starting the next. Never have three half-built modules in progress at once; it's the fastest way to lose track of what actually works.

## Standard Practices (don't overthink these)

- **Python/Django:** PEP 8, Django's standard app layout, environment variables via `.env` (never hardcoded secrets/config), migrations committed with the code that needs them.
- **React:** functional components + hooks, no state management library unless the component genuinely needs one (plain `useState`/`useContext` is enough for a hackathon scope), co-locate a component's files only if there are actually multiple files to co-locate.
- **Naming:** standard, descriptive, boring is good — `get_user_by_id`, not `fetchUsrData2`. Consistency matters more than any specific style choice.

## Definition of Done (per module/component)

A piece of code is done when:
- [ ] It matches its locked contract exactly — no more, no less
- [ ] It passes its own tests
- [ ] There's no dead code, unused imports, or commented-out blocks
- [ ] A teammate could read it cold and understand what it does within a minute
- [ ] It follows the framework's standard patterns, not a custom invention

## Quick Checklist for Directing AI Agents

When prompting an agent to write a module, give it:
1. The locked contract (input/output shapes)
2. "Follow standard Django/DRF/React conventions"
3. "Write only what's needed for this contract — no extra features, no speculative code"
4. "Keep it in the existing file structure — don't create new files unless this genuinely doesn't belong anywhere existing"
5. A one-line description of what "done" looks like for this specific module

Then review the output against the Definition of Done above before merging it in.
