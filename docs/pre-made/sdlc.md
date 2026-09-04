# SDLC — CWA Ship Karachi 2026

**Purpose:** Prove this system went through a real, standard SDLC — not a "hacked together" flow — while fitting entirely inside a 5-hour build window.

## Governing Rules

1. **No phase is skipped.** Every phase below runs, even if compressed to a few minutes. Skipping a phase to save time is not allowed — cutting *scope within* a phase is.
2. **Everything preparable in advance is prepared in advance.** If a phase's output doesn't depend on knowing the theme, it's already done before kickoff.
3. **Every phase is time-boxed.** When time runs out, the phase ends with whatever it has — don't let one phase eat another's budget.
4. **Every phase produces one concrete artifact** (a document, a contract, a test result, a deployed build). This is what makes the SDLC demonstrable to judges, not just claimed.

## Phase-by-Phase

### Phase 1 — Discovery & SRS Generation
**Time-box: 9:30–10:00 (30 min)**
Answer the pre-written discovery question bank (below) as a team, as soon as the theme is revealed. Feed the answers into an LLM with a fixed prompt template to generate a short SRS-style document (problem statement, scope, user stories, must-haves vs. stretch). No open-ended brainstorming here — the question bank exists specifically to prevent this phase from sprawling.
**Output:** `srs.md`

### Phase 2 — Solution Design
**Time-box: 10:00–10:30 (30 min)**
Map the SRS onto the existing scaffold: which service owns which part of the problem, what the Core Domain Service's models/endpoints actually are, whether the AI Service's role changes shape. This phase only decides *what fits where* in the architecture already built — it does not re-litigate the architecture itself. End with components distributed to owners.
**Output:** Updated `architecture.md` (domain-specific), ownership assignments

### Phase 3 — Component Design
**Time-box: 10:30–10:45 (15 min)**
Each owner independently defines their component's contract: endpoints, request/response shapes, data model, key logic — filling the OpenAPI contract template. This is a design pass, not implementation; it's what lets everyone build in parallel with zero interface guesswork in Phase 4.
**Output:** One filled contract per component

### Phase 4 — Implementation
**Time-box: 10:45–12:30 (105 min)**
Each owner directs AI agents to implement their component strictly against its locked contract and the coding guidelines. Owners review and correct agent output rather than hand-writing from scratch. No cross-component coordination needed here — that's the point of Phase 3.
**Output:** Working code per component, committed to the repo

### Phase 5 — Component (Unit) Testing
**Time-box: 12:30–13:00 (30 min)**
Each owner writes and runs unit tests for their own component per the testing guidelines, to the quality bar defined there — before touching anything else. A component isn't "done" until its own tests pass.
**Output:** Passing test suite per component

*— Lunch break, 13:00–14:00 —*

### Phase 6 — Integration & System Testing
**Time-box: 14:00–15:00 (60 min)**
Combine all components: wire real inter-service calls in place of mocks, bring the full stack up via `docker-compose up`, run end-to-end tests through the Gateway. This is where contract mismatches (if any) surface — fix them here, not by rewriting components from scratch.
**Output:** Full system running end-to-end locally

### Phase 7 — Refinement
**Time-box: 15:00–15:20 (20 min)**
Fix anything integration testing surfaced. No new features here — this phase exists to stabilize, not extend.
**Output:** Stable, deployable build

### Phase 8 — Documentation
**Time-box: 15:20–15:45 (25 min)**
Write the project documentation per the predefined documentation guide — concise, complete, no bloat. Most of the structure (architecture, SDLC, guidelines) already exists from pre-hackathon prep; this phase fills in the domain-specific parts (what was actually built, how to run it, key decisions made on the day).
**Output:** Final `README.md` / project docs, deployed build

### Phase 9 — Presentation & Submission
**Time-box: 15:45–16:00 (15 min)**
Feed the finished documentation into an AI tool (e.g. NotebookLM) to generate a short explainer/presentation — this is fast specifically *because* the documentation is already concise and complete. Package and submit by 16:00.
**Output:** Explainer artifact, final submission

## Full-Day Timeline

| Time | Phase | Duration |
|---|---|---|
| 9:30–10:00 | 1. Discovery & SRS | 30 min |
| 10:00–10:30 | 2. Solution Design | 30 min |
| 10:30–10:45 | 3. Component Design | 15 min |
| 10:45–12:30 | 4. Implementation | 105 min |
| 12:30–13:00 | 5. Component Testing | 30 min |
| 13:00–14:00 | *Lunch* | — |
| 14:00–15:00 | 6. Integration & System Testing | 60 min |
| 15:00–15:20 | 7. Refinement | 20 min |
| 15:20–15:45 | 8. Documentation | 25 min |
| 15:45–16:00 | 9. Presentation & Submission | 15 min |

## Discovery Question Bank

Answered as a team the moment the theme is revealed; answers feed directly into the SRS-generation prompt.

1. What is the core problem, in one sentence?
2. Who is the target user, specifically (not "everyone")?
3. What is the single primary user flow, start to finish?
4. What are the 3–5 must-have features for a working demo (MVP)? What's explicitly out of scope?
5. What data entities does the system need to store and manage?
6. Where does AI/LLM capability actually create value in this solution (not just "add AI somewhere")?
7. What does success look like in the live demo — what will we show judges happen?
8. Are there any external APIs, datasets, or constraints the problem statement implies we must use?
9. What's the one thing that, if it breaks, kills the demo — and how do we make sure it doesn't?
