# Software Requirements Specification (SRS)
## AI Banking Customer Support System

**Project:** CWA Ship Karachi 2026 — Production-Grade AI Product  
**Phase:** SDLC Phase 1 (Discovery & SRS Generation)  
**Status:** Approved Baseline  
**Governing Documents:** [architecture-v3.md](file:///c:/Users/kaaif/Documents/Github/New%20folder/bank-customer-support/docs/architecture-v3.md), [ai-system.md](file:///c:/Users/kaaif/Documents/Github/New%20folder/bank-customer-support/docs/ai-system.md), [project-info.md](file:///c:/Users/kaaif/Documents/Github/New%20folder/bank-customer-support/docs/project-info.md), [sdlc.md](file:///c:/Users/kaaif/Documents/Github/New%20folder/bank-customer-support/docs/sdlc.md)

---

## 1. Problem Statement & Purpose

### 1.1 Problem Statement
Retail banking customers frequently face long wait times, rigid IVR trees, and cumbersome mobile apps for routine operations (balance checks, transaction clarification, fund transfers, bill payments, card controls, and dispute filing). Traditional customer service operations are costly, labor-intensive, and unavailable 24/7.

### 1.2 Purpose & Vision
Build a secure, multichannel, AI-powered banking customer-support system serving customers via Web and WhatsApp. The system automates routine requests using a conversational assistant orchestrated by LangGraph, while strictly enforcing enterprise banking guardrails: **the AI never accesses the database directly and never executes state-altering transactions without explicit confirmation or human authorization**.

---

## 2. Project Scope

### 2.1 In-Scope (MVP Baseline)
1. **Multichannel Conversational Support:** Authenticated self-service Web Portal and WhatsApp assistant.
2. **Core Banking Operations:**
   - Account balance inquiries and summary cards.
   - Transaction search, natural language filtering, and plain-English merchant explanations.
   - Account/Beneficiary transfers with mandatory two-phase explicit confirmation. (Only beneficiary transfers through whatsapp)
   - Utility bill inquiries and payments (e.g., K-Electric, Sui Gas, StormFiber).
   - Payment card controls (freeze/unfreeze and permanent lost/stolen block).
   - Dispute and fraud case intake with ticket generation.
3. **Human-In-The-Loop (HITL) & Role-Based Portals:**
   - Support Agent portal: live chat takeover / human handoff.
   - Compliance Manager portal: high-value transfer reviews and dispute resolutions.
   - System Administrator portal: full-stack health, telemetry, and dynamic AI configuration.
4. **Security & Guardrails:**
   - Pre-LLM prompt injection heuristic scanner.
   - Post-LLM leakage redaction filter.
   - Role-Based Access Control (RBAC) and strict API-level data ownership checks (`account.user == request.user`).
   - Immutable audit logs and full-stack telemetry.

### 2.2 Explicitly Out-of-Scope
- Real money settlement networks (1LINK, RAAST, SWIFT) — transactions are simulated via the internal Core Banking Engine.
- Physical branch operations (physical cash handling, paper cheque clearing).
- Lending, mortgage underwriting, wealth management, and foreign exchange trading.
- Voice/telephony IVR (text-based conversational channels only).
- Official Meta WhatsApp Business Cloud API onboarding (using local Express WhatsApp service container).

---

## 3. User Personas & Role-Based Access Control (RBAC)

All human users and automated system actors authenticate against a single unified identity model (`users_user`) governed by the `role` attribute:

| Role | Target Actor | Permissions & Responsibilities |
|---|---|---|
| **`CUSTOMER`** | Retail Banking Customer | Authenticates via Web (credentials/JWT) or WhatsApp (phone number). Access strictly restricted to own accounts, cards, beneficiaries, transactions, and chat sessions. |
| **`SUPPORT_AGENT`** | Frontline Support Staff | Views active customer sessions, executes one-click human handoff takeover, accesses read-only customer 360 overview (masked PII), and updates service tickets. |
| **`COMPLIANCE_MANAGER`** | Risk & Operations Staff | Reviews and authorizes Level 2 HITL actions (high-value transfers, out-of-pattern spending), adjudicates dispute/fraud cases, and reviews account limits. |
| **`SYSTEM_ADMIN`** | Infrastructure & Tech Admin | Full system oversight: inspects full-stack telemetry (Main Service, Workers, WhatsApp, AI), manages staff credentials, and adjusts dynamic AI configurations via Django Admin. |
| **`AI_AGENT`** | Automated System Actor | System user identity with an actual `user_id` for database auditability and foreign key integrity. Operates strictly under scoped tool permissions per graph node. |

---

## 4. Functional Requirements

### 4.1 Authentication & Session Management
- **FR-1.1 (Web Auth):** The system shall authenticate customers and staff using secure JWT-based credentials with automatic session expiry.
- **FR-1.2 (WhatsApp Identity):** The system shall resolve inbound WhatsApp messages to customer accounts using verified unique `phone_number` records. Only the number registered on the customer account can be used for whatsapp access.
- **FR-1.3 (Tenant Data Isolation):** The backend shall validate data ownership on every API endpoint (`record.user_id == request.user.id`). Any attempt to access unauthorized accounts (IDOR) shall be rejected with `403 Forbidden` and logged in the Security Audit Log.

### 4.2 Account & Balance Inquiries
- **FR-2.1 (Balance Retrieval):** Customers shall be able to query available balance, ledger balance, account type, and currency in natural language.
- **FR-2.2 (Multi-Account Disambiguation):** When a customer holds multiple accounts (e.g., Current and Savings), the agent shall prompt the customer to specify which account to check.
- **FR-2.3 (Privacy Display):** The Web Portal shall provide a privacy mask toggle for account numbers and balances.

### 4.3 Transaction History & Explanation
- **FR-3.1 (Natural Language Filtering):** Customers shall be able to filter transactions by date ranges, amount thresholds, categories (dining, utilities, transfers), and transaction types (debit/credit).
- **FR-3.2 (Transaction Explanation):** The agent shall explain transaction entries (merchant codes, fees, taxes) in plain English using stored database metadata.
- **FR-3.3 (Zero Hallucination Rule):** The agent shall never invent merchant details not present in the banking database. Unidentified transactions shall trigger an offer to dispute or freeze the card.

### 4.4 Money Transfers (Two-Phase Commit)
- **FR-4.1 (Beneficiary Disambiguation):** The agent shall resolve recipient names against saved beneficiaries. If multiple matches or zero matches exist, the agent shall prompt for clarification. 
- **FR-4.2 (Balance & Limit Validation):** The system shall verify available balance and enforce the customer's `daily_transfer_limit` and `per_transaction_limit` before staging any transfer.
- **FR-4.3 (Staged Confirmation):** The AI shall never execute a transfer directly. The Main Service shall create a short-lived `core_pendingaction` record (5-minute TTL) and render a structured confirmation card (Recipient, Masked Account, Amount, Fee).
- **FR-4.4 (Explicit Execution):** Transfers shall execute only when the customer provides explicit confirmation (clicking `[Confirm Transfer]` on Web or replying `CONFIRM <amount>` on WhatsApp).
- **FR-4.5 (Idempotent Execution):** Every transfer execution request shall use an idempotency token to prevent duplicate debits from network retries.
- **FR-4.5 (Transfer Reciept):** The agent should also provide a transaction reciept upon a successful transfer.


### 4.5 Utility Bill Payments
- **FR-5.1 (Biller Inquiry):** Customers shall be able to check outstanding utility bills (electricity, gas, telecom, internet) using registered billers and consumer numbers.
- **FR-5.2 (Bill Payment Execution):** Upon customer confirmation, the system shall deduct funds from the chosen account, mark the bill as paid, and return an official payment reference receipt.

### 4.6 Card Management
- **FR-6.1 (Temporary Freeze / Unfreeze):** Customers shall be able to instantly toggle card status between `ACTIVE` and `FROZEN`.
- **FR-6.2 (Lost / Stolen Permanent Block):** Customers shall be able to permanently block compromised cards (`BLOCKED_LOST`). The agent shall explain that blocking is irreversible and initiate a card replacement workflow. Blocking request must immediately freeze the card, with the delayed permanant block after 7 days. The request should be able to be cancelled within 7 days.

### 4.7 Dispute & Fraud Intake
- **FR-7.1 (Dispute Initiation):** When a customer reports an unrecognized or fraudulent charge, the agent shall locate the transaction, log customer notes, and create a `core_servicerequest` ticket with status `INVESTIGATING`.
- **FR-7.2 (Immediate Card Protection):** The agent shall immediately offer to freeze the card associated with the disputed transaction.
- **FR-7.3 (Auto-Escalation):** The dispute ticket shall be routed to the Compliance Manager HITL review queue. The agent shall not make autonomous refund commitments.

### 4.8 Human-in-the-Loop (HITL) & Staff Operations
- **FR-8.1 (Customer Step-Up Review):** Transfers exceeding high-value thresholds (e.g. > Rs. 50,000) shall require step-up re-authentication.
- **FR-8.2 (Compliance Approvals Queue):** High-risk transfers and dispute claims shall be queued in the Compliance Manager portal for manual approval/rejection.
- **FR-8.3 (Human Handoff):** Customers may request a human representative at any point. The Support Agent shall be able to take over the session seamlessly, disabling AI generation for that thread.

### 4.9 System Observability & Dynamic Configuration
- **FR-9.1 (Full-Stack Observability):** The System Admin portal shall display metrics across 4 tiers: Main Service API health, Redis worker queue depths/heartbeats, WhatsApp gateway connectivity, and AI token/cost telemetry.
- **FR-9.2 (Dynamic AI Tuning):** Administrators shall be able to update prompt versions, model tier routings (`fast` vs `smart`), temperature, and fallback chains via Django Admin without container restarts.

---

## 5. Non-Functional Requirements (NFRs)

### 5.1 Security & Compliance
- **NFR-1.1 (Least Privilege):** AI Workers and Background Workers shall have zero direct access to PostgreSQL credentials; all data interactions must pass through authenticated Main Service internal endpoints. All roles (human/ai) must be given the minimum required privilege.
- **NFR-1.2 (Input Guardrails):** Every incoming user prompt shall pass through an injection detection heuristic to neutralize jailbreak attempts and system prompt extraction attacks.
- **NFR-1.3 (Output Guardrails):** Outbound AI responses shall pass through an automated scanner to block PII leakage (unmasked PANs, credentials, internal server paths).
- **NFR-1.4 (Immutable Audit Trail):** All financial transactions, administrative actions, and security triggers shall write to immutable audit tables (`core_auditlog`, `core_aitelemetry`).

### 5.2 Performance & Reliability
- **NFR-2.1 (Response Times):** Read queries (balance, transaction list) must respond within 300 milliseconds (p99). Conversational AI generations shall stream or return first-token within 1500 milliseconds. The application shall utilize visual loading/typing indicators.
- **NFR-2.2 (Worker Fault Tolerance):** Worker pool tasks shall have a defined execution timeout according to the type of worker, single-retry backoff, and dead-letter queue routing to prevent queue poisoning.
- **NFR-2.3 (LLM High Availability):** LiteLLM shall maintain multi-provider fallback chains (e.g., Primary: OpenAI -> Fallback: Claude/Groq) to ensure zero conversational interruption during provider throttling.

---

## 6. MVP vs. Stretch Matrix

| Feature / Capability | Priority | Delivery Phase | Notes |
|---|---|---|---|
| Customer Web Portal (Dashboard & Chat) | **Must-Have** | MVP Baseline | React + Tailwind |
| Core Banking Engine (Accounts, Txns, Cards) | **Must-Have** | MVP Baseline | Django Core App |
| Balance & Transaction Filtering NLP | **Must-Have** | MVP Baseline | LangGraph Worker |
| Staged Transfer with Two-Phase Confirm | **Must-Have** | MVP Baseline | `pending_action` workflow |
| Card Freeze / Unfreeze & Lost Block | **Must-Have** | MVP Baseline | Real-time card status toggle |
| Basic Dispute Intake & Ticket Generation | **Must-Have** | MVP Baseline | Creates `core_servicerequest` |
| WhatsApp Bidirectional Chat Integration | **Must-Have** | MVP Baseline | Express WhatsApp Service |
| Pre-LLM Injection & Output Guardrails | **Must-Have** | MVP Baseline | Security boundary |
| Role-Based Admin & Full-Stack Telemetry | **Must-Have** | MVP Baseline | Agent, Compliance, Admin |
| Dynamic AI Prompt & Model Config | **Must-Have** | MVP Baseline | Django Admin backed |
| Real-time WebSocket Push (Channels) | *Could have* | If time allows | Replaces polling |
| RAG Semantic Search for Bank Policies | *Stretch* | Phase 4/6 Stretch | pgvector integration |
| PDF Account Statement Generation | *Stretch* | Phase 4/6 Stretch | Background Worker PDF dispatch |

---

## 7. Traceability & Next Phase Deliverables

This SRS formally concludes **SDLC Phase 1 (Discovery & SRS Generation)**.
- **Next Phase:** **SDLC Phase 2 (Solution Design)**
- **Phase 2 Target:** Map SRS requirements to service models, define endpoints on Main Service (`users` and `core`), configure LangGraph worker states, and assign component ownership per [sdlc.md](file:///c:/Users/kaaif/Documents/Github/New%20folder/bank-customer-support/docs/sdlc.md).
