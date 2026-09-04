# System Architecture

**Project:** CWA Ship Karachi 2026 — Production-Grade AI Product
**Status:** Pre-hackathon baseline — domain-agnostic, filled in at kickoff

## Diagram

```
                    ┌───────────────────┐
                    │   React Frontend  │
                    └─────────┬─────────┘
                              │ HTTPS + CORS
                              ▼
    ┌───────────────────────────────────────────────────┐
 ┌──│                   Main Service (Django)           │
 │  │   /auth/*   /api/*   /api/whatsapp/inbound        │◄──────────────┐
 │  └───────────────────┬───────────────────────────────┘               │
 │                      │ enqueues                                      │ inbound webhook
 │            ┌─────────┴─────────┐                                     │ (metadata only,
 │            ▼                   ▼                                     │  no file bytes)
 │    ┌───────────────┐   ┌───────────────┐                             │
 │    │   ai_queue    │   │  tasks_queue  │   Redis                     │
 │    └───────┬───────┘   └───────┬───────┘                             │
 │            ▼                   ▼                                     │
 │ ┌────────────────────┐ ┌─────────────────────┐                ┌──────────────────┐
 │ │  AI Worker Pool    │ │  Background Worker  │                │ WhatsApp Service │
 │ │  (×3, async)       │ │  (async, dispatches │                │(Express, prebuilt│
 │ │ LangGraph +        │ │   by job type via   │                │  unofficial lib) │
 │ │ LangChain + LiteLLM│ │   TASK_HANDLERS)    │                └────────┬─────────┘
 │ └────────────────────┘ └──────────┬──────────┘                         ▲
 │                                   │         direct HTTP (outbound send,│
 │                                   └────────────────────────────────────┘
 │                                             via shared helper module)           
 │            
 │ ┌───────────────────────────────────────────────────┐
 │ │                     Postgres                      │
 └►│     schema defined at kickoff — only Main Service │
   │             ever reads/writes to it               │
   └───────────────────────────────────────────────────┘
```

## Components

### Frontend

| Attribute | Value |
|---|---|
| Stack | Vite + React |
| Delivery | Static files served by a lightweight static server, e.g. `serve` |
| Runtime | Separate container |
| Connection | Direct HTTPS to Main Service; no reverse proxy |
| Routing | React Router; fully separate from backend API routes |

### Main Service

| Attribute | Value |
|---|---|
| Stack | Django |
| Scope | Auth and Core Domain merged into one project |
| Apps | `users` and `core` |
| Database | The **only** component that touches Postgres; every other component uses a Main Service endpoint, no exceptions |
| Endpoints | `/auth/*`, `/api/*`, `GET /api/jobs/{job_id}`, `POST /api/whatsapp/inbound` |
| Jobs | Enqueues jobs to Redis |
| CORS | `django-cors-headers`, enabled for the frontend origin |
| User identity | `phone_number` is a candidate key so inbound WhatsApp messages can resolve to a user |
| Phone verification | Possible addition, not committed; likely more complexity than the hackathon needs |

### AI Worker Pool

| Attribute | Value |
|---|---|
| Stack | Async Python; no web framework |
| Replicas | 3 |
| Input | Consumes `ai_queue` only; never receives HTTP |
| AI stack | LangGraph/LangChain for orchestration; LiteLLM for model calls |
| Guardrails | Per-replica concurrency cap, per-job timeout, one retry with backoff |
| Configuration | Fetches prompts, model tiers, and fallback order through a small internal Main Service endpoint, not direct DB access |

### Background Worker

| Attribute | Value |
|---|---|
| Stack | Same async pattern as the AI Worker Pool |
| Input | Consumes `tasks_queue` |
| Dispatch | Internal `TASK_HANDLERS` map keyed on `job["type"]` |
| Example jobs | `generate_pdf`, `send_whatsapp_notification`, `send_otp` |
| Queue model | One homogeneous worker pool with many job types, not multiple worker pools sharing one queue |
| Status | Handler implementations are defined at kickoff; the dispatch pattern is fixed now |

### WhatsApp Service

| Attribute | Value |
|---|---|
| Stack | Express.js |
| Library | Pre-built unofficial library |
| Preparation | Built ahead of the hackathon; session kept logged in and warm before the demo |
| Official API | Official Business API approval lag ruled it out |
| QR risk | QR re-scans mid-demo are a real risk |
| Interface | Small HTTP API; not a queue consumer |
| Rate limiting | Light per-phone-number limit on inbound webhook traffic, protecting against a flood of junk before the demo |

#### WhatsApp Flows

| Flow | Behavior |
|---|---|
| Outbound endpoint | `POST /whatsapp/send`, called directly by AI Worker Pool and Background Worker, not through Main Service |
| Outbound rationale | Large payloads such as PDFs and media never touch Main Service's request thread. The unofficial library is inherently flaky, so a hung WhatsApp session cannot degrade Main Service's request/response cycle. |
| Outbound client | Both workers use one shared helper module, avoiding duplicate HTTP clients. |
| Inbound path | WhatsApp webhook → WhatsApp Service → Main Service `/api/whatsapp/inbound` |
| Inbound payload | Lightweight payload containing sender phone number, text, and a **media reference**; never raw file bytes |
| Inbound processing | Main Service validates the payload, resolves the phone number to a user, and enqueues a job. This is the untrusted-input boundary and the one path that goes through Main Service. |
| Media processing | The worker that picks up the job fetches actual media directly from WhatsApp Service while processing it, not through Django. |

### Redis

| Attribute | Value |
|---|---|
| Queues | `ai_queue` for AI Worker Pool only; `tasks_queue` for Background Worker only, with multi-type internal dispatch |
| Other data | Worker heartbeat keys |
| Operations | `RPUSH`/`BLPOP` |
| Exclusions | No Celery; no channel layer |

### Postgres

| Attribute | Value |
|---|---|
| Ownership | One shared database, owned exclusively by Main Service. `PGVector` gets a scoped, explicit exception. |
| Schema | Domain schema defined at kickoff |
| AI data | Config tables for prompts, model-tier mapping, and fallback order are decided now |
| WhatsApp data | The `phone_number` field is decided now |
| Access | Only Main Service ever reads or writes to it |

## Communication

| From → To | Transport | Contract and rationale |
|---|---|---|
| Frontend ↔ Main Service | REST/JSON over HTTPS | CORS-enabled |
| Main Service → AI/Background workers | Redis queues, not REST | Avoids blocking a request thread on slow work |
| AI/Background workers → WhatsApp Service | Direct HTTP, outbound | One shared client helper; no queue or Main Service hop; content is already decided and needs no validation |
| WhatsApp Service → Main Service | HTTP webhook, inbound only | Untrusted external input is validated by Main Service before anything is enqueued |
| AI Worker Pool → Main Service | Internal HTTP endpoint | Retrieves AI config instead of using direct Postgres access, keeping the database ownership rule intact. Cached briefly in-worker for approximately 30–60 seconds, so this is not a round-trip on every call. |
| Frontend → Main Service | Polling `GET /api/jobs/{job_id}` | Retrieves job status |

**Optional, not mandated:** Django Channels + WebSockets could replace polling with push-based updates if a specific need justifies it later. It is not part of the baseline.

## Contract-First Workflow

| Step | Activity |
|---|---|
| 1 | At kickoff, spend approximately 20–30 minutes writing OpenAPI-style contracts for every service endpoint: request/response shape, status codes, and error cases. Lock them before implementation. |
| 2 | Each service is implemented against its own contract, in parallel, by AI agents. |
| 3 | Gateway and React frontend build against the contract using mocked responses before real services are ready. |
| 4 | DRF auto-generates OpenAPI schemas through `drf-spectacular`; Swagger UI is served per service with no hand-written docs. |
| 5 | Afternoon integration swaps mocks for live calls instead of discovering what an API returns. |

## Deployment

| Attribute | Value |
|---|---|
| Target | Single VM |
| Command | `docker-compose up -d` |
| Containers | Frontend, Main Service, AI Worker Pool ×3, Background Worker, WhatsApp Service, Redis, and Postgres |
| WhatsApp Service | Runs as a normal service like everything else; no gating is needed because it is already built |

## Production-Readiness Checklist

- [ ] Health/liveness signal per component: Main Service `/health`; workers through Redis heartbeat; WhatsApp Service `/health`
- [ ] CI: lint + tests on push
- [ ] Structured logging
- [ ] `.env`-based configuration with no hardcoded secrets
- [ ] API docs auto-served through DRF + `drf-spectacular`
- [ ] One-command local spin-up and deploy
- [ ] WhatsApp session pre-authenticated and warm before the demo; not scanned live

## AI System

Full design — orchestration stack, model access, RAG, and security (agent-based, data-based, proactive threat management) — lives in docs/ai-system.md.

## Dynamic Configuration

Dynamic configuration is scoped deliberately because it is cheap and high-value, not because everything should be dynamic.

### Dynamic Values

| Value | Storage and management |
|---|---|
| Prompt text + version | DB-backed config models owned by Main Service; edited via Django Admin |
| Model tier → provider/model mapping | DB-backed config models owned by Main Service; edited via Django Admin |
| Fallback chain order | DB-backed config models owned by Main Service; edited via Django Admin |
| Per-prompt temperature/max_tokens | DB-backed config models owned by Main Service; edited via Django Admin |
| Admin UI | Django Admin provides a free CRUD UI; no custom dashboard is needed |
| Worker access | AI Worker Pool fetches current config from a small internal Main Service endpoint such as `GET /api/internal/ai-config`, not direct Postgres access. This keeps the database ownership rule intact. |
| Cache | Config is cached in-worker for approximately 30–60 seconds, so this is not a round-trip on every call. |

### Deliberately Not Dynamic

The orchestration graph structure, tool functions, and RAG chunking logic stay in code. Config values are dynamic; orchestration logic is not.

## Repository Structure

```
repo/
├── compose.yml
├── shared/
│   └── whatsapp_client.py      # imported by ai-worker and background-worker
├── frontend/
│   ├── Dockerfile
│   └── src/
├── main-service/
│   ├── Dockerfile
│   ├── manage.py
│   ├── users/
│   └── core/
├── ai-worker/
│   ├── Dockerfile
│   └── main.py
├── background-worker/
│   ├── Dockerfile
│   └── main.py
├── whatsapp-service/
│   ├── Dockerfile
│   └── index.js
└── docs/
    ├── architecture.md
    ├── sdlc.md
    ├── coding-guidelines.md
    ├── testing-guidelines.md
    ├── documentation-guide.md
    ├── ux-guide.md
    └── ui-guide.md
```

`ai-worker` and `background-worker` build with the repo root as Docker build context (not their own subfolder) specifically so their Dockerfiles can `COPY shared/` in — that's what makes one real shared module possible instead of two copies of the same HTTP client.

## Ownership Map

| Component | Owner |
|---|---|
| Main Service (Auth + Core) | TBD |
| AI Worker Pool | TBD |
| Background Worker | TBD |
| WhatsApp Service | TBD |
| Frontend | TBD |

## Hackathon-Day Timeline

| Time | Phase | Duration |
|---|---|---|
| 9:30–10:00 | Discovery & SRS | 30 min |
| 10:00–10:30 | Solution Design | 30 min |
| 10:30–10:45 | Component Design | 15 min |
| 10:45–12:30 | Implementation | 105 min |
| 12:30–13:00 | Component Testing | 30 min |
| 13:00–14:00 | *Lunch* | — |
| 14:00–15:00 | Integration & System Testing | 60 min |
| 15:00–15:20 | Refinement | 20 min |
| 15:20–15:45 | Documentation | 25 min |
| 15:45–16:00 | Presentation & Submission | 15 min |
