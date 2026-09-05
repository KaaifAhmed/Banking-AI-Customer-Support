# System Interface & OpenAPI Contracts Specification
## AI Banking Customer Support System

**Project:** CWA Ship Karachi 2026 — Production-Grade AI Product  
**Phase:** SDLC Phase 2 (Contract Locking)  
**Status:** **LOCKED BASELINE — IMMUTABLE CONTRACT**  
**Governing Documents:** [docs/srs.md](file:///c:/Users/kaaif/Documents/Github/Banking-AI-Customer-Support/docs/srs.md), [docs/system-design.md](file:///c:/Users/kaaif/Documents/Github/Banking-AI-Customer-Support/docs/system-design.md), [docs/architecture.md](file:///c:/Users/kaaif/Documents/Github/Banking-AI-Customer-Support/docs/architecture.md), [docs/pre-made/sdlc.md](file:///c:/Users/kaaif/Documents/Github/Banking-AI-Customer-Support/docs/pre-made/sdlc.md)

---

## 1. Governing Rules for Interface Contracts

1. **Immutability:** This contract is the **single source of truth** across all four team members. No endpoint path, method, field name, data type, or status code may be altered during implementation without explicit consensus.
2. **Standard Response Envelope:** Every REST response returned by the backend MUST adhere strictly to the response envelope:
   ```json
   {
     "success": true,
     "data": { ... },
     "error": null
   }
   ```
   Or upon failure:
   ```json
   {
     "success": false,
     "data": null,
     "error": {
       "code": "ERROR_CONSTANT",
       "message": "Human-readable explanation of error."
     }
   }
   ```
3. **Idempotency:** All monetary and state-altering actions accept an optional `Idempotency-Key` header (UUID) to prevent duplicate execution from network retries.
4. **Standard Error Codes:**
   - `AUTH_REQUIRED` (401): Missing or invalid JWT.
   - `FORBIDDEN_IDOR` (403): User attempted to access an account/resource they do not own.
   - `INSUFFICIENT_FUNDS` (400): Balance is less than debit amount.
   - `LIMIT_EXCEEDED` (400): Amount exceeds daily or per-transaction limit.
   - `ACTION_EXPIRED` (400): Staged action passed its 5-minute TTL.
   - `INVALID_ACTION` (400): Staged action already executed, rejected, or parameters altered.
   - `BILL_ALREADY_PAID` (400): Utility bill has no outstanding dues.
   - `CARD_LOCKED` (400): Card is permanently blocked (`BLOCKED_LOST`) and cannot be unfrozen.
   - `RATE_LIMITED` (429): Inbound message or request volume threshold exceeded.
   - `VALIDATION_ERROR` (400): Request schema or parameters failed validation.
   - `SERVER_ERROR` (500): Internal unhandled exception.

---

## 2. Authentication & Identity Contracts (`/auth/*`)

### `POST /auth/register/`
- **Description:** Registers a new retail customer account. Requires full 13/15-digit CNIC. Automatically assigns to the `Customer` Django Group.
- **Auth Scope:** `Public`
- **Request Body:**
  ```json
  {
    "username": "string (required, unique)",
    "password": "string (required, min 8 chars)",
    "full_name": "string (required)",
    "email": "string (required, email format)",
    "phone_number": "string (required, unique, E.164 e.g. +923001234567)",
    "cnic": "string (required, unique, format: XXXXX-XXXXXXX-X or 13 digits)"
  }
  ```
- **Success Response (`201 Created`):**
  ```json
  {
    "success": true,
    "data": {
      "user_id": 12,
      "username": "ahmed_khan",
      "full_name": "Ahmed Khan",
      "email": "ahmed@example.com",
      "phone_number": "+923001234567",
      "cnic": "42101-1234567-1",
      "cnic_last4": "5671",
      "role": "Customer"
    },
    "error": null
  }
  ```

---

### `POST /auth/login/`
- **Description:** Authenticates customer or staff member, returning JWT tokens and user profile summary.
- **Auth Scope:** `Public`
- **Request Body:**
  ```json
  {
    "username_or_phone": "string (required)",
    "password": "string (required)"
  }
  ```
- **Success Response (`200 OK`):**
  ```json
  {
    "success": true,
    "data": {
      "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
      "refresh_token": "eyJhbGciOiJIUzI1NiIsIn...",
      "expires_in": 3600,
      "user": {
        "id": 12,
        "username": "ahmed_khan",
        "full_name": "Ahmed Khan",
        "phone_number": "+923001234567",
        "role": "Customer",
        "groups": ["Customer"]
      }
    },
    "error": null
  }
  ```

---

### `POST /auth/refresh/`
- **Description:** Refreshes an expired JWT access token using a valid refresh token.
- **Auth Scope:** `Public`
- **Request Body:**
  ```json
  {
    "refresh_token": "string (required)"
  }
  ```
- **Success Response (`200 OK`):**
  ```json
  {
    "success": true,
    "data": {
      "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
      "expires_in": 3600
    },
    "error": null
  }
  ```

---

### `GET /auth/me/`
- **Description:** Returns the authenticated user profile, linked accounts, and active roles.
- **Auth Scope:** `IsAuthenticated`
- **Success Response (`200 OK`):**
  ```json
  {
    "success": true,
    "data": {
      "id": 12,
      "username": "ahmed_khan",
      "full_name": "Ahmed Khan",
      "email": "ahmed@example.com",
      "phone_number": "+923001234567",
      "cnic_masked": "42101-*******-1",
      "cnic_last4": "5671",
      "role": "Customer",
      "groups": ["Customer"],
      "accounts": [
        {
          "id": "c7a8b9e1-2f34-4b56-8a90-1c2d3e4f5a6b",
          "account_number": "0102030405060708",
          "iban": "PK36MEZN0001020304050608",
          "account_type": "CURRENT",
          "currency": "PKR",
          "status": "ACTIVE"
        }
      ]
    },
    "error": null
  }
  ```

---

## 3. Core Banking Contracts (`/api/banking/*`)

### `GET /api/banking/accounts/`
- **Description:** Returns all bank accounts belonging to the authenticated customer.
- **Auth Scope:** `Customer (Owner)`
- **Success Response (`200 OK`):**
  ```json
  {
    "success": true,
    "data": [
      {
        "id": "c7a8b9e1-2f34-4b56-8a90-1c2d3e4f5a6b",
        "account_number": "0102030405060708",
        "account_number_masked": "**** **** **** 0708",
        "iban": "PK36MEZN0001020304050608",
        "account_type": "CURRENT",
        "currency": "PKR",
        "available_balance": "84500.50",
        "current_balance": "85000.00",
        "daily_transfer_limit": "100000.00",
        "per_transaction_limit": "50000.00",
        "status": "ACTIVE"
      }
    ],
    "error": null
  }
  ```

---

### `GET /api/banking/accounts/{id}/balance/`
- **Description:** Returns live balance breakdown and spend limits for a specific account.
- **Auth Scope:** `Customer (Owner only)`
- **Success Response (`200 OK`):**
  ```json
  {
    "success": true,
    "data": {
      "account_id": "c7a8b9e1-2f34-4b56-8a90-1c2d3e4f5a6b",
      "account_number_masked": "**** **** **** 0708",
      "account_type": "CURRENT",
      "currency": "PKR",
      "available_balance": "84500.50",
      "current_balance": "85000.00",
      "holds_balance": "499.50",
      "daily_limit_remaining": "95000.00",
      "status": "ACTIVE"
    },
    "error": null
  }
  ```

---

### `GET /api/banking/transactions/`
- **Description:** Lists customer transactions with flexible filtering by date, amount, category, and type.
- **Auth Scope:** `Customer (Owner only)`
- **Query Parameters:**
  - `account_id`: string (optional, defaults to primary account)
  - `start_date`: string (optional, format `YYYY-MM-DD`)
  - `end_date`: string (optional, format `YYYY-MM-DD`)
  - `min_amount`: number (optional)
  - `max_amount`: number (optional)
  - `category`: string (optional, e.g. `DINING`, `UTILITY`, `TRANSFER`, `GROCERY`)
  - `type`: string (optional, `DEBIT` or `CREDIT`)
  - `limit`: integer (optional, default: 20)
- **Success Response (`200 OK`):**
  ```json
  {
    "success": true,
    "data": {
      "total_count": 2,
      "aggregate_amount": "-9500.00",
      "transactions": [
        {
          "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
          "reference_number": "TRX-2026-9812",
          "amount": "5000.00",
          "transaction_type": "DEBIT",
          "category": "TRANSFER",
          "counterparty_name": "Ahmed Khan",
          "description": "Funds transfer to Venus Account ****4821",
          "timestamp": "2026-09-04T14:32:00Z",
          "status": "COMPLETED"
        },
        {
          "id": "e21ba29a-11bb-4231-9988-112233445566",
          "reference_number": "TRX-2026-9801",
          "amount": "4500.00",
          "transaction_type": "DEBIT",
          "category": "DINING",
          "counterparty_name": "Kolachi Restaurant Clifton",
          "description": "POS Purchase at Kolachi Karachi",
          "timestamp": "2026-09-03T20:15:00Z",
          "status": "COMPLETED"
        }
      ]
    },
    "error": null
  }
  ```

---

### `GET /api/banking/transactions/{id}/`
- **Description:** Returns detailed transaction metadata for transaction explanation workflows.
- **Auth Scope:** `Customer (Owner only)`
- **Success Response (`200 OK`):**
  ```json
  {
    "success": true,
    "data": {
      "id": "e21ba29a-11bb-4231-9988-112233445566",
      "reference_number": "TRX-2026-9801",
      "amount": "4500.00",
      "currency": "PKR",
      "transaction_type": "DEBIT",
      "category": "DINING",
      "counterparty_name": "Kolachi Restaurant Clifton",
      "channel": "POS_TERMINAL",
      "merchant_code": "MCC-5812",
      "tax_deducted": "0.00",
      "bank_fee": "0.00",
      "timestamp": "2026-09-03T20:15:00Z",
      "status": "COMPLETED",
      "is_disputed": false
    },
    "error": null
  }
  ```

---

### `GET /api/banking/beneficiaries/`
- **Description:** Lists saved beneficiaries for the authenticated customer.
- **Auth Scope:** `Customer (Owner only)`
- **Success Response (`200 OK`):**
  ```json
  {
    "success": true,
    "data": [
      {
        "id": 1,
        "nickname": "Ahmed Khan",
        "bank_name": "Venus Bank",
        "account_number_masked": "**** **** **** 4821",
        "daily_limit": "50000.00",
        "is_verified": true
      },
      {
        "id": 2,
        "nickname": "Bilal Ali",
        "bank_name": "Standard Chartered",
        "account_number_masked": "**** **** **** 9012",
        "daily_limit": "50000.00",
        "is_verified": true
      }
    ],
    "error": null
  }
  ```

---

### `GET /api/banking/cards/`
- **Description:** Lists payment cards linked to the customer's accounts.
- **Auth Scope:** `Customer (Owner only)`
- **Success Response (`200 OK`):**
  ```json
  {
    "success": true,
    "data": [
      {
        "id": "d1e2f3a4-b5c6-4789-8012-3456789abcde",
        "account_id": "c7a8b9e1-2f34-4b56-8a90-1c2d3e4f5a6b",
        "card_number_masked": "**** **** **** 4821",
        "card_type": "DEBIT",
        "expiry_date": "2028-12-31",
        "expiry_display": "12/28",
        "status": "ACTIVE",
        "daily_spend_limit": "50000.00",
        "international_enabled": false
      }
    ],
    "error": null
  }
  ```

---

### `GET /api/banking/bills/`
- **Description:** Lists registered utility billers and unpaid/recent bills with optional filtering by payment status, category, and due date.
- **Auth Scope:** `Customer (Owner only)`
- **Request Headers:** `Authorization: Bearer <jwt>`
- **Query Parameters:**
  - `category` (optional string): `ELECTRICITY` | `GAS` | `WATER` | `TELECOM` | `INTERNET` | `GOVERNMENT`
  - `is_paid` (optional boolean): Filter by payment status (`true` or `false`)
  - `due_before` (optional date string, `YYYY-MM-DD`): Return bills due on or before this date
  - `due_after` (optional date string, `YYYY-MM-DD`): Return bills due on or after this date
  - `limit` (optional integer): Maximum bills to return (default: `20`, max: `100`)
- **Success Response (`200 OK`):**
  ```json
  {
    "success": true,
    "data": [
      {
        "bill_id": 101,
        "biller_name": "K-Electric",
        "category": "ELECTRICITY",
        "consumer_number": "0400012345678",
        "amount": "8450.00",
        "due_date": "2026-09-15",
        "is_paid": false
      },
      {
        "bill_id": 102,
        "biller_name": "StormFiber",
        "category": "TELECOM",
        "consumer_number": "SF-99128",
        "amount": "3200.00",
        "due_date": "2026-09-20",
        "is_paid": false
      }
    ],
    "error": null
  }
  ```

---

## 4. Conversational & Webhook Contracts (`/api/chat/*`, `/api/whatsapp/*`)

### `POST /api/chat/send/`
- **Description:** Receives a user message from the Web Portal, creates a message record in Postgres, and enqueues a job to Redis `ai_queue`.
- **Auth Scope:** `IsAuthenticated`
- **Request Body:**
  ```json
  {
    "session_id": "string (optional UUID, creates new session if omitted)",
    "message": "string (required, max 1000 chars)"
  }
  ```
- **Success Response (`202 Accepted`):**
  ```json
  {
    "success": true,
    "data": {
      "job_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "status": "PENDING"
    },
    "error": null
  }
  ```

---

### `GET /api/chat/jobs/{job_id}/` (Alias: `GET /api/jobs/{job_id}/`)
- **Description:** Polls the asynchronous processing status and completed result of an AI chat job.
- **Auth Scope:** `Customer (Owner of job/session)`
- **Request Headers:** `Authorization: Bearer <jwt>`
- **Security & Ownership Enforcement:**
  - The endpoint **strictly verifies job ownership**: `job.session.user_id == request.user.id`.
  - If `job_id` belongs to another customer or session, the server returns `404 Not Found` (`JOB_NOT_FOUND`) to prevent enumeration attacks and unauthorized data exfiltration.
  - Cross-user job probing is automatically logged as a security event in `AuditLog`.
- **Success Response (`200 OK` - Completed with Rich Widget):**
  ```json
  {
    "success": true,
    "data": {
      "job_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "status": "COMPLETED",
      "response": {
        "text": "Your available balance in your Current Account is Rs. 84,500.50.",
        "rich_widget": {
          "widget_type": "BALANCE_CARD",
          "payload": {
            "account_id": "acc_01",
            "account_title": "Muhammad Kaaif",
            "account_number_masked": "**** **** **** 0708",
            "account_type": "CURRENT",
            "available_balance": "84500.50",
            "currency": "PKR",
            "as_of": "2026-09-05T20:15:00Z"
          }
        }
      }
    },
    "error": null
  }
  ```
- **Success Response (`200 OK` - Processing):**
  ```json
  {
    "success": true,
    "data": {
      "job_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "status": "PROCESSING",
      "response": null
    },
    "error": null
  }
  ```
- **Error Responses:**
  - `401 Unauthorized` (`UNAUTHORIZED`): Missing or invalid JWT.
  - `404 Not Found` (`JOB_NOT_FOUND`): Job does not exist or does not belong to the authenticated user.

---

### `GET /api/chat/sessions/{id}/`
- **Description:** Retrieves the chronological chat message history for a session.
- **Auth Scope:** `IsAuthenticated`
- **Success Response (`200 OK`):**
  ```json
  {
    "success": true,
    "data": {
      "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "channel": "WEB",
      "status": "ACTIVE",
      "is_verified": true,
      "messages": [
        {
          "id": 1,
          "sender_type": "USER",
          "content": "Check my balance",
          "metadata": {},
          "timestamp": "2026-09-04T10:00:00Z"
        },
        {
          "id": 2,
          "sender_type": "AI_ASSISTANT",
          "content": "Your available balance in your Current Account is Rs. 84,500.50.",
          "metadata": {
            "rich_widget": {
              "widget_type": "BALANCE_CARD",
              "payload": {
                "account_id": "acc_01",
                "account_title": "Muhammad Kaaif",
                "account_number_masked": "**** **** **** 0708",
                "account_type": "CURRENT",
                "available_balance": "84500.50",
                "currency": "PKR",
                "as_of": "2026-09-05T20:15:00Z"
              }
            }
          },
          "timestamp": "2026-09-04T10:00:02Z"
        }
      ]
    },
    "error": null
  }
  ```

---

### `POST /api/whatsapp/inbound/`
- **Description:** Webhook endpoint called by the Express WhatsApp Service when a message arrives. Resolves sender phone number to a User, validates session, and enqueues to `ai_queue`.
- **Auth Scope:** `Service Token` (`X-Service-Token: <SECRET>`)
- **Request Body:**
  ```json
  {
    "phone_number": "+923001234567",
    "text": "Transfer 5000 to Ahmed",
    "message_id": "wamid.HBgLMjA2...",
    "timestamp": 1725450720,
    "media": null
  }
  ```
- **Success Response (`200 OK`):**
  ```json
  {
    "success": true,
    "data": {
      "status": "enqueued",
      "job_id": "5f6e7d8c-9b0a-1122-3344-5566778899aa",
      "session_id": "b2c3d4e5-f6a7-8899-aabb-ccddeeff0011"
    },
    "error": null
  }
  ```

---

## 4.1. Rich Chat Widgets & Confirmation Modals Specification

### Overview: How Frontend Receives & Resolves Interactive Widgets
1. **Asynchronous Polling & Delivery:**
   - The customer enters a query or action request in the Web Chat.
   - Frontend calls `POST /api/chat/send/` and receives `{ "job_id": "<UUID>", "session_id": "<UUID>", "status": "PENDING" }`.
   - Frontend begins polling `GET /api/chat/jobs/{job_id}/` every 500ms–1000ms.
   - When processing completes, `GET /api/chat/jobs/{job_id}/` returns `status: "COMPLETED"` containing `response.text` and an optional `response.rich_widget`.
2. **Interactive Confirmation Modals:**
   - If the user's intent is transactional (e.g. Funds Transfer, Bill Payment, Card Freeze, Dispute Filing), the AI worker calls the backend staging endpoint (`/api/actions/stage-*`), generating a short-lived `staging_id` (5-min TTL).
   - The job's `rich_widget` is returned with `widget_type: "CONFIRMATION_MODAL"`, containing the full financial breakdown, expiry timestamp, and direct execution parameters.
   - The frontend renders an inline confirmation card/modal with explicit **[Confirm]** and **[Cancel]** buttons.
   - When the user clicks **[Confirm]**, the frontend directly submits `POST /api/actions/confirm-*` with `staging_id` and a client-generated `idempotency_key`.
   - Upon confirmation success, the widget transitions to a **Success Receipt**, eliminating any risk of double submission.
3. **Session Persistence:**
   - Every rich widget is saved inside `Message.metadata.rich_widget` in Postgres.
   - Polling `GET /api/chat/sessions/{id}/` returns historical widgets in their preserved state.

---

### Standard Widget Envelope
All widgets returned in `response.rich_widget` or stored in `Message.metadata.rich_widget` conform to this standard schema:

```json
{
  "widget_type": "STRING_IDENTIFIER",
  "payload": {}
}
```

---

### 1. `BALANCE_CARD`
Rendered when user queries account balance.
```json
{
  "widget_type": "BALANCE_CARD",
  "payload": {
    "account_id": "c7a8b9e1-2f34-4b56-8a90-1c2d3e4f5a6b",
    "account_title": "Muhammad Kaaif",
    "account_number_masked": "**** **** **** 0708",
    "account_type": "CURRENT",
    "available_balance": "84500.50",
    "currency": "PKR",
    "as_of": "2026-09-05T20:15:00Z"
  }
}
```

### 2. `TRANSACTION_LIST`
Rendered when user asks to see recent transactions or account history.
```json
{
  "widget_type": "TRANSACTION_LIST",
  "payload": {
    "account_number_masked": "****0708",
    "count": 2,
    "transactions": [
      {
        "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "date": "2026-09-04T14:32:00Z",
        "description": "Funds transfer to Venus Account ****4821",
        "category": "TRANSFER",
        "amount": "-5000.00",
        "currency": "PKR",
        "status": "COMPLETED"
      },
      {
        "id": "e21ba29a-11bb-4231-9988-112233445566",
        "date": "2026-09-03T11:15:00Z",
        "description": "Imtiaz Super Market POS 0921",
        "category": "SHOPPING",
        "amount": "-4500.00",
        "currency": "PKR",
        "status": "COMPLETED"
      }
    ]
  }
}
```

### 3. `CONFIRMATION_MODAL`
Rendered when user initiates a financial or irreversible action (Funds Transfer, Bill Payment, Card Lock).
```json
{
  "widget_type": "CONFIRMATION_MODAL",
  "payload": {
    "action_type": "FUNDS_TRANSFER",
    "staging_id": "3a4b5c6d-7e8f-9012-3456-789abcdef012",
    "title": "Confirm Funds Transfer",
    "expires_at": "2026-09-05T20:25:00Z",
    "requires_otp": false,
    "summary": {
      "from_account": "Current Account (****0708)",
      "recipient_name": "Ahmed Khan",
      "recipient_bank": "Venus Bank",
      "recipient_account": "**** **** **** 4821",
      "amount": "5000.00",
      "fee": "0.00",
      "total_deduction": "5000.00",
      "currency": "PKR"
    },
    "confirm_endpoint": "/api/actions/confirm-transfer/",
    "cancel_endpoint": "/api/actions/cancel-staged/",
    "confirm_payload": {
      "staging_id": "3a4b5c6d-7e8f-9012-3456-789abcdef012"
    }
  }
}
```

### 4. `OTP_VERIFICATION_MODAL`
Rendered when a transaction exceeds the Tier 2 HITL threshold (> Rs. 25,000) or requires two-factor challenge.
```json
{
  "widget_type": "OTP_VERIFICATION_MODAL",
  "payload": {
    "action_type": "HIGH_VALUE_TRANSFER",
    "staging_id": "3a4b5c6d-7e8f-9012-3456-789abcdef012",
    "title": "One-Time Password Verification",
    "message": "Enter the 6-digit verification code sent via SMS to your registered phone ending in ****776.",
    "masked_phone": "+92 300 ****776",
    "otp_length": 6,
    "expires_in_seconds": 300,
    "resend_endpoint": "/api/actions/resend-otp/",
    "verify_endpoint": "/api/actions/confirm-transfer/",
    "verify_payload": {
      "staging_id": "3a4b5c6d-7e8f-9012-3456-789abcdef012"
    }
  }
}
```

### 5. `BILL_SUMMARY_CARD`
Rendered when user asks to review an upcoming or unpaid utility bill.
```json
{
  "widget_type": "BILL_SUMMARY_CARD",
  "payload": {
    "bill_id": 101,
    "biller_name": "K-Electric",
    "category": "ELECTRICITY",
    "consumer_number": "0400012345678",
    "amount": "8450.00",
    "due_date": "2026-09-15",
    "is_paid": false,
    "actionable": true,
    "pay_action": {
      "endpoint": "/api/actions/pay-bill/",
      "payload": {
        "bill_id": 101
      }
    }
  }
}
```

### 6. `CARD_STATUS_CARD`
Rendered when user manages debit/credit cards or asks to freeze/unfreeze a card.
```json
{
  "widget_type": "CARD_STATUS_CARD",
  "payload": {
    "card_id": "b1a2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
    "card_number_masked": "4111 **** **** 5510",
    "cardholder_name": "Muhammad Kaaif",
    "card_type": "DEBIT",
    "status": "ACTIVE",
    "daily_spend_limit": "50000.00",
    "international_enabled": false,
    "available_actions": [
      { "action": "FREEZE", "label": "Freeze Card", "target_status": "FROZEN" },
      { "action": "BLOCK", "label": "Report Lost / Stolen", "target_status": "BLOCKED_LOST" }
    ]
  }
}
```

### 7. `DISPUTE_RECEIPT_CARD`
Rendered when an unrecognized transaction is escalated into an official dispute.
```json
{
  "widget_type": "DISPUTE_RECEIPT_CARD",
  "payload": {
    "ticket_number": "CMP-2026-0812",
    "status": "PENDING_REVIEW",
    "disputed_amount": "4500.00",
    "currency": "PKR",
    "reason": "Customer reported fraudulent POS debit at unknown merchant",
    "card_status_updated": "FROZEN",
    "sla": "7 to 15 business days",
    "created_at": "2026-09-05T20:20:00Z"
  }
}
```

### 8. `HITL_PENDING_BANNER`
Rendered when a transaction exceeds the Tier 3 HITL threshold (> Rs. 50,000) or triggers compliance review.
```json
{
  "widget_type": "HITL_PENDING_BANNER",
  "payload": {
    "pending_action_id": "7b8c9d0e-1f2a-3b4c-5d6e-7f8a9b0c1d2e",
    "action_type": "HIGH_VALUE_TRANSFER",
    "status": "AWAITING_STAFF_APPROVAL",
    "title": "Compliance Authorization Required",
    "message": "This transfer of Rs. 150,000.00 requires secondary authorization by Venus Bank compliance staff. You will receive an SMS confirmation once approved.",
    "estimated_review_time": "10–15 minutes"
  }
}
```

---

## 5. Transactional Action Contracts (`/api/actions/*`)

### `POST /api/actions/stage-transfer/`
- **Description:** Staging endpoint (called by AI Worker tool or Web UI). Validates recipient, balance, and limits; creates a `PendingAction` with a 5-minute TTL. Does NOT move money.
- **Auth Scope:** `Customer (Owner)` or `Internal Secret`
- **Request Body:**
  ```json
  {
    "beneficiary_id": 1,
    "amount": 5000.00,
    "from_account_id": "c7a8b9e1-2f34-4b56-8a90-1c2d3e4f5a6b"
  }
  ```
- **Success Response (`201 Created`):**
  ```json
  {
    "success": true,
    "data": {
      "pending_action_id": "3a4b5c6d-7e8f-9012-3456-789abcdef012",
      "status": "AWAITING_USER",
      "expires_at": "2026-09-04T14:37:00Z",
      "summary": {
        "recipient_name": "Ahmed Khan",
        "recipient_bank": "Venus Bank",
        "recipient_account_masked": "**** **** **** 4821",
        "amount": "5000.00",
        "fee": "0.00",
        "total_deduction": "5000.00",
        "currency": "PKR"
      }
    },
    "error": null
  }
  ```

---

### `POST /api/actions/confirm-transfer/`
- **Description:** Executes a previously staged transfer atomically upon customer confirmation.
- **Auth Scope:** `Customer (Owner)` or `Internal Secret`
- **Request Headers:** Optional `Idempotency-Key: <UUID>`
- **Request Body:**
  ```json
  {
    "pending_action_id": "3a4b5c6d-7e8f-9012-3456-789abcdef012"
  }
  ```
- **Success Response (`200 OK`):**
  ```json
  {
    "success": true,
    "data": {
      "reference_number": "TRX-2026-9812",
      "status": "COMPLETED",
      "amount": "5000.00",
      "recipient_name": "Ahmed Khan",
      "new_available_balance": "79500.50",
      "timestamp": "2026-09-04T14:33:05Z"
    },
    "error": null
  }
  ```
- **Error Response (`400 Bad Request` - Expired):**
  ```json
  {
    "success": false,
    "data": null,
    "error": {
      "code": "ACTION_EXPIRED",
      "message": "The staged transfer has expired. Please initiate the request again."
    }
  }
  ```

---

### `POST /api/actions/pay-bill/`
- **Description:** Executes payment of an outstanding utility bill. Deducts balance atomically and marks bill paid.
- **Auth Scope:** `Customer (Owner)` or `Internal Secret`
- **Request Body:**
  ```json
  {
    "bill_id": 101,
    "from_account_id": "c7a8b9e1-2f34-4b56-8a90-1c2d3e4f5a6b"
  }
  ```
- **Success Response (`200 OK`):**
  ```json
  {
    "success": true,
    "data": {
      "receipt_number": "BILL-2026-004812",
      "biller_name": "K-Electric",
      "consumer_number": "0400012345678",
      "amount_paid": "8450.00",
      "paid_at": "2026-09-04T14:40:00Z",
      "remaining_balance": "71050.50"
    },
    "error": null
  }
  ```

---

### `POST /api/actions/card-status/`
- **Description:** Toggles or permanently updates payment card status.
- **Auth Scope:** `Customer (Owner)` or `Internal Secret`
- **Request Body:**
  ```json
  {
    "card_id": "d1e2f3a4-b5c6-4789-8012-3456789abcde",
    "status": "FROZEN",
    "reason": "Customer misplaced card"
  }
  ```
- **Success Response (`200 OK`):**
  ```json
  {
    "success": true,
    "data": {
      "card_id": "d1e2f3a4-b5c6-4789-8012-3456789abcde",
      "card_number_masked": "**** **** **** 4821",
      "previous_status": "ACTIVE",
      "current_status": "FROZEN",
      "updated_at": "2026-09-04T15:00:00Z"
    },
    "error": null
  }
  ```

---

### `POST /api/actions/dispute/`
- **Description:** Lodges an official transaction dispute ticket. Can optionally auto-freeze the associated card. Enqueues ticket to Compliance HITL queue.
- **Auth Scope:** `Customer (Owner)` or `Internal Secret`
- **Request Body:**
  ```json
  {
    "transaction_id": "e21ba29a-11bb-4231-9988-112233445566",
    "reason": "UNAUTHORIZED_TRANSACTION",
    "customer_notes": "I did not make this purchase in Clifton Karachi.",
    "auto_freeze_card": true
  }
  ```
- **Success Response (`201 Created`):**
  ```json
  {
    "success": true,
    "data": {
      "ticket_number": "CMP-2026-0812",
      "status": "PENDING_REVIEW",
      "card_status": "FROZEN",
      "disputed_amount": "4500.00",
      "sla": "7 to 15 business days",
      "created_at": "2026-09-04T15:05:00Z"
    },
    "error": null
  }
  ```

---

## 6. Operations & Administration Contracts (`/api/admin/*`)

### `GET /api/admin/system/health/`
- **Description:** Full-system operational health summary across database, Redis queues, worker heartbeats, WhatsApp gateway, and external LLM provider status.
- **Auth Scope:** `Staff (SystemAdmin Group)`
- **Request Headers:** `Authorization: Bearer <jwt>`
- **Success Response (`200 OK`):**
  ```json
  {
    "success": true,
    "data": {
      "status": "HEALTHY",
      "timestamp": "2026-09-05T20:20:00Z",
      "uptime_seconds": 86400,
      "environment": "production",
      "degraded_components": [],
      "components": {
        "postgres": {
          "status": "UP",
          "latency_ms": 1.8,
          "active_connections": 14,
          "max_connections": 100,
          "database_size": "45.2 MB",
          "migrations_status": "UP_TO_DATE"
        },
        "redis": {
          "status": "UP",
          "latency_ms": 0.6,
          "used_memory_human": "2.4M",
          "connected_clients": 6,
          "total_keys": 312
        },
        "ai_worker_pool": {
          "status": "UP",
          "active_replicas": 3,
          "queue_depth": 1,
          "in_flight_jobs": 1,
          "last_heartbeat": "2026-09-05T20:19:58Z",
          "error_rate_5m_pct": 0.0
        },
        "background_worker": {
          "status": "UP",
          "active_workers": 2,
          "queue_depth": 0,
          "last_heartbeat": "2026-09-05T20:19:55Z",
          "failed_tasks_24h": 0
        },
        "whatsapp_service": {
          "status": "UP",
          "connection_state": "CONNECTED",
          "session_authenticated": true,
          "phone_number": "+923001234567",
          "uptime_seconds": 14200,
          "latency_ms": 42
        },
        "llm_gateway": {
          "status": "UP",
          "primary_provider": "google",
          "fallback_available": true,
          "latency_ms": 240
        }
      }
    },
    "error": null
  }
  ```

---

### `GET /api/admin/telemetry/`
- **Description:** Aggregated AI operational observability, token usage, cost estimates, tier distribution, agent roles, fallback events, guardrail triggers, and RAG retrieval metrics.
- **Auth Scope:** `Staff (SystemAdmin Group)`
- **Request Headers:** `Authorization: Bearer <jwt>`
- **Query Parameters:**
  - `period` (optional string): `1h` | `24h` | `7d` | `30d` (default: `24h`)
- **Success Response (`200 OK`):**
  ```json
  {
    "success": true,
    "data": {
      "period": "LAST_24_HOURS",
      "overview": {
        "total_calls": 342,
        "total_tokens": 128450,
        "prompt_tokens": 92100,
        "completion_tokens": 36350,
        "estimated_cost_usd": "0.192",
        "latency_p50_ms": 1150,
        "latency_p95_ms": 2480,
        "error_rate_pct": 0.58
      },
      "tier_distribution": {
        "fast-llm": {
          "total_calls": 290,
          "total_tokens": 85400,
          "cost_usd": "0.085",
          "avg_latency_ms": 980
        },
        "smart-llm": {
          "total_calls": 52,
          "total_tokens": 43050,
          "cost_usd": "0.107",
          "avg_latency_ms": 2350
        }
      },
      "model_distribution": [
        {
          "tier": "fast-llm",
          "provider": "google",
          "model_name": "gemini-1.5-flash",
          "calls": 275,
          "tokens": 81200,
          "cost_usd": "0.081",
          "is_fallback": false
        },
        {
          "tier": "fast-llm",
          "provider": "groq",
          "model_name": "llama-3.1-8b",
          "calls": 15,
          "tokens": 4200,
          "cost_usd": "0.004",
          "is_fallback": true
        },
        {
          "tier": "smart-llm",
          "provider": "google",
          "model_name": "gemini-1.5-pro",
          "calls": 52,
          "tokens": 43050,
          "cost_usd": "0.107",
          "is_fallback": false
        }
      ],
      "agent_role_distribution": {
        "retriever": { "calls": 142, "avg_latency_ms": 420 },
        "responder": { "calls": 342, "avg_latency_ms": 1100 },
        "action_executor": { "calls": 48, "avg_latency_ms": 650 }
      },
      "fallback_events": {
        "total_fallbacks_triggered": 15,
        "primary_rate_limit_hits": 12,
        "primary_timeout_hits": 3,
        "fallback_recovery_success_pct": 100.0
      },
      "guard_triggers": {
        "prompt_injection_blocked": 4,
        "system_prompt_leakage_blocked": 1,
        "output_guard_rejected": 2,
        "pii_redacted": 12,
        "structured_output_failures": 3,
        "repeated_injection_flagged_sources": [
          {
            "identifier": "+923009988776",
            "channel": "WHATSAPP",
            "flags_count": 3,
            "last_flagged_at": "2026-09-05T19:40:00Z"
          }
        ]
      },
      "rag_metrics": {
        "total_retrievals": 142,
        "avg_retrieval_latency_ms": 45,
        "avg_sources_per_query": 2.4,
        "pgvector_query_count": 142
      },
      "tool_call_counts": {
        "get_balance": 180,
        "list_transactions": 95,
        "stage_transfer": 32,
        "pay_bill": 14,
        "block_card": 8,
        "lodge_dispute": 4
      }
    },
    "error": null
  }
  ```

---

### `GET /api/admin/hitl/pending/`
- **Description:** Lists all Level 2 pending actions (transfers > Rs. 50,000, disputes) requiring compliance authorization.
- **Auth Scope:** `Staff (ComplianceManager Group)`
- **Success Response (`200 OK`):**
  ```json
  {
    "success": true,
    "data": [
      {
        "pending_action_id": "7b8c9d0e-1f2a-3b4c-5d6e-7f8a9b0c1d2e",
        "action_type": "HIGH_VALUE_TRANSFER",
        "user_name": "Hamza Tariq",
        "user_phone": "+923009988776",
        "amount": "150000.00",
        "recipient_name": "Tariq Mahmood",
        "status": "AWAITING_ADMIN",
        "created_at": "2026-09-04T15:12:00Z"
      }
    ],
    "error": null
  }
  ```

---

### `POST /api/admin/hitl/{id}/approve/`
- **Description:** Compliance Manager approves a flagged pending action, triggering execution.
- **Auth Scope:** `Staff (ComplianceManager Group)`
- **Success Response (`200 OK`):**
  ```json
  {
    "success": true,
    "data": {
      "pending_action_id": "7b8c9d0e-1f2a-3b4c-5d6e-7f8a9b0c1d2e",
      "status": "APPROVED",
      "reviewed_by": "compliance_officer_1",
      "reviewed_at": "2026-09-04T15:15:00Z"
    },
    "error": null
  }
  ```

---

### `POST /api/admin/chat/{id}/takeover/`
- **Description:** Support Agent pauses AI responses and takes over the live customer session.
- **Auth Scope:** `Staff (SupportAgent Group)`
- **Success Response (`200 OK`):**
  ```json
  {
    "success": true,
    "data": {
      "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "status": "ESCALATED_HUMAN",
      "agent_name": "Areeb Support Rep",
      "taken_over_at": "2026-09-04T15:20:00Z"
    },
    "error": null
  }
  ```

---

## 7. Internal Worker Contracts (`/api/internal/*`)

### `GET /api/internal/ai-config/`
- **Description:** Called by AI Worker Pool on startup and periodic refresh to fetch active system prompts, model tiers, and fallback chains.
- **Auth Scope:** `Internal Secret` (`X-Internal-Secret: <SECRET>`)
- **Success Response (`200 OK`):**
  ```json
  {
    "success": true,
    "data": {
      "active_prompt_version": "v1.2",
      "system_prompt": "You are Venus Bank's official AI Support Assistant...",
      "model_tiers": {
        "fast": { "provider": "google", "model": "gemini-1.5-flash", "temperature": 0.2 },
        "smart": { "provider": "openai", "model": "gpt-4o", "temperature": 0.1 }
      },
      "fallback_chains": {
        "fast": ["gemini-1.5-flash", "gpt-4o-mini", "claude-3-haiku"]
      }
    },
    "error": null
  }
  ```

---

## 8. Outbound WhatsApp HTTP Client Contract (`shared/whatsapp_client.py`)

### `POST /whatsapp/send` (Called on Express WhatsApp Service)
- **Description:** AI Worker or Background Worker sends an outbound message or media attachment to a WhatsApp recipient.
- **Request Headers:** `Content-Type: application/json`
- **Request Body (Text Message):**
  ```json
  {
    "to": "+923001234567",
    "message": "*Venus Bank Support*\nYour available balance is *Rs. 84,500.50*."
  }
  ```
- **Request Body (Media / PDF Statement):**
  ```json
  {
    "to": "+923001234567",
    "message": "Here is your requested 6-month account statement.",
    "media_url": "http://main-service:8000/media/statements/stmt_20260904.pdf",
    "filename": "Venus_Account_Statement.pdf"
  }
  ```
- **Success Response (`200 OK`):**
  ```json
  {
    "success": true,
    "message_id": "wamid.HBgLMjA2...",
    "status": "sent"
  }
  ```

---

## 9. Redis Queue Payload Schemas

### 9.1 `ai_queue` Message Schema (Enqueued by Main Service)
```json
{
  "job_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "user_id": 12,
  "channel": "WEB",
  "message": "Transfer Rs. 5000 to Ahmed",
  "is_verified": true,
  "enqueued_at": "2026-09-04T14:32:00.123456Z"
}
```

### 9.2 `tasks_queue` Message Schema (Background Worker)
```json
{
  "job_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "type": "generate_pdf",
  "user_id": 12,
  "account_id": "c7a8b9e1-2f34-4b56-8a90-1c2d3e4f5a6b",
  "payload": {
    "start_date": "2026-03-01",
    "end_date": "2026-09-01",
    "delivery_channel": "WHATSAPP",
    "phone_number": "+923001234567"
  },
  "enqueued_at": "2026-09-04T15:00:00Z"
}
```

---

## 10. Traceability & Lock Status

This contract document formally completes the **Inter-Service Contract Locking** deliverable of **SDLC Phase 2**.
- **Lock Date:** September 5, 2026
- **Next Phase:** **SDLC Phase 3 (Component Design)**
- **Team Impact & Execution Boundaries:**
  - **Areeb (Frontend):** May immediately mock these API responses and rich interactive widgets (`docs/contracts.md` §4.1) to build all chat, banking, and admin UI pages.
  - **Hamza & Kaaif (Main Service & Background Worker):** Implement Django models, DRF serializers, atomic viewsets, and Redis queue workers strictly conforming to these locked schemas.
  - **Javed & Kaaif (AI Worker):** In Phase 3, independently design the internal LangGraph graph nodes, LiteLLM router fallback tiers, and agent tools to consume `/api/internal/ai-config/` and execute actions exclusively by calling the locked backend REST endpoints (`/api/actions/*`, `/api/banking/*`, `/api/internal/*`) over HTTP with the internal service secret.

