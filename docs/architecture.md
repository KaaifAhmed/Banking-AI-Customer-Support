# System Architecture (Domain-Specific)
## AI Banking Customer Support System

**Project:** CWA Ship Karachi 2026 — Production-Grade AI Product  
**Phase:** SDLC Phase 2 (Solution Design)  
**Status:** Updated Domain Architecture  
**Governing Documents:** [docs/srs.md](file:///c:/Users/kaaif/Documents/Github/Banking-AI-Customer-Support/docs/srs.md), [docs/system-design.md](file:///c:/Users/kaaif/Documents/Github/Banking-AI-Customer-Support/docs/system-design.md), [docs/pre-made/architecture-v3.md](file:///c:/Users/kaaif/Documents/Github/Banking-AI-Customer-Support/docs/pre-made/architecture-v3.md)

---

## 1. System Overview

This document adapts the baseline architecture from [docs/pre-made/architecture-v3.md](file:///c:/Users/kaaif/Documents/Github/Banking-AI-Customer-Support/docs/pre-made/architecture-v3.md) to the specific domain requirements of the **AI Banking Customer Support System** specified in [docs/srs.md](file:///c:/Users/kaaif/Documents/Github/Banking-AI-Customer-Support/docs/srs.md). For detailed relational schemas, API contracts, LangGraph state machine definitions, and execution flows, refer to the companion [docs/system-design.md](file:///c:/Users/kaaif/Documents/Github/Banking-AI-Customer-Support/docs/system-design.md).

```
                    ┌───────────────────┐
                    │   React Frontend  │
                    │ (Customer + Admin)│
                    └─────────┬─────────┘
                              │ HTTPS + CORS
                              ▼
    ┌───────────────────────────────────────────────────┐
 ┌──│                   Main Service (Django)           │
 │  │   /auth/*   /api/*   /api/whatsapp/inbound        │◄──────────────┐
 │  │   /api/actions/*     /api/admin/*                 │               │
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
 │            │                      │         direct HTTP (outbound send,│
 │            └──────────────────────┴────────────────────────────────────┘
 │                         via shared helper module (shared/whatsapp_client.py)
 │            
 │ ┌───────────────────────────────────────────────────┐
 │ │                     Postgres                      │
 └►│  Users, Accounts, Transactions, Beneficiaries,    │
   │  Cards, Bills, Disputes, HITL Actions, Telemetry  │
   │      - ONLY Main Service ever reads/writes to it  │
   └───────────────────────────────────────────────────┘
```

---

## 2. Component Boundaries & Domain Specialization

### 2.1 React Frontend (`frontend/`)
- **Customer Self-Service View:** Bank account summary, transaction history filter, interactive chat interface with widgets (account balance privacy toggle, interactive transfer confirmation cards).
- **Role-Based Admin View:** Support Agent live chat handoff roster, Compliance Manager HITL pending approvals queue, and System Admin full-stack telemetry monitoring.

### 2.2 Main Service (`main-service/`)
- **Django Apps:**
  - `users`: Unified identity model with RBAC roles (`CUSTOMER`, `SUPPORT_AGENT`, `COMPLIANCE_MANAGER`, `SYSTEM_ADMIN`, `AI_AGENT`), JWT authentication, and phone/CNIC resolution.
  - `core`: Core banking models (`Account`, `Transaction`, `Beneficiary`, `PaymentCard`, `Biller`, `Bill`, `ServiceRequest`), staged transactions (`PendingAction`), and audit logs (`SecurityAuditLog`, `AITelemetry`).
- **Database Access Law:** Strictly enforced — **only** Main Service connects to PostgreSQL.

### 2.3 AI Worker Pool (`ai-worker/`)
- **Stack:** LangGraph + LangChain + LiteLLM.
- **Queue Consumer:** Consumes `ai_queue` only. Does not serve HTTP.
- **Node-Scoped Tools:** Tools bound per graph node (inquiry nodes cannot execute transfers). Tool calls execute via Main Service internal endpoints.
- **Dynamic Config:** Fetches prompt versions, model tiers, and fallbacks from `GET /api/internal/ai-config` (caching strategy and duration to be finalized during the AI component design pass in Phase 4).

### 2.4 Background Worker (`background-worker/`)
- **Stack:** Async Python worker consuming `tasks_queue`.
- **Job Dispatch:** Handled via internal `TASK_HANDLERS` map (e.g. `generate_pdf`, `send_whatsapp_notification`).
- **Outbound WhatsApp:** Dispatches PDF links and notifications directly to WhatsApp Service via `shared/whatsapp_client.py`.

### 2.5 WhatsApp Service (`whatsapp-service/`)
- **Stack:** Node.js + Express.js.
- **Inbound Webhook:** Receives messages from WhatsApp Web session and dispatches lightweight metadata payload to Main Service `POST /api/whatsapp/inbound`.
- **Outbound HTTP API:** Receives direct HTTP requests on `POST /whatsapp/send` from workers.

---

## 3. SDLC Phase 2 Team Ownership Assignments

The project is driven by a 4-member team. Leadership and component ownership are distributed as follows:

| Team Member | Core Focus & Role | Owned Components & Directories | Key Deliverables for Phase 4 (Component Design) |
|---|---|---|---|
| **Kaaif** | **Project Lead & System Architect** | Cross-system architecture, `main-service/` core actions, and AI co-design with Javed (`ai-worker/`) | System cohesion, inter-service contracts, staged transaction logic, and AI prompt/tool contracts. |
| **Hamza** | **Backend & Infrastructure Lead** | `main-service/` (Django, Users, Core, DB migrations), Redis queues, and `background-worker/` | OpenAPI specs for `/auth/*` and `/api/*`, database schema migrations, Redis queue setup, and worker handlers. |
| **Javed** | **AI / LLM Lead** | `ai-worker/` (LangGraph, LiteLLM, Prompts, Tools) | LangGraph state graph schema, LiteLLM provider fallback configs, tool schemas, injection detection rules. |
| **Areeb** | **Frontend Lead** | `frontend/` (React, Vite, Tailwind CSS) | UI component wireframes, client-side API/envelope integration, interactive chat widgets, and Admin dashboards. |
