# System Design Document (SDD)
## AI Banking Customer Support System

**Project:** CWA Ship Karachi 2026 — Production-Grade AI Product  
**Phase:** SDLC Phase 2 (Solution Design)  
**Status:** Approved Baseline  
**Governing Documents:** [docs/srs.md](file:///c:/Users/kaaif/Documents/Github/Banking-AI-Customer-Support/docs/srs.md), [docs/pre-made/architecture-v3.md](file:///c:/Users/kaaif/Documents/Github/Banking-AI-Customer-Support/docs/pre-made/architecture-v3.md), [docs/pre-made/ai-system.md](file:///c:/Users/kaaif/Documents/Github/Banking-AI-Customer-Support/docs/pre-made/ai-system.md), [docs/project-info.md](file:///c:/Users/kaaif/Documents/Github/Banking-AI-Customer-Support/docs/project-info.md)

---

## 1. Executive Summary & Architecture Topology

This document maps the functional requirements from [docs/srs.md](file:///c:/Users/kaaif/Documents/Github/Banking-AI-Customer-Support/docs/srs.md) onto the baseline system architecture defined in [docs/pre-made/architecture-v3.md](file:///c:/Users/kaaif/Documents/Github/Banking-AI-Customer-Support/docs/pre-made/architecture-v3.md).

The system automates retail banking customer support across Web and WhatsApp channels through an asynchronous, decoupled, queue-driven architecture:
- **Main Service (Django):** The single authoritative owner of PostgreSQL and domain business logic.
- **AI Worker Pool (LangGraph + LiteLLM):** Consumes `ai_queue` exclusively. Performs multi-turn dialogue, parameter extraction, and scoped tool calling without direct database access.
- **Background Worker (Async Python):** Consumes `tasks_queue` for asynchronous jobs (e.g. PDF statement generation).
- **WhatsApp Service (Express.js):** Maintains active WhatsApp Web sessions, forwards inbound webhooks to Main Service, and provides outbound HTTP delivery.
- **Frontend (React + Vite):** Responsive customer portal and role-based operational dashboard.

```
                            ┌────────────────────────────────────────┐
                            │    React Frontend (Vite + Tailwind)    │
                            │   - Customer Portal (Chat + Summary)   │
                            │   - Role-Based Admin / HITL Dashboard  │
                            └───────────────────┬────────────────────┘
                                                │ HTTPS + CORS
                                                ▼
┌──────────────────┐  Inbound Webhook ┌───────────────────────────────────────────────────┐
│ WhatsApp Service │─────────────────►│              Main Service (Django REST)           │
│ (Express.js)     │  (Metadata Only) │  - Auth & RBAC (users)                            │
└────────┬─────────┘                  │  - Banking Core & Transactions (core)             │
         ▲                            │  - Webhook Endpoint (/api/whatsapp/inbound)       │
         │                            │  - Internal AI Config (/api/internal/ai-config)   │
         │                            └───────────┬───────────────────────────┬───────────┘
         │ Direct HTTP                            │ enqueues                  │ exclusive DB read/write
         │ Outbound Send                          ▼                           ▼
         │ (via shared                ┌───────────────────────┐   ┌───────────────────────┐
         │  helper client)            │       ai_queue        │   │      tasks_queue      │ (Redis)
         │                            └───────────┬───────────┘   └───────────┬───────────┘
         │                                        │                           │
         ├────────────────────────────────────────┼─────────────┐             │
         │                                        ▼             │             ▼
         │                            ┌───────────────────────┐ │ ┌───────────────────────┐
         │                            │  AI Worker Pool (×3)  │ │ │   Background Worker   │
         │                            │  - LangGraph Graph    │ │ │   - PDF Generator     │
         │                            │  - LiteLLM Router     │ │ │   - Outbound Notifier │
         │                            │  - Tool Binding Nodes │ │ │   - OTP Dispatcher    │
         │                            └───────────┬───────────┘ │ └───────────────────────┘
         │                                        │             │
         │                                        │ Scoped HTTP │ Internal Tool Calls
         └────────────────────────────────────────┴─────────────┴───────────────────────┐
                                                                                        │
                                      ┌─────────────────────────────────────────────────┴─┐
                                      │                     PostgreSQL                    │
                                      │  Owned exclusively by Main Service                │
                                      │  (Users, Core Banking, Sessions, Audit, Config)   │
                                      └───────────────────────────────────────────────────┘
```

---

## 2. Component Ownership & SRS Traceability

| Component | Technology | Primary Responsibilities | SRS Traceability |
|---|---|---|---|
| **Frontend** | React, Vite, Tailwind CSS, Lucide Icons | Customer dashboard, interactive chat widgets (chips, balance privacy toggle, confirmation cards), Support Agent live queue, Compliance HITL reviews, Admin telemetry metrics. | FR-1.1, FR-2.3, FR-4.4, FR-8.1–8.3, FR-9.1 |
| **Main Service** | Python 3.11, Django 5, Django REST Framework | User authentication, RBAC enforcement, PostgreSQL domain models, financial transactions, WhatsApp inbound validation, job enqueueing, internal API endpoints. | FR-1.1–1.3, FR-2.1–2.2, FR-4.2–4.5, FR-5.1–5.2, FR-6.1–6.2, FR-7.1–7.3, NFR-1.1, NFR-1.4 |
| **AI Worker Pool** | Async Python, LangGraph, LangChain, LiteLLM | Conversational orchestration, intent classification, multi-turn slot filling, input/output guardrails, scoped tool invocation via Main Service, outbound WhatsApp reply triggers. | FR-2.1, FR-3.1–3.3, FR-4.1, FR-4.3, FR-5.1, FR-6.1–6.2, FR-7.1–7.2, NFR-1.2–1.3, NFR-2.3 |
| **Background Worker** | Async Python, Redis Worker (`tasks_queue`) | Long-running asynchronous tasks (PDF account statement compilation, scheduled alerts, automated notifications). | FR-8.1, Stretch Matrix (PDF statements) |
| **WhatsApp Service** | Node.js, Express, `whatsapp-web.js` | Persistent WhatsApp Web session, QR authentication, webhook dispatch to Main Service, outbound message/media HTTP endpoint. | FR-1.2, WhatsApp Channel flows |
| **Redis** | Redis 7 | Message broker for `ai_queue` and `tasks_queue`, worker heartbeat tracking, transient rate-limit counters. | Architecture §"Redis", NFR-2.2 |
| **PostgreSQL** | Postgres 16 (+ pgvector for stretch RAG) | Relational persistence for accounts, transactions, users, chat logs, HITL pending actions, audit logs, and dynamic AI configuration. | Architecture §"Postgres", NFR-1.4 |

---

## 3. Database Schema Design (PostgreSQL / Main Service)

All tables are defined in Django under `users` and `core` applications. Foreign key relations and constraints ensure complete auditability.

```
                    ┌──────────────────┐
                    │    users_user    │
                    └────────┬─────────┘
                             │ 1:N
         ┌───────────────────┼───────────────────┬───────────────────┐
         │ 1:N               │ 1:N               │ 1:N               │ 1:N
         ▼                   ▼                   ▼                   ▼
┌──────────────────┐┌──────────────────┐┌──────────────────┐┌──────────────────┐
│   core_account   ││ core_beneficiary ││ core_chatsession ││core_servicerequest│
└────────┬─────────┘└──────────────────┘└────────┬─────────┘└──────────────────┘
         │ 1:N                                   │ 1:N
         ├───────────────────┐                   ▼
         ▼                   ▼          ┌──────────────────┐
┌──────────────────┐┌──────────────────┐│ core_chatmessage │
│ core_transaction ││    core_card     │└──────────────────┘
└──────────────────┘└──────────────────┘
```

### 3.1 `users` Application Models

#### `User` (`users_user`)
Standard Django User extended with full CNIC requirement and role-based attributes:
```python
class User(AbstractUser):
    # Roles are managed via Django's native auth.Group framework:
    # Standard Groups: 'Customer', 'SupportAgent', 'ComplianceManager', 'SystemAdmin', 'AIAgent'
    phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    cnic = models.CharField(max_length=15, unique=True)  # Required at account registration (e.g. '42101-1234567-1')
    kyc_status = models.CharField(
        max_length=20,
        choices=(("VERIFIED", "Verified"), ("PENDING", "Pending"), ("REJECTED", "Rejected")),
        default="VERIFIED",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def cnic_last4(self):
        digits = "".join(filter(str.isdigit, self.cnic or ""))
        return digits[-4:] if len(digits) >= 4 else ""

    @property
    def role(self):
        """Derives primary role directly from native Django Group membership."""
        group = self.groups.first()
        return group.name if group else "Customer"
```

---

### 3.2 `core` Application Models

#### `Account` (`core_account`)
```python
class Account(models.Model):
    ACCOUNT_TYPES = (("CURRENT", "Current Account"), ("SAVINGS", "Savings Account"))
    STATUS_CHOICES = (("ACTIVE", "Active"), ("FROZEN", "Frozen"), ("DORMANT", "Dormant"))

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="accounts")
    account_number = models.CharField(max_length=16, unique=True)
    iban = models.CharField(max_length=24, unique=True)
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPES, default="CURRENT")
    currency = models.CharField(max_length=3, default="PKR")
    available_balance = models.DecimalField(max_digits=14, decimal_places=2)
    current_balance = models.DecimalField(max_digits=14, decimal_places=2)
    daily_transfer_limit = models.DecimalField(max_digits=14, decimal_places=2, default=100000.00)
    per_transaction_limit = models.DecimalField(max_digits=14, decimal_places=2, default=50000.00)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="ACTIVE")
    created_at = models.DateTimeField(auto_now_add=True)
```

#### `Beneficiary` (`core_beneficiary`)
```python
class Beneficiary(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="beneficiaries")
    nickname = models.CharField(max_length=50)
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=24)
    is_verified = models.BooleanField(default=True)
    daily_limit = models.DecimalField(max_digits=12, decimal_places=2, default=50000.00)
```

#### `Transaction` (`core_transaction`)
```python
class Transaction(models.Model):
    TYPES = (("DEBIT", "Debit"), ("CREDIT", "Credit"))
    CATEGORIES = (
        ("TRANSFER", "Funds Transfer"),
        ("BILL_PAYMENT", "Bill Payment"),
        ("DINING", "Dining & Restaurants"),
        ("GROCERY", "Grocery & Shopping"),
        ("UTILITY", "Utilities"),
        ("FEE", "Taxes & Bank Fees"),
    )
    STATUS = (("COMPLETED", "Completed"), ("PENDING", "Pending"), ("FAILED", "Failed"), ("DISPUTED", "Disputed"))

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference_number = models.CharField(max_length=20, unique=True)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="transactions")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=6, choices=TYPES)
    category = models.CharField(max_length=20, choices=CATEGORIES)
    counterparty_name = models.CharField(max_length=100)
    description = models.CharField(max_length=255)
    timestamp = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=10, choices=STATUS, default="COMPLETED")
```

#### `PaymentCard` (`core_card`)
```python
class PaymentCard(models.Model):
    CARD_TYPES = (("DEBIT", "Debit Card"), ("CREDIT", "Credit Card"))
    STATUS_CHOICES = (
        ("ACTIVE", "Active"),
        ("FROZEN", "Temporarily Frozen"),
        ("BLOCKED_LOST", "Permanently Blocked"),
        ("EXPIRED", "Expired"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="cards")
    card_number_masked = models.CharField(max_length=19)  # **** **** **** 4821
    card_type = models.CharField(max_length=10, choices=CARD_TYPES, default="DEBIT")
    expiry_date = models.DateField()                      # Proper DateField (validated in API/UI as MM/YY)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="ACTIVE")
    daily_spend_limit = models.DecimalField(max_digits=12, decimal_places=2, default=50000.00)
    international_enabled = models.BooleanField(default=False)
```

#### `Biller` and `Bill` (`core_biller`, `core_bill`)
```python
class Biller(models.Model):
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50) # ELECTRICITY, GAS, TELECOM, WATER

class Bill(models.Model):
    biller = models.ForeignKey(Biller, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bills")
    consumer_number = models.CharField(max_length=50)
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
```

#### `ChatSession` and `ChatMessage` (`core_chatsession`, `core_chatmessage`)
```python
class ChatSession(models.Model):
    CHANNELS = (("WEB", "Web Portal"), ("WHATSAPP", "WhatsApp"))
    STATUS_CHOICES = (("ACTIVE", "Active"), ("ESCALATED_HUMAN", "Human Takeover"), ("CLOSED", "Closed"))

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_sessions")
    channel = models.CharField(max_length=10, choices=CHANNELS, default="WEB")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ACTIVE")
    is_verified = models.BooleanField(default=True) # False initially on WhatsApp until CNIC last 4 is validated
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class ChatMessage(models.Model):
    SENDER_TYPES = (("USER", "User"), ("AI_ASSISTANT", "AI Assistant"), ("HUMAN_AGENT", "Human Agent"), ("SYSTEM", "System"))

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    sender_type = models.CharField(max_length=15, choices=SENDER_TYPES)
    sender_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    content = models.TextField()
    metadata_json = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
```

#### `PendingAction` (`core_pendingaction`)
Governs two-phase commit actions and Level 2 HITL compliance reviews:
```python
class PendingAction(models.Model):
    ACTION_TYPES = (
        ("TRANSFER", "Funds Transfer"),
        ("BILL_PAYMENT", "Bill Payment"),
        ("CARD_BLOCK", "Permanent Card Block"),
        ("DISPUTE_SUBMISSION", "Transaction Dispute"),
    )
    STATUS_CHOICES = (
        ("AWAITING_USER", "Awaiting Customer Confirmation"),
        ("AWAITING_ADMIN", "Awaiting Compliance Approval"),
        ("COMPLETED", "Executed Successfully"),
        ("REJECTED", "Rejected / Cancelled"),
        ("EXPIRED", "Expired"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    payload_json = models.JSONField() # Holds verified amount, recipient_id, account_id
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="AWAITING_USER")
    expires_at = models.DateTimeField() # 5-minute TTL
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_actions")
    created_at = models.DateTimeField(auto_now_add=True)
```

#### `ServiceRequest` / Dispute Ticket (`core_servicerequest`)
```python
class ServiceRequest(models.Model):
    TYPES = (("DISPUTE_TRANSACTION", "Transaction Dispute"), ("STATEMENT_REQUEST", "Account Statement"), ("CARD_REPLACEMENT", "Card Replacement"))
    STATUS = (("PENDING_REVIEW", "Pending Review"), ("INVESTIGATING", "Investigating"), ("RESOLVED", "Resolved"), ("REJECTED", "Rejected"))

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_number = models.CharField(max_length=20, unique=True) # e.g. CMP-2026-0921
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    request_type = models.CharField(max_length=25, choices=TYPES)
    related_transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, blank=True)
    related_card = models.ForeignKey(PaymentCard, on_delete=models.SET_NULL, null=True, blank=True)
    reason_notes = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS, default="PENDING_REVIEW")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

#### Observability & Configuration Models (`core_aitelemetry`, `core_auditlog`, `core_aiconfig`)
- **`AITelemetry`:** Stores `job_id`, `user_id`, `agent_role`, `model`, `prompt_version`, `prompt_tokens`, `completion_tokens`, `latency_ms`, `cost_estimate`, `guard_flags`.
- **`SecurityAuditLog`:** Immutable record of admin logins, privilege escalations, IDOR blocks, and rate-limit triggers.
- **`AIConfig`:** Dynamic DB table managing prompt versions, model tiers (`fast` vs `smart`), fallback order, and temperature.

---

## 4. Backend Architecture Baseline (`main-service`)

The Main Service follows standard Django / DRF layered conventions, enforcing strong separation of concerns, transactional safety, and strict database isolation.

```
main-service/
├── config/
│   ├── settings.py          # Environment-backed Django settings
│   ├── urls.py              # Root router: /auth/*, /api/*, /health
│   ├── asgi.py & wsgi.py
├── users/
│   ├── models.py            # User identity, CNIC, phone (uses native Django Groups for RBAC)
│   ├── serializers.py       # Auth & Profile serializers
│   ├── views.py             # Login, Register, Refresh, Me
│   └── urls.py
├── core/
│   ├── models.py            # Accounts, Cards, Txns, Bills, Sessions, Disputes
│   ├── serializers.py       # Domain serializers & response envelopes
│   ├── views/
│   │   ├── banking.py       # Accounts, balances, transactions, cards, bills
│   │   ├── chat.py          # Chat message intake, polling, session management (enqueues to ai_queue)
│   │   ├── actions.py       # Staging & confirming transfers, bill payments, disputes
│   │   ├── admin_ops.py     # HITL approvals, takeover, system health overview
│   │   ├── internal.py      # Internal AI config & tool execution for workers
│   │   └── whatsapp.py      # WhatsApp inbound webhook (enqueues to ai_queue)
│   ├── services/            # Domain Business Logic Layer
│   │   ├── transfer_service.py  # Atomic transfer execution with select_for_update()
│   │   ├── card_service.py      # Card freeze/unfreeze/block state machine
│   │   └── dispute_service.py   # Dispute creation and HITL ticket routing
│   └── urls.py
```

### 4.1 Layered Architecture Pattern
1. **View Layer (DRF APIViews / ViewSets):**
   - Strictly responsible for HTTP parsing, auth verification via native Django `Group` permissions, serializer validation, and standard response envelope formatting.
   - Directly enqueues jobs to Redis (`ai_queue` and `tasks_queue`) without redundant service indirection.
   - Delegates domain banking mutations to the domain service layer.
2. **Native Django Groups for RBAC:**
   - Uses Django's built-in `auth.Group` and `auth.Permission` framework rather than custom permission boilerplate.
   - Roles (`Customer`, `SupportAgent`, `ComplianceManager`, `SystemAdmin`) are mapped directly to Django Groups.
   - Views verify access using Django's idiomatic group checks (e.g. `request.user.groups.filter(name="ComplianceManager").exists()`).
3. **Domain Service Layer (`core/services/`):**
   - Encapsulates critical financial invariants, limit validations, and state changes.
   - Keeps business logic strictly separated from HTTP handlers.
4. **Database Concurrency & Atomic Transaction Pattern:**
   - All financial mutations execute inside `django.db.transaction.atomic()` with `select_for_update()` to prevent race conditions:
   ```python
   # core/services/transfer_service.py
   @transaction.atomic
   def execute_staged_transfer(pending_action_id: str, user: User) -> Transaction:
       pending = PendingAction.objects.select_for_update().get(id=pending_action_id, user=user)
       if pending.status != "AWAITING_USER" or pending.expires_at < timezone.now():
           raise InvalidActionError("Action expired or invalid.")
       
       sender_acc = Account.objects.select_for_update().get(id=pending.payload_json["from_account_id"])
       if sender_acc.available_balance < pending.payload_json["amount"]:
           raise InsufficientFundsError("Insufficient balance.")
       
       sender_acc.available_balance -= pending.payload_json["amount"]
       sender_acc.current_balance -= pending.payload_json["amount"]
       sender_acc.save()

       txn = Transaction.objects.create(
           reference_number=generate_ref(),
           account=sender_acc,
           amount=pending.payload_json["amount"],
           transaction_type="DEBIT",
           category="TRANSFER",
           counterparty_name=pending.payload_json["recipient_name"],
           status="COMPLETED"
       )
       pending.status = "COMPLETED"
       pending.save()
       return txn
   ```
5. **Direct View-to-Queue Producer Pattern:**
   - Tasks are enqueued directly within the view (e.g. `chat.py` or `whatsapp.py`) using Redis `rpush`:
   ```python
   # Direct push in view when message is received
   job_payload = {
       "job_id": str(uuid.uuid4()),
       "session_id": str(session.id),
       "user_id": request.user.id,
       "message": content,
       "channel": session.channel,
       "enqueued_at": timezone.now().isoformat(),
   }
   redis_client.rpush("ai_queue", json.dumps(job_payload))
   ```
6. **Internal Worker Authentication:**
   - Workers communicate with internal endpoints (`/api/internal/*`) using a pre-shared header: `X-Internal-Secret: <SECRET_FROM_ENV>`. This ensures external web callers cannot reach internal configuration or execution endpoints.

---

## 5. API Endpoints & Contract Catalog

All API endpoints strictly return the standard response envelope:
```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

### 5.1 Route Hierarchy (Grouped by Domain)

To ensure maximum clarity and maintainability, endpoints are categorized into intuitive domain prefixes rather than a flat namespace:

```
/auth/*               --> User authentication, JWT, profile
/api/banking/*        --> Core banking accounts, transactions, cards, bills
/api/chat/*           --> Chat messages, sessions, polling
/api/actions/*        --> Staged operations (transfers, bill pay, freeze, dispute)
/api/admin/*          --> Role-based operations (HITL, takeover, system health)
/api/whatsapp/*       --> Inbound WhatsApp gateway webhook
/api/internal/*       --> Worker-only endpoints (AI config, internal tool execution)
```

#### 1. Authentication & Profile (`/auth/*`)
| Method | Endpoint | Description | Auth Scope |
|---|---|---|---|
| `POST` | `/auth/login/` | Issues JWT access & refresh tokens | Public |
| `POST` | `/auth/register/` | Registers customer (requires full CNIC, phone, email) | Public |
| `POST` | `/auth/refresh/` | Refreshes expired JWT | Public |
| `GET` | `/auth/me/` | Retrieves authenticated user profile, role, & permissions | `IsAuthenticated` |

#### 2. Core Banking Operations (`/api/banking/*`)
| Method | Endpoint | Description | Auth Scope |
|---|---|---|---|
| `GET` | `/api/banking/accounts/` | Lists customer's active bank accounts | Customer (Owner only) |
| `GET` | `/api/banking/accounts/{id}/balance/` | Returns available balance, ledger balance, & currency | Customer (Owner only) |
| `GET` | `/api/banking/transactions/` | Filters transactions by date, amount, category | Customer (Owner only) |
| `GET` | `/api/banking/beneficiaries/` | Lists saved transfer beneficiaries | Customer (Owner only) |
| `GET` | `/api/banking/cards/` | Lists masked payment cards | Customer (Owner only) |
| `GET` | `/api/banking/bills/` | Lists unpaid and recent utility bills | Customer (Owner only) |

#### 3. Conversational & Webhook (`/api/chat/*`, `/api/whatsapp/*`)
| Method | Endpoint | Description | Auth Scope |
|---|---|---|---|
| `POST` | `/api/chat/send/` | Web customer sends message; enqueues to `ai_queue` | `IsAuthenticated` |
| `GET` | `/api/chat/sessions/{id}/` | Polls chat session history and active status | `IsAuthenticated` |
| `GET` | `/api/jobs/{job_id}/` | Polls asynchronous job processing status | `IsAuthenticated` |
| `POST` | `/api/whatsapp/inbound/` | Webhook from WhatsApp Service; verifies phone, enqueues to `ai_queue` | Service Token |

#### 4. Transactional Actions & Staging (`/api/actions/*`)
| Method | Endpoint | Description | Auth Scope |
|---|---|---|---|
| `POST` | `/api/actions/stage-transfer/` | Validates balance/limit; generates `PendingAction` with 5-min TTL | Customer / Internal Worker |
| `POST` | `/api/actions/confirm-transfer/` | Executes staged transfer atomically upon matching `pending_action_id` | Customer / Internal Worker |
| `POST` | `/api/actions/pay-bill/` | Executes utility bill debit and marks bill paid | Customer / Internal Worker |
| `POST` | `/api/actions/card-status/` | Sets card status (`ACTIVE`, `FROZEN`, `BLOCKED_LOST`) | Customer / Internal Worker |
| `POST` | `/api/actions/dispute/` | Creates dispute ticket and routes to HITL queue | Customer / Internal Worker |

#### 5. Operations & Full-System Health (`/api/admin/*`)
| Method | Endpoint | Description | Auth Scope |
|---|---|---|---|
| `GET` | `/api/admin/system/health/` | Full-stack health: Postgres, Redis, Workers, WhatsApp | System Admin |
| `GET` | `/api/admin/system/components/` | Individual component uptime, latency, and error counts | System Admin |
| `GET` | `/api/admin/telemetry/` | Aggregated AI token usage, cost estimates, and latency percentiles | System Admin |
| `GET` | `/api/admin/audit-logs/` | System security audit log (auth events, IDOR attempts) | System Admin |
| `GET` | `/api/admin/hitl/pending/` | Lists pending Level 2 actions (high transfers, disputes) | Compliance Manager |
| `POST` | `/api/admin/hitl/{id}/approve/` | Authorizes pending action | Compliance Manager |
| `POST` | `/api/admin/hitl/{id}/reject/` | Rejects pending action with audit note | Compliance Manager |
| `POST` | `/api/admin/chat/{id}/takeover/` | Handoff toggle: shifts chat from AI to human agent | Support Agent |

#### 6. Internal Worker Endpoints (`/api/internal/*`)
| Method | Endpoint | Description | Auth Scope |
|---|---|---|---|
| `GET` | `/api/internal/ai-config/` | AI workers fetch active prompts, model tiers, and fallbacks | Internal Secret |
| `POST` | `/api/internal/actions/execute/` | AI workers invoke Main Service transactional tools | Internal Secret |

---

## 6. AI Worker Orchestration & LangGraph Baseline

The AI Worker Pool runs as an asynchronous Python worker pool (3 replicas) consuming `ai_queue`.

> [!NOTE]
> The graph structure below establishes the architectural contract boundaries and tool allowances. Specific prompt templates, token budgets, and node implementations will be detailed by the AI lead (Javed & Kaaif) during Phase 4/5.

```
                     ┌───────────────────────┐
                     │   Inbound AI Job      │
                     └───────────┬───────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │   guard_input_node    │ ──(Injection detected)──► [Log & Safe Rejection]
                     └───────────┬───────────┘
                                 │ (Clean Input)
                                 ▼
                     ┌───────────────────────┐
                     │  intent_router_node   │
                     └───────────┬───────────┘
                                 │
         ┌───────────────────────┼───────────────────────┬───────────────────────┐
         ▼                       ▼                       ▼                       ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  account_inquiry │    │ transfer_staging │    │ card_management  │    │  dispute_intake  │
│      node        │    │      node        │    │      node        │    │      node        │
└────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘
         │                       │                       │                       │
         │                       ▼                       │                       │
         │              ┌──────────────────┐             │                       │
         │              │confirmation_gate │             │                       │
         │              │      node        │             │                       │
         │              └────────┬─────────┘             │                       │
         │                       │                       │                       │
         └───────────────────────┼───────────────────────┴───────────────────────┘
                                 ▼
                     ┌───────────────────────┐
                     │   guard_output_node   │ ──(PII/Secret detected)─► [Redact Sensitive Data]
                     └───────────┬───────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │  Deliver to Customer  │
                     │ (Web Poll / WhatsApp) │
                     └───────────────────────┘
```

### 6.1 Strict Architectural Boundary for AI Tools
The AI Worker **never** connects directly to PostgreSQL or executes database statements. Every tool in the AI worker executes via scoped HTTP requests to the Main Service internal endpoints:
- `get_balance(account_id)` $\rightarrow$ calls `GET /api/banking/accounts/{id}/balance/`
- `stage_transfer(from_acc, to_acc, amount)` $\rightarrow$ calls `POST /api/actions/stage-transfer/`
- `confirm_transfer(pending_action_id)` $\rightarrow$ calls `POST /api/actions/confirm-transfer/`
- `set_card_status(card_id, status)` $\rightarrow$ calls `POST /api/actions/card-status/`
- `lodge_dispute(txn_id, notes)` $\rightarrow$ calls `POST /api/actions/dispute/`

---

## 7. End-to-End Execution Flows & Sequence Diagrams

### 7.1 Two-Phase Beneficiary Transfer Flow
```
Customer (Web/WA)          AI Worker (LangGraph)          Main Service                 PostgreSQL
      │                             │                          │                            │
      │ 1. "Send Rs. 5000 to Ahmed" │                          │                            │
      ├────────────────────────────►│                          │                            │
      │                             │ 2. HTTP POST             │                            │
      │                             │    /actions/stage-       │                            │
      │                             │    transfer/             │                            │
      │                             ├─────────────────────────►│ 3. Check Limits & Balance  │
      │                             │                          ├───────────────────────────►│
      │                             │                          │ 4. Save PendingAction      │
      │                             │ 5. Return Staged ID      │    (status: AWAITING_USER) │
      │                             │◄─────────────────────────┤◄───────────────────────────┤
      │ 6. Render Confirmation Card │                          │                            │
      │    (Recipient, Amt, Fee)    │                          │                            │
      │◄────────────────────────────┤                          │                            │
      │                             │                          │                            │
      │ 7. Explicit Confirm Action  │                          │                            │
      ├────────────────────────────►│                          │                            │
      │                             │ 8. HTTP POST             │                            │
      │                             │    /actions/confirm-     │                            │
      │                             │    transfer/ (Staged ID) │                            │
      │                             ├─────────────────────────►│ 9. Execute Atomic Transfer │
      │                             │                          │    (select_for_update,     │
      │                             │                          │     Debit sender,          │
      │                             │                          │     Credit recipient)      │
      │                             │                          ├───────────────────────────►│
      │                             │ 10. Return Ref: TRX-9812 │◄───────────────────────────┤
      │                             │◄─────────────────────────┤                            │
      │ 11. Transaction Receipt     │                          │                            │
      │◄────────────────────────────┤                          │                            │
```

---

### 7.2 WhatsApp CNIC Verification & Onboarding Flow
```
Customer (WhatsApp)         WhatsApp Service           Main Service              AI Worker Pool
      │                            │                        │                         │
      │ 1. "Hi" from +923001234567 │                        │                         │
      ├───────────────────────────►│ 2. POST /whatsapp/     │                         │
      │                            │    inbound webhook     │                         │
      │                            ├───────────────────────►│ 3. Resolve phone to User│
      │                            │                        │    Session exists? No.  │
      │                            │                        │    Create ChatSession   │
      │                            │                        │    (is_verified: False) │
      │                            │                        │ 4. Enqueue to ai_queue  │
      │                            │                        ├────────────────────────►│
      │                            │                        │                         │ 5. Verification Gate:
      │                            │ 6. Outbound WA Send    │                         │    "Please enter last
      │                            │    (via shared client) │                         │     4 digits of CNIC"
      │ 7. Prompt for CNIC last 4  │◄─────────────────────────────────────────────────┤
      │◄───────────────────────────┤                        │                         │
      │                            │                        │                         │
      │ 8. "4821"                  │                        │                         │
      ├───────────────────────────►│ 9. Webhook Inbound     │                         │
      │                            ├───────────────────────►│ 10. Match User.cnic_last4│
      │                            │                        │     is_verified = True  │
      │                            │                        │ 11. Enqueue to ai_queue │
      │                            │                        ├────────────────────────►│
      │                            │ 12. Outbound WA Send   │                         │ 13. Render Banking Menu
      │ 14. Welcome & Menu Options │◄─────────────────────────────────────────────────┤     (Balance, History)
      │◄───────────────────────────┤                        │                         │
```

---

### 7.3 Dispute & Emergency Card Freeze Flow (HITL Level 2)
```
Customer                    AI Worker                 Main Service              Postgres / Compliance
   │                             │                         │                           │
   │ 1. "I don't recognize       │                         │                           │
   │     this Rs. 25,000 charge" │                         │                           │
   ├────────────────────────────►│ 2. HTTP GET             │                           │
   │                             │    /banking/txns/{id}/  │                           │
   │                             ├────────────────────────►│ 3. Query DB Txn Record   │
   │                             │ 4. Return Txn Metadata  ├──────────────────────────►│
   │                             │◄────────────────────────┤◄──────────────────────────┤
   │ 5. Confirm Txn Details &    │                         │                           │
   │    Offer Card Freeze        │                         │                           │
   │◄────────────────────────────┤                         │                           │
   │                             │                         │                           │
   │ 6. "Yes, freeze my card     │                         │                           │
   │     and file dispute"       │                         │                           │
   ├────────────────────────────►│ 7. HTTP POST            │                           │
   │                             │    /actions/card-status/│                           │
   │                             ├────────────────────────►│ 8. UPDATE core_card       │
   │                             │                         │    SET status='FROZEN'    │
   │                             │ 9. Card Frozen OK       ├──────────────────────────►│
   │                             │◄────────────────────────┤                           │
   │                             │                         │                           │
   │                             │ 10. HTTP POST           │                           │
   │                             │     /actions/dispute/   │                           │
   │                             ├────────────────────────►│ 11. INSERT ServiceRequest │
   │                             │                         │     status: PENDING_REVIEW│
   │                             │ 12. Ticket CMP-2026-0812├──────────────────────────►│
   │                             │◄────────────────────────┤ 13. Push to HITL Queue    │
   │ 14. Dispute Reference       │                         ├──────────────────────────►│ (Compliance Review)
   │     CMP-2026-0812 & SLA     │                         │                           │
   │◄────────────────────────────┤                         │                           │
```

---

## 8. Frontend Architecture Baseline (`frontend/`)

The frontend is a single-page application built with **React 18 + Vite + Tailwind CSS**. It provides self-service banking for customers and operational portals for bank personnel.

### 8.1 View & Route Hierarchy
```
/                         --> Redirects to /login or /dashboard
/login                    --> Credentials login (Customer & Staff)
/register                 --> Customer self-registration (Name, Phone, Full CNIC, Email)
/dashboard                --> Customer Self-Service Portal
    ├── Summary Section   --> Balances (with privacy mask eye toggle), Cards summary
    ├── Chat Interface    --> Real-time conversational assistant, interactive widgets
    └── History Section   --> Filterable transaction statement
/admin/agent              --> Support Agent Live Chat Roster & Takeover Console
/admin/compliance         --> Compliance Manager HITL Pending Approvals (Disputes, High Transfers)
/admin/system             --> System Administrator Full-System Health & Telemetry Dashboard
```

### 8.2 Client-Side State & API Envelope Handling
- **API Client:** Standard Axios / fetch wrapper injecting JWT `Authorization: Bearer <token>`.
- **Response Handling:** Unwraps the standard envelope (`{ success, data, error }`). Displays non-intrusive toast notifications for error payloads.
- **State Management:** React Context (`AuthContext` for user session & role; `ChatContext` for active conversation and polling).
- **Polling Strategy:** When a message is sent to `/api/chat/send/`, the client polls `/api/jobs/{job_id}/` until status is `COMPLETED`, appending the assistant message to the chat feed.

---

## 9. Multi-Tier Observability & Monitoring Architecture

Observability is engineered across all four distributed tiers to ensure complete system transparency:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                SYSTEM OBSERVABILITY LAYERS                             │
├──────────────────┬──────────────────┬──────────────────┬───────────────────────────────┤
│ 1. Main Service  │ 2. Worker Queues │ 3. WhatsApp Gate │ 4. AI & LLM Telemetry         │
├──────────────────┼──────────────────┼──────────────────┼───────────────────────────────┤
│ • API Latency    │ • ai_queue depth │ • Session Health │ • Token Counts (in/out)       │
│   (p50, p95, p99)│ • tasks_queue    │   (Warm/QR/Down) │ • Cost Estimation (USD/PKR)   │
│ • HTTP 4xx / 5xx │   depth          │ • Inbound Webhook│ • Model Fallback Triggers     │
│ • DB Connection  │ • Worker Heart-  │   Latency        │   (OpenAI -> Claude -> Groq)  │
│   Pool Count     │   beat Ping      │ • Outbound Send  │ • Prompt Injection Attempts   │
│ • Security Audit │ • Job Processing │   Success Rate   │ • PII Output Redaction Flags  │
│   Log (IDOR, Auth│   Duration & DLQ │ • Phone Rate-    │ • Active Prompt Versions      │
│   Failures)      │                  │   Limit Counters │                               │
└──────────────────┴──────────────────┴──────────────────┴───────────────────────────────┘
```

---

## 10. SDLC Phase 2 Team Ownership Assignments

The project is executed by a 4-member team with clear ownership boundaries:

| Team Member | Role | Primary Responsibility | Directory Scope | Deliverable for Phase 4 (Component Design) |
|---|---|---|---|---|
| **Kaaif** | **Project Lead & System Architect** | System cohesion, core transactional logic, and AI co-design with Javed | `main-service/core/`, `ai-worker/` | System inter-service contracts, staged transaction schemas, AI prompt/tool contracts. |
| **Hamza** | **Backend & Infrastructure Lead** | Django backend architecture, Postgres models/migrations, Redis queues, background worker | `main-service/`, `background-worker/` | OpenAPI specs for `/auth/*` and `/api/*`, DB migration scripts, Redis worker consumer setup. |
| **Javed** | **AI / LLM Lead** | LangGraph orchestration, LiteLLM router, tool bindings, guardrail implementation | `ai-worker/` | LangGraph state graph schema, LiteLLM fallback chains, tool schemas, injection detection rules. |
| **Areeb** | **Frontend Lead** | React SPA, Tailwind UI components, chat drawer, customer & admin dashboards | `frontend/` | UI component wireframes, client-side API/envelope integration, interactive chat widgets. |

---

## 11. Traceability & Conclusion

This System Design Document establishes the complete technical blueprint, bridging **SDLC Phase 1 (SRS)** and **SDLC Phase 2 (Solution Design)**.
- **Next Step:** Proceed to **SDLC Phase 3 (Contract Locking: 10:20–10:30)**, where the team finalizes the shared OpenAPI contracts, followed by **SDLC Phase 4 (Component Design: 10:30–10:45)**.
