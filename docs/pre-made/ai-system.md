
# AI System — CWA Ship Karachi 2026

**Purpose:** This is the core of the product. Full design of the AI/LLM system — orchestration, runtime, and security — pulled out of `architecture.md` into its own file because it's the thing being judged most closely. Read alongside `architecture.md` (component boundaries) and `coding-guidelines.md`/`testing-guidelines.md` (how it's built).

## 1. Orchestration & Model Stack

- **Orchestration:** LangGraph (built on LangChain) — state graphs handle cycles and multi-agent coordination directly. Baseline, not just an escape hatch: the code is AI-agent-authored, so the framework's learning curve costs little here, and LangGraph's cycle/multi-agent support is hard to replicate by hand in the time available.
- **Model access:** LiteLLM underneath, wired into LangChain via `ChatLiteLLMRouter` (`langchain-litellm`) — LangGraph nodes use it as a normal chat model while LiteLLM's fallback chains and cost tracking run underneath.
- **Model tiers + fallback:** a LiteLLM `Router` config — `fast` / `smart` tiers, each with an ordered fallback list. Swapping a rate-limited model mid-demo is a config change, not a code change.
- **Prompts:** LangChain `PromptTemplate`s, versioned as named files (e.g. `prompts/v1_summarize.py`).
- **Structured output:** `.with_structured_output(PydanticModel)` — validation and parsing in one step.
- **Tool calling:** `@tool` decorator + `.bind_tools()` — native provider function-calling underneath.
- **RAG:** pgvector as the vector store, via LangChain's `PGVector` retriever. `PGVector` connects to Postgres directly, `PGVector` gets a scoped, explicit exception.
- **Streaming:** flagged as a probable stretch feature, not baseline.

## 2. AI Worker Pool Runtime

Async Python, no web framework, 3 replicas, consuming `ai_queue` only. Per-replica concurrency cap, per-job timeout, one retry with backoff, heartbeat for liveness. AI config (prompts, model tiers, fallback order) fetched from Main Service via `GET /api/internal/ai-config`, cached ~30–60s — never a direct DB connection. Full detail in `architecture.md` §"AI Worker Pool".

## 3. Dynamic Configuration

Prompt text/version, model tier→provider mapping, fallback order, and per-prompt temperature/max_tokens are DB-backed and editable via Django Admin — cheap and high-value. Deliberately **not** dynamic: the orchestration graph, tool functions, and RAG chunking logic. Config changes at runtime; logic doesn't. Full detail in `architecture.md` §"Dynamic Configuration".

## 4. Security — Agent-Based

### 4.1 Principle of Least Access
- No agent or worker ever holds a Postgres credential — everything goes through Main Service's scoped API. This was already the architecture for other reasons (keeping "only Main Service touches Postgres" true); it's also PLA in practice, not a separate mechanism.
- Tools are bound **per graph node**, not globally: `.bind_tools([...])` gets exactly the tools that node's task requires. A summarization node never holds a tool that can send a message or write data.
- LLM provider API keys live only in the AI Worker Pool's environment — never passed into a prompt, a tool's input, or anywhere a model's output could echo them back out.
- If a specific task genuinely needs a write capability, it's scoped to that one job, not granted as a standing permission to the agent generally.
- Information from internal documents shouldn't be sent directly/fully as output.

### 4.2 Role-Based Access Control
Agent roles are defined explicitly, each with an allow-list of tools. For example:

```python
AGENT_ROLES = {
    "retriever":       {"tools": ["search_documents"], "can_act_externally": False},
    "responder":       {"tools": ["search_documents", "format_response"], "can_act_externally": False},
    "action_executor": {"tools": ["send_whatsapp_message"], "can_act_externally": True},
}
```

A graph node is instantiated with exactly one role's tool set — never the full registry. Unlike prompts/model config, **role definitions live in code**, reviewed like any other code — permissions are not part of Dynamic Configuration. Same "config is dynamic, logic isn't" boundary as §3, applied to access control specifically because permissions are exactly the kind of thing that shouldn't be one Django-Admin click away from being loosened.

### 4.3 Don't Fully Trust LLM Output
- Any output that triggers an action (a DB write via Main Service, a tool call, an external message) is schema-validated first — never executed as if it were pre-approved instructions.
- Everything heading externally (a WhatsApp send, a written record) passes through the output guard (§5.1) — no exception for "trusted" internal agents.
- Where an answer is RAG-grounded, the source is retained alongside it, so a claim is traceable to what it was actually based on rather than presented as verified fact with no provenance.

### 4.4 Agent Identities for Traceability
`ai_calls` telemetry (already planned: `prompt_version`, `model`, `tokens`, `latency_ms`, `cost_estimate`) is extended with `agent_role`, `job_id`, and the initiating `user_id`/phone number. Any downstream action — a tool call, a WhatsApp send — logs which role triggered it, so the full chain from "user asked X" to "agent Y called tool Z" is reconstructable after the fact.

## 5. Security — Data-Based

### 5.1 Input/Output Blockers
**Into the LLM:**
- Untrusted content (user messages, RAG results, tool/web results, WhatsApp messages) is inserted as clearly delimited *data* — LangChain's message-role structure (system / human / tool) enforces this rather than hand-built string concatenation that could blur data and instructions together.
- A lightweight injection-pattern check (flagging phrases like "ignore previous instructions" or attempts to extract the system prompt) runs on external input before use — flagged and logged, not silently passed through.
- Basic sanity limits: length caps, rejecting empty/malformed payloads, before a call is made at all.

**Out of the LLM:**
- Structured-output validation is the first gate.
- A second, explicit output guard scans for leakage before anything external is sent: no echoed system prompts, no obvious credential patterns, no PII beyond what the task needs.
- This matters concretely because of WhatsApp — it's the one place AI-generated content leaves the system for an external, unmoderated channel. Nothing reaches `shared/whatsapp_client.py`'s `send_whatsapp_message()` without clearing the output guard first.

### 5.2 Securing/Verifying Sources
- RAG ingestion only accepts deliberately vetted sources — not arbitrary user-supplied content silently becoming trusted context.
- Retrieved content is stored with its source (document/URL + timestamp) so it's traceable — same idea as §4.3's source-retention, applied at ingestion.
- Live web-fetch/search tool results get the same treatment as RAG content: delimited as data, never as instructions.

## 6. Proactive Threat Management

### 6.1 General System Security
- Secrets only in `.env`/environment — already the pattern throughout (`coding-guidelines.md`).
- JWT already scopes who can reach the system at all (`architecture.md`).
- `pip-audit` / `npm audit` as a cheap CI addition, catching known-vulnerable dependencies before they ship.
- Any genuinely sensitive field, if one ends up needed, gets encrypted at rest — a call made at kickoff if it comes up, not assumed necessary now.

### 6.2 Logging & Anomaly Flagging
`ai_calls` telemetry is the audit trail: every call, agent role, tool invocation, and guard trigger (injection flagged, output blocked) is logged — not just successes. Simple anomaly signal: repeated injection flags from the same source (user/session/phone number) in a short window gets flagged for review. Doesn't need to be sophisticated to be useful.

### 6.3 Known Risk Surface
Naming these explicitly is itself a production-grade signal — a system that names its weak points is more credible than one that claims to have none:
- **Unofficial WhatsApp library** — the least-trusted input path (user-controlled, spoofed session). Its inbound content gets the strictest input handling of anything in the system.
- **RAG ingestion**, if activated — a poisoning vector; a crafted document could carry instruction-like text aimed at hijacking whatever agent retrieves it.
- **Tool-calling** — risk is bounded by RBAC (§4.2/§5.2) specifically because an over-scoped toolset is the most direct path to unintended action.
- **LLM provider credentials** — the one leak that would be genuinely bad. Confined to the AI Worker Pool's environment, never reachable from prompt content or tool output.
