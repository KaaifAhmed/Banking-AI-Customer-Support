# Documentation Guide — CWA Ship Karachi 2026

**Purpose:** Govern what gets written in Phase 8 (25 minutes). Same rule as coding and UX: every line fights for its place. Documentation that isn't read is worse than no documentation — it's wasted time on both ends.

## The Core Idea: Phase 8 Mostly Finalizes, Rarely Creates

Most of the documentation already exists by the time Phase 8 starts:

| Document | Created | Phase 8 job |
|---|---|---|
| `architecture.md` | Pre-hackathon, updated in Phase 2 | Quick check: does it still match what was actually built? Fix any drift, don't rewrite. |
| `srs.md` | Phase 1 | Same — verify it still reflects reality after implementation. Light edit, not a rewrite. |
| `sdlc.md`, `coding-guidelines.md`, `testing-guidelines.md`, `ux-guide.md`, `ui-guide.md` | Pre-hackathon | Process documents — leave as-is. They describe how we work, not what we built. |

**The one new document Phase 8 actually writes is the README.** Everything else is either already true or gets a two-minute accuracy pass. This is the entire payoff of documenting early instead of at the end.

## README.md — the one new document

The README is the single entry point. A judge, or anyone else, should be able to open only this file and understand what the project is and how to run it. It links out to everything else rather than repeating it.

**Structure (skip any section that would have nothing real to say):**

1. **What it is** — one paragraph. The problem, who it's for, what it does. No marketing language.
2. **How to run it** — exact, copy-pasteable commands (`docker-compose up`, seed steps if any). If it doesn't work by following these lines exactly, it's not done.
3. **How it works** — a few sentences, linking to `architecture.md` and `srs.md` for depth rather than re-explaining them.
4. **Demo flow** — the primary user journey from `ux-guide.md`'s locked map, written as a short numbered walkthrough a judge can follow live.
5. **What's out of scope** — one line, if relevant, so limitations read as a deliberate decision, not an oversight.

## Writing Rules (apply to the README and any edits to existing docs)

- **Plain English.** Short sentences, active voice, no jargon left unexplained.
- **Say it once.** If something is already documented elsewhere, link to it — never copy it into a second file. Two copies of the same fact means one of them will eventually be wrong.
- **No padding.** A section with nothing substantive to say gets deleted, not filled with filler to look complete.
- **Write for a two-minute read.** A judge or teammate should get the full picture of the README in under three minutes. If it's longer, cut, don't reorganize.
- **Show, don't narrate.** Exact commands and concrete examples over descriptions of what a command "does."

## What NOT to Create

Skip these — they're common in production docs but add no value for a one-day hackathon deliverable:

- A separate user manual (the README's demo flow covers this)
- A hand-written API reference (already auto-generated per `architecture.md` §7 — link to the Swagger UI instead)
- A changelog or contributing guide
- Any second document that only restates what an existing one already says

## Definition of Done (Phase 8)

- [ ] README exists, and a stranger could get the system running from it alone
- [ ] `architecture.md` and `srs.md` reflect what was actually built, not just the original plan
- [ ] No content is duplicated across documents — everything links instead of repeats
- [ ] Every remaining sentence would be missed if it were deleted
- [ ] Full README reads in under 3 minutes
