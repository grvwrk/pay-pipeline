# pay-pipeline

an agent system built on razorpay test-mode apis, built to do two things: grow a merchant's revenue, and make that merchant transactable by an ai buyer end to end.

structured as a diode network — data flows freely for discovery, execution is blocked behind rules that don't depend on a model.

---

## architecture

```
       +---------------------------------------------+
       |           Conversational Interface          |
       +---------------------------------------------+
                              |
                              v
       +---------------------------------------------+
       |    Multi-Agent Orchestrator (LlamaIndex)     |  <-- untrusted layer
       +---------------------------------------------+
                              |
                              v
                     [Checkout Request]
                              |
                              v
       ===============================================
       |         GUARDRAIL & POLICY ENGINE           |  <-- trusted layer
       ===============================================
         |              |              |           |
    Spend Limits    Idempotency    Categories   Approval
         |              |              |           |
         +--------------+-------+------+-----------+
                                |
                                v (if approved)
       +---------------------------------------------+
       |    Isolated Executable Tools & Razorpay      |
       +---------------------------------------------+
```

---

## implementation

### separation of intelligence and execution
the orchestrator — llm completions, entity extraction, semantic lookups, upsell generation — is treated as untrusted. it can hallucinate, misread intent, fail. it can read inventory and build a virtual cart on its own. it cannot create an order or issue a refund directly.

to move money, it has to emit a typed event and hand it to the policy engine. the policy engine is plain rule-based code, runs independent of any model, and is what actually decides whether the action goes through. limits inside it are configurable, not hardcoded.

### state verification
an order is never marked paid on creation. it's recorded as `ORDER_CREATED` and stays there. razorpay handles the actual authorization. when it succeeds, razorpay fires a webhook back — the payload is decoded, its signature checked against the configured webhook secret, and only then does the order transition to `PAYMENT_CAPTURED`. nothing on this system's side gets to decide a payment happened.

an invalid signature gets logged and dropped, not processed. a valid one is routed by event type — a capture event asserts the amount matches before updating state; a refund event loads the refund metadata before updating state. either path writes to the audit chain afterward.

### audit chain
every security-relevant event is hash chained. each record's hash is computed from its own canonical payload plus the previous record's hash, so record `N` can't be altered without breaking every record after it. the resulting hash is then signed with a separate hmac secret, so even a direct database edit that recomputes the chain correctly still can't reproduce a valid signature. validating the trail means walking the chain from the genesis record forward, recomputing each hash, and checking each signature against the secret.

### data layer
- **products** — catalog for lookups and cart building.
- **carts / cart_items** — session basket state, active until checkout or abandonment.
- **orders** — the authoritative record of a transaction, tracked through its local state machine alongside razorpay's own order status.
- **payments** — capture results, keyed to an order, populated once a webhook is verified.
- **refunds** — traced back to the original payment, bounded by it.
- **approvals** — tokens for transactions gated behind human confirmation, with their own pending/approved/rejected/expired lifecycle.
- **audit_records** — the hash chain itself: index, prev hash, record hash, actor, action, and the decision that was made.

---

## configuration

configure parameters in [config.yaml](file:///c:/razorpay/pay-pipeline/config.yaml) or override using environment variables.

### local variables
- **`PAYMENT_PROVIDER_MODE`**: `simulator` (offline testing) or `razorpay` (live test rails).
- **`RAZORPAY_KEY_ID`**: razorpay key id (required if mode is `razorpay`).
- **`RAZORPAY_KEY_SECRET`**: razorpay secret key (required if mode is `razorpay`).
- **`RAZORPAY_WEBHOOK_SECRET`**: signature secret for webhook verification (default: `pay_pipeline_webhook_secret_default_2026`).

---

## setup

### 1. environment preparation
create virtual environment and install packages:
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. database initialization
the sqlite database (`pay_pipeline.db`) and schema are created and seeded with default product catalog items automatically on application startup.

### 3. start uvicorn
run the backend server:
```powershell
python -m backend.app.main
```
the api will bind to `http://localhost:8000`. interactive swagger documentation is served at `http://localhost:8000/docs`.

---

## api verification

verify end-to-end functionality using guided scenarios or raw terminal api calls.

### guided demo scenarios
pre-built workflows that simulate specific integration pipelines. run via `POST /api/v1/scenarios/run/{scenario_id}`.

- **`discovery_and_reasoning`**: search catalog under ₹5,000. catalog agent reasons over specs and filters matches.
- **`upsell_basket_growth`**: adds keychron keyboard to cart, auto-bundles with walnut wrist rest, and applies a bundle discount.
- **`graceful_failure_spend_limit`**: attempts to purchase a ₹7,999 keyboard. the guardrail engine blocks checkout against the ₹5,000 ceiling.
- **`gated_approval_flow`**: attempts to purchase a ₹4,499 keyboard. since it exceeds the ₹3,000 gate, the order transitions to `PENDING_APPROVAL` and generates an approval token.
- **`duplicate_request_idempotency`**: attempts identical checkout requests sequentially with the same idempotency key to verify double-spend protection.
- **`valid_refund_flow`**: captures a test payment and processes a partial refund.

### conversational chat
for conversational purchases. parses query, runs policy checks, and returns order metadata.

**endpoint**: `POST /api/v1/chat`

**command (powershell)**:
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/chat" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"user_message": "Buy me a mobile charger", "user_id": "buyer_01"}'
```

**response**:
```json
{
  "type": "ORDER_CREATED",
  "message": "Order order_TUsUCQha8WL97Q created for ₹1499.00. Awaiting payment initiation.",
  "order": {
    "order_id": "order_TUsUCQha8WL97Q",
    "amount": 1499.0,
    "status": "created"
  },
  "payment_link": "https://rzp.io/rzp/wA603Ka9"
}
```

### agentic commerce protocol (acp)
endpoints for autonomous machine-to-machine commerce.

* **discovery**: `GET /api/v1/acp/discover?query=keyboard`
  returns search matching query.
* **quote**: `POST /api/v1/acp/quote`
  evaluates cart discounts and bundle recommendations.
* **checkout**: `POST /api/v1/acp/checkout`
  submits cart to policy engine and generates razorpay links.

**command (powershell)**:
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/acp/checkout" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"cart_id": "cart_ce66d0c26057", "user_id": "agent_buyer_01"}'
```

---

## webhook execution

### webhook setup
to test verified status updates locally, expose port 8000 using ngrok:
```bash
ngrok http 8000
```

register the forwarding url in the razorpay dashboard settings under webhooks:
- **url**: `https://<ngrok-subdomain>.ngrok-free.app/api/v1/webhooks/razorpay`
- **secret**: `pay_pipeline_webhook_secret_default_2026`
- **active events**: `payment.captured`, `order.paid`

when a user pays via the generated `payment_link`, razorpay hits the webhook receiver, transitioning the SQLite order status to `paid` and recording payment capture telemetry in `pay_pipeline.db`.

---
