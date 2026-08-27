# pay-pipeline: System Architecture & Reference Specification

This document provides a highly detailed, component-level technical specification of the **pay-pipeline** commerce and policy engine. It outlines the core security principles, database schemas, cryptographic audit protocols, routing mechanisms, and transactional lifecycles.

---

## 1. Core Architectural Philosophy

The application enforces a strict security envelope around financial transactions, structured as a **diode network** where data flows freely for discovery, but execution is blocked behind model-independent checks.

```
       +---------------------------------------------+
       |           Conversational Interface          |
       +---------------------------------------------+
                              |
                              v
       +---------------------------------------------+
       |   Multi-Agent Orchestrator (LlamaIndex)    |  <-- LLM/Agent (Untrusted Layer)
       +---------------------------------------------+
                              |
                              v
                     [Checkout Request]
                              |
                              v
       ===============================================
       |         GUARDRAIL & POLICY ENGINE           |  <-- Rigid Rules (Trusted Layer)
       ===============================================
         |              |              |           |
    Spend Limits    Idempotency    Categories   Approval
         |              |              |           |
         +--------------+-------+------+-----------+
                                |
                                v (If Approved)
       +---------------------------------------------+
       |    Isolated Executable Tools & Razorpay     |  <-- REST APIs & Signatures
       +---------------------------------------------+
```

### A. Separation of Intelligence (Untrusted) and Execution (Trusted)
* **Untrusted Layer (AI Orchestrator)**: Includes LLM completions, entity extraction, semantic lookups, and upsell generation. These are treated as *untrusted* inputs that can hallucinate or fail.
* **Trusted Layer (Policy Engine)**: Comprises Python-defined, rule-based modules that run independent of the LLM. 
* **The Diode Boundary**: Agents can read inventory and build virtual carts. However, to create an order or issue a refund, they must generate a typed event and pass it to the trusted policy gate.

### B. Reactive State Verification via Signed Webhooks
* When a payment link is created, the local order is recorded in the `ORDER_CREATED` state (never marked `PAID`).
* Razorpay handles user authorization securely.
* Upon success, Razorpay fires a webhook back to the application. The system decodes the webhook payload, validates its SHA-256 signature against the configured `razorpay_webhook_secret`, and executes the state transition to `PAYMENT_CAPTURED`.

### C. Cryptographic Tamper Detection
* The audit trail uses sequential hash chaining.
* Any deletion or modification of records in SQLite breaks the chain signature because the hash of block $N$ incorporates the hash of block $N-1$.
* The HMAC secret signs the final hash using the `AUDIT_HMAC_SECRET`, ensuring database-level edits cannot reconstruct signatures.

---

## 2. Exhaustive Database Schema Specification

The tables are mapped using SQLAlchemy in [`backend/app/database/models.py`](file:///c:/razorpay/pay-pipeline/backend/app/database/models.py). The following is the exact SQLite table layout:

### 2.1 `products` (Inventory Catalog)
Stores catalog items available for agent lookups and cart creation.
* **`id`** (`VARCHAR(64)`, Primary Key, Indexed): Unique SKU code (e.g. `sku_kb_keychron_k2`).
* **`name`** (`VARCHAR(255)`, Non-Nullable): Human-readable name.
* **`category`** (`VARCHAR(100)`, Non-Nullable, Indexed): Category tag (used for whitelisting rules).
* **`price`** (`FLOAT`, Non-Nullable): Unit cost in INR.
* **`inventory`** (`INTEGER`, Default `0`): Physical count of available stock.
* **`rating`** (`FLOAT`, Default `4.5`): Product rating score.
* **`specs_json`** (`TEXT`, Default `"{}"`): Key-value specs mapping.
* **`tags_json`** (`TEXT`, Default `"[]"`): Array of search index keywords.
* **`complementary_ids_json`** (`TEXT`, Default `"[]"`): SKU arrays linked for upsell logic.
* **`description`** (`TEXT`, Default `""`): Markdown description of the product.
* **`created_at`** (`DATETIME`): UTC creation timestamp.

### 2.2 `carts` (Temporary Session Basket)
Represents a customer's active basket before checking out.
* **`cart_id`** (`VARCHAR(64)`, Primary Key, Indexed): Random UUID representing the session.
* **`user_id`** (`VARCHAR(64)`, Non-Nullable, Indexed): Unique ID of the buyer.
* **`currency`** (`VARCHAR(10)`, Default `"INR"`): ISO currency.
* **`subtotal_amount`** (`FLOAT`, Default `0.0`): Sum of items before discount.
* **`discount_amount`** (`FLOAT`, Default `0.0`): Applied discount total.
* **`total_amount`** (`FLOAT`, Default `0.0`): Final subtotal (net amount to charge).
* **`status`** (`VARCHAR(32)`, Default `"ACTIVE"`): Cart states: `ACTIVE`, `CHECKED_OUT`, `ABANDONED`.
* **`applied_bundle_json`** (`TEXT`, Nullable): Description of bundle promo applied (if any).
* **`created_at`** / **`updated_at`** (`DATETIME`): Session tracking times.

### 2.3 `cart_items` (Basket Line Items)
* **`id`** (`INTEGER`, Primary Key, Autoincremented): Line item index.
* **`cart_id`** (`VARCHAR(64)`, Foreign Key `carts.cart_id`, Cascaded on Delete): Parent cart.
* **`product_id`** (`VARCHAR(64)`, Non-Nullable): Product ID SKU.
* **`name`** (`VARCHAR(255)`): Cached product name.
* **`price`** (`FLOAT`): Product price at time of cart insertion.
* **`quantity`** (`INTEGER`, Default `1`): Number of items ordered.
* **`subtotal`** (`FLOAT`): Price $\times$ quantity.
* **`category`** (`VARCHAR(100)`): Product category.

### 2.4 `orders` (Transaction Record)
Maintains authoritative purchase states.
* **`order_id`** (`VARCHAR(64)`, Primary Key, Indexed): Razorpay order ID (or generated simulator UUID).
* **`cart_id`** (`VARCHAR(64)`, Non-Nullable, Indexed): Cart ID linked to this order.
* **`user_id`** (`VARCHAR(64)`, Indexed): User ID of the purchaser.
* **`amount`** (`FLOAT`): Bill amount in INR.
* **`amount_in_paise`** (`INTEGER`): Final bill amount in paise (INR $\times$ 100) submitted to payment rails.
* **`currency`** (`VARCHAR(10)`, Default `"INR"`): ISO currency.
* **`status`** (`VARCHAR(32)`, Default `"created"`): Razorpay order states (`created`, `attempted`, `paid`).
* **`receipt`** (`VARCHAR(64)`): Unique receipt string.
* **`state`** (`VARCHAR(64)`, Default `"ORDER_CREATED"`): Local state machine state.
* **`notes_json`** (`TEXT`, Default `"{}"`): Context data sent to Razorpay.
* **`idempotency_key`** (`VARCHAR(128)`, Nullable, Indexed): Request verification key.
* **`created_at`** / **`updated_at`** (`DATETIME`): Timestamps.

### 2.5 `payments` (Capture Receipt Log)
Logs individual capture results sent via webhooks or simulator callbacks.
* **`payment_id`** (`VARCHAR(64)`, Primary Key, Indexed): Razorpay payment ID (`pay_...`).
* **`order_id`** (`VARCHAR(64)`, Foreign Key `orders.order_id`): Linked order.
* **`user_id`** (`VARCHAR(64)`): Purchaser identification.
* **`amount`** (`FLOAT`): Captured amount.
* **`currency`** (`VARCHAR(10)`): ISO currency.
* **`method`** (`VARCHAR(32)`, Default `"upi"`): Payment tool used (`upi`, `card`, `netbanking`).
* **`status`** (`VARCHAR(32)`, Default `"pending"`): `captured`, `failed`, `pending`.
* **`error_code`** / **`error_description`** (`TEXT`): Error telemetry if capture fails.
* **`verified_at`** (`DATETIME`, Nullable): When webhook signature was successfully verified.

### 2.6 `refunds` (Refund Tracing Ledger)
Enforces limits on refunds relative to original payment bounds.
* **`refund_id`** (`VARCHAR(64)`, Primary Key, Indexed): Unique refund transaction ID (`rfnd_...`).
* **`payment_id`** (`VARCHAR(64)`, Foreign Key `payments.payment_id`): Original payment transaction.
* **`order_id`** (`VARCHAR(64)`, Nullable): Original order.
* **`user_id`** (`VARCHAR(64)`): Issuer ID.
* **`amount`** (`FLOAT`): Refunded value in INR.
* **`currency`** (`VARCHAR(10)`): Currency.
* **`reason`** (`TEXT`): Explanation for log files.
* **`status`** (`VARCHAR(32)`, Default `"processed"`): `processed`, `failed`.

### 2.7 `approvals` (Gated Human-in-the-Loop Orders)
Stores order confirmation tokens awaiting human validation.
* **`token`** (`VARCHAR(128)`, Primary Key, Indexed): Crypto-secure verification string.
* **`user_id`** (`VARCHAR(64)`, Indexed): Requesting buyer.
* **`amount`** (`FLOAT`): Transaction amount.
* **`cart_id`** (`VARCHAR(64)`): Target cart.
* **`reason`** (`TEXT`): Policy threshold trigger description.
* **`status`** (`VARCHAR(32)`, Default `"PENDING"`): `PENDING`, `APPROVED`, `REJECTED`, `EXPIRED`.
* **`created_at`** / **`approved_at`** (`DATETIME`): Timestamps.

### 2.8 `audit_records` (Hash-Chained System Ledger)
* **`index`** (`INTEGER`, Primary Key): Monotonically increasing index number.
* **`event_id`** (`VARCHAR(64)`, Unique, Indexed): Event UUID.
* **`timestamp`** (`VARCHAR(64)`, Non-Nullable): ISO string.
* **`prev_hash`** (`VARCHAR(128)`, Non-Nullable): Hash value of `index - 1`.
* **`record_hash`** (`VARCHAR(128)`, Non-Nullable, Indexed): Hash value of current record.
* **`actor_id`** / **`actor_role`** (`VARCHAR(64)`): Who initiated the action.
* **`action`** / **`intent`** / **`tool_name`** (`VARCHAR(64)`): Action metadata.
* **`arguments_json`** (`TEXT`): JSON dump of parameters passed to the tool.
* **`guardrail_decision`** (`VARCHAR(64)`): `APPROVED`, `DENIED`, or `PENDING_APPROVAL`.
* **`approval_required`** (`BOOLEAN`): Human-in-the-loop flag.
* **`transaction_state`** (`VARCHAR(64)`): Order status state.
* **`result_status`** (`VARCHAR(32)`): `SUCCESS`, `FAILED`, `PENDING`.
* **`signature`** (`VARCHAR(256)`, Non-Nullable): HMAC SHA-256 signature of `record_hash`.
* **`latency_ms`** (`FLOAT`): System latency execution tracking.
* **`explainability_notes`** (`TEXT`): Human-readable reasoning notes for audit.

---

## 3. Cryptographic Chain Security Protocol

The system logs every security-sensitive event to a cryptographic hash chain using SHA-256 and HMAC verification.

```
+-----------------------------------+
|      Audit Record (Index N-1)     |
|  - Data: ...                      |
|  - Record Hash: Hash(N-1)         |
+-----------------------------------+
                  |
                  v (Linked as input)
+---------------------------------------------------------+
|                Audit Record (Index N)                   |
|  - Prev Hash: Hash(N-1)                                 |
|  - Payload: { Index, Action, Args, Result... }          |
|  - Canonical Representation: json.dumps(Payload)        |
|  - Record Hash: SHA-256(Canonical Repr + Prev Hash)     |
|  - Signature: HMAC-SHA256(Record Hash, HMAC_SECRET)     |
+---------------------------------------------------------+
```

### A. Hash Computation (`backend/app/audit/hash_chain.py`)
Each record is serialized into a canonical representation (sorted keys, stringified fields, no padding spaces). The SHA-256 hash is calculated as:

$$\text{Canonical Repr} = \text{JSON}_{\text{canonical}}(\{\text{prev\_hash}, \text{index}, \text{timestamp}, \text{actor\_id}, \text{actor\_role}, \text{action}, \text{intent}, \text{arguments}, \text{decision}, \text{state}, \text{status}\})$$

$$\text{Record Hash} = \text{SHA-256}(\text{Canonical Repr})$$

### B. HMAC Signature generation (`backend/app/audit/signer.py`)
To prevent attackers from rewriting the database values and recomputing the SHA-256 chain, the `Record Hash` is signed using HMAC-SHA-256:

$$\text{Signature} = \text{HMAC-SHA256}(\text{Key} = \text{AUDIT\_HMAC\_SECRET}, \text{Msg} = \text{Record Hash})$$

### C. Validation Loop
When validating the audit trail, the service executes:
1. Fetch record $0$ (verify signature against standard genesis values).
2. For record $N$ where $N > 0$:
   * Verify that `prev_hash` matches `record_hash` of record $N-1$.
   * Recompute `record_hash` from the database columns and assert equality.
   * Verify the `signature` using the local `AUDIT_HMAC_SECRET` and `hmac.compare_digest` to prevent timing attacks.

---

## 4. Multi-Agent Orchestrator Execution Flow

The conversational routing maps incoming natural language calls inside [`backend/app/workflows/commerce_workflow.py`](file:///c:/razorpay/pay-pipeline/backend/app/workflows/commerce_workflow.py).

### Detailed Request Tracing (Example: "Buy me a mobile charger")

```
[User Request] "Buy me a mobile charger"
      |
      v
1. API Router (backend/app/api/chat.py)
   - Receives ChatRequest payload.
   - Invokes commerce_workflow.run(user_message=...)
      |
      v
2. Step: intent_router (commerce_workflow.py)
   - Evaluates text using rules or LLM.
   - If purchase intent is detected:
     - Extracts SKU or queries catalog using semantic filters.
     - Emits a CatalogDiscoveryEvent.
      |
      v
3. Step: catalog_agent (commerce_workflow.py)
   - Searches catalog DB.
   - Resolves product: "sku_charger_fast" (Price: 1499.00).
   - Evaluates Campaign database for relevant deals/upsells.
   - Emits a CheckoutCartEvent with Cart details.
      |
      v
4. Step: policy_agent (commerce_workflow.py)
   - Intercepts CartEvent before execution.
   - Calls money_tools.create_order_guarded(cart, user_id).
      |
      +---> trusted_policy_engine (policy_engine.py)
            - Run check: Idempotency Key (Approved)
            - Run check: Category Allowed (Approved)
            - Run check: Spend Limiter <= 5,000 (Approved)
            - Run check: Daily Cumulative <= 15,000 (Approved)
            - Run check: Human Approval Threshold > 3,000 (False; Approved)
            - Returns PolicyEvaluationResult(allowed=True)
      |
      v
5. execute_order (money_tools.py)
   - Invokes razorpay_client.create_order()
     - POST https://api.razorpay.com/v1/orders
     - Receives Razorpay Order ID: order_TUsP...
   - Invokes razorpay_client.create_payment_link(order)
     - POST https://api.razorpay.com/v1/payment_links
     - Receives short checkout URL: https://rzp.io/...
   - Records Order to database (ORDER_CREATED state).
   - Appends audit trail event via audit_service.py (hash chained).
      |
      v
6. return_to_client (StopEvent)
   - Returns order details and payment link JSON.
```

---

## 5. Webhook State Transition Logic

The Webhook Receiver [`backend/app/payment/webhook_handler.py`](file:///c:/razorpay/pay-pipeline/backend/app/payment/webhook_handler.py) processes events fired by Razorpay.

```
       [Webhook Request from Razorpay]
                      |
                      v
          [Validate Signature]
                      |
          +-----------+-----------+
          |                       |
      [Valid]                  [Invalid]
          |                       |
          v                       v
[Check Event Type]        [Log HTTP 400 & Drop]
          |
    +-----+-----------------------------------------+
    |                                               |
[order.paid / payment.captured]            [refund.processed]
    |                                               |
    v                                               v
State: Await Webhook                       State: PAID
    |                                               |
    v                                               v
Assert Order amount matches                     Load refund metadata
    |                                               |
    v                                               v
Update order state to PAID                 Update order state to REFUNDED
    |                                               |
    v                                               v
Log to Audit Chain (HMAC Signed)           Log to Audit Chain (HMAC Signed)
```

### Signature Verification Code Block:
```python
def verify_webhook_signature(self, raw_payload: str, signature: str) -> bool:
    if not self.webhook_secret:
        return False
    expected_signature = hmac.new(
        self.webhook_secret.encode("utf-8"),
        raw_payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)
```
If verification passes, the order state transitions dynamically via `backend.app.payment.state_machine.state_machine.transition(...)`.
