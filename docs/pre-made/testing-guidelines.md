# Testing Guidelines — CWA Ship Karachi 2026

**Purpose:** Prove the system actually works, at every level, without burying the team in test infrastructure they don't have time to manage. Minimal, meaningful, and understandable beats exhaustive.

## Philosophy

- **Lightweight TDD.** For each module in a component's build order, write a small test that defines what "correct" looks like *before* (or right alongside) implementing it. The test is the spec, not an afterthought.
- **Test what matters, not everything.** Cover the contract's inputs/outputs and the failure paths that would actually break the demo. Don't chase 100% coverage or test framework internals (e.g. don't test that Django's ORM saves a row — test that *your* endpoint behaves correctly).
- **Readable over sophisticated.** A test should read like a plain description of behavior. If a teammate can't tell what a test checks from its name and body in a few seconds, it's too complicated for this context.

## TDD Workflow (per module)

1. Look at the module's piece of the contract (e.g. "`POST /auth/login` → valid credentials return a JWT; invalid credentials return 401").
2. Write one test per behavior, named for that behavior, before or immediately after asking the AI agent to implement it.
3. Implement until the test passes.
4. Move to the next module. Don't batch-write all tests at the end — that turns testing into a separate, dreaded phase instead of part of building.

## What to Test

- **Contract compliance:** given a valid input, does the endpoint return the right shape and status code?
- **Core logic correctness:** the actual business rule the module exists for (e.g. "expired JWT is rejected," not "Django can serialize a dict").
- **Known failure paths:** the errors that are actually likely — bad input, missing auth, not-found — matching the standard error envelope.

## What Not to Test

- Framework internals (Django's ORM, DRF's serializer machinery) — trust the framework.
- Exhaustive edge cases with no realistic chance of occurring in a demo.
- UI pixel-level detail on the frontend — a couple of key interaction tests (e.g. "form submit calls the right endpoint") is enough; don't build a full frontend test suite.

## Test Levels & Where They Happen

| Level | Scope | When | Tooling |
|---|---|---|---|
| Unit | One module/function within a component | Phase 4–5 (as each module is built) | Django `TestCase` / `pytest-django` |
| Component | One service's endpoints, in isolation | End of Phase 5 | DRF `APIClient` |
| Integration/System | Real calls across services via the Gateway | Phase 6 | `docker-compose up` + a short end-to-end script/Postman collection |

Keep it to these three levels. No separate load testing, no elaborate CI test matrices — a green CI run on push (lint + this test suite) is enough to demonstrate production discipline to judges.

## Writing Tests

- One behavior per test. `test_login_with_valid_credentials_returns_token`, `test_login_with_wrong_password_returns_401` — not one giant test covering five cases.
- Minimal mocking: only mock things genuinely external to the component under test (an LLM API call, another service). Never mock your own component's internals — if you need to, the component is probably too tangled.
- Use the framework's built-in test client and fixtures. No custom test framework, no unnecessary factory libraries unless a teammate already knows one cold.

## Definition of Done (testing)

A component is "surpassing the quality bar" when:
- [ ] Every contract endpoint has at least one test for the success case and one for the primary failure case
- [ ] All tests pass locally and in CI
- [ ] Test names alone explain what's being verified, no need to read the body to guess
- [ ] No test depends on another test's side effects or run order

## Quick Checklist for Directing AI Agents

When asking an agent to build a module:
1. Give it the specific behavior to satisfy (from the contract)
2. Ask for the test first: "write a test that checks X returns Y for input Z"
3. Then ask for the implementation that makes it pass
4. Review: does the test name describe real behavior, or did the agent test something trivial/internal?
