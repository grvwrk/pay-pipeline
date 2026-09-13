# pay-pipeline frontend

a separate single-page app for the pay-pipeline backend. react + vite + typescript + tailwind v4. it talks to the fastapi service over `/api/v1` and holds no business logic of its own — carts are priced server-side, and every money-moving decision is rendered from what the policy engine returned.

---

## setup

the backend must be running first (see the root [README](../README.md)):

```powershell
python -m backend.app.main   # binds http://localhost:8000
```

then, in a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

the app serves on `http://localhost:5173`. vite proxies `/api` and `/health` to `localhost:8000`, so the browser sees one origin and cors is never in play during development.

### scripts

- `npm run dev` — dev server with hot reload and the backend proxy
- `npm run build` — typecheck then emit a static bundle to `dist/`
- `npm run preview` — serve the built bundle
- `npm run typecheck` — types only

### pointing at a different backend

for a static build served separately from the api, set an absolute origin:

```
VITE_API_BASE=https://api.example.com
```

leave it empty to use the dev proxy. see [.env.example](.env.example).

---

## screens

**agent console** (`/chat`) — conversational purchasing against `POST /api/v1/chat`. each agent reply carries its response type, and the right-hand inspector shows the full reasoning trace (which agent acted, what tool it called, how long it took) next to the deterministic policy evaluation. when the policy engine gates a transaction, the approval token is surfaced with a button that registers human approval and re-issues the purchase. a "force payment failure" toggle passes `force_fail_payment` through for testing the failure path.

when the order response carries a `payment_link`, the razorpay hosted-checkout url is rendered inline in the reply — a **pay now** button that opens it in a new tab, a copy-link button, and the raw url. the same block appears in the inspector's order panel, which explains instead when no link was issued (razorpay only returns one when `provider_mode` is `razorpay` and both api credentials are set).

**catalog** (`/catalog`) — filtered product discovery. adding an item calls `POST /api/v1/cart`, so bundle detection and discount pricing happen on the server.

**cart & checkout** (`/cart`) — line items, bundle discount, and the checkout run. the idempotency key is editable: submit twice with the same key to watch double-spend protection reject the replay. a created order sits in `ORDER_CREATED`; its razorpay payment link is the primary action, with test-payment and simulate-failure buttons below it. the ui states plainly that capture is not final until a signed webhook arrives.

**orders & refunds** (`/orders`) — order table with transaction state, a detail pane including the idempotency key and gateway notes, and a refund form bounded by the captured amount.

**sync with razorpay** — a paid order only turns green once the gateway confirms capture, which normally arrives as a webhook. razorpay cannot reach `localhost`, so the header carries a **sync with razorpay** button (`POST /payments/reconcile-pending`) and each unsettled order a **check payment status** button (`POST /payments/reconcile/{order_id}`). both pull the authoritative status and apply it, turning the row `COMPLETED` on capture or `PAYMENT_FAILED` on a failed or cancelled link. the cart page does the same automatically: opening the payment link starts polling until the gateway has a verdict.

**guardrails** (`/guardrails`) — reads and writes `GET/POST /api/v1/guardrails/config`. spend ceiling, approval threshold, cumulative cap, quantity limit, currency, allowed categories and merchant whitelist. changes are staged locally and marked `unsaved` until submitted.

**audit chain** (`/audit`) — the hash-chained ledger. each record shows its previous hash, its own hash and the hmac signature that covers it; "verify integrity" walks the chain via `GET /api/v1/audit/verify`.

**merchant growth** (`/merchant`) — aov lift against baseline, upsell conversion, cart abandonment, guardrail interception count, plus segments and bounded-budget campaigns.

**demo scenarios** (`/scenarios`) — one card per preset scenario, each labelled with the decision code it is meant to produce, with the agent trace and raw payload expanded on demand.

---

## layout

```
src/
  lib/
    api.ts        typed client for every backend route; ApiError carries FastAPI's `detail`
    types.ts      mirrors the backend pydantic models
    format.ts     inr/percent/date formatting, idempotency key generation
    useAsync.ts   fetch-on-mount with manual reload
  state/
    session.tsx   buyer id, server-side cart id, active approval token
  components/
    ui.tsx            panel, badge, stat, spinner, empty, error, json, row
    PolicyPanel.tsx   decision code, bounded amount, per-rule pass/fail
    PaymentLink.tsx   razorpay hosted-checkout link: pay now, copy, raw url
    ReasoningTrace.tsx  agent-by-agent trace
    PageHeader.tsx
  pages/          one file per screen
```

### notes on behaviour

- several endpoints return `404` when there is genuinely nothing yet — an empty audit ledger, no captured orders for analytics. those render as guidance rather than as failures.
- the cart id is kept in `localStorage` and re-attached on load; if the backend no longer has it, the reference is dropped silently.
- the buyer id in the sidebar is sent as `user_id` on every write, so spend limits can be observed per buyer.
