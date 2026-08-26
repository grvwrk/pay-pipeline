# pay-pipeline

an agent system built on razorpay test-mode apis, built to do two things: grow a merchant's revenue, and make that merchant transactable by an ai buyer end to end.

every money-moving action passes through a guardrail before it reaches razorpay — bounded by configurable limits, gated behind approval where required, and logged into a tamper-evident audit trail. nothing executes because a model decided to.

---

## architecture

```mermaid
flowchart TD
    subgraph Client_Layer ["Client & Buyer Layer"]
        HumanBuyer["Human Buyer (Conversational UI)"]
        AIBuyer["External AI Buyer (ACP / MCP Protocol)"]
        MerchantAdmin["Merchant Dashboard (Growth & Campaigns)"]
    end

    subgraph Orchestrator_Layer ["Multi-Agent Orchestrator"]
        IntentRouter["Intent Router Step"]
        CatalogAgent["Catalog Agent Step"]
        UpsellAgent["Upsell & Cross-Sell Agent Step"]
        CheckoutAgent["Checkout Agent Step"]
    end

    subgraph Security_Layer ["Deterministic Guardrail & Policy Engine"]
        GuardrailEngine["Policy Engine (Model-Independent)"]
        RuleSpendLimit["Configurable Spend Limit"]
        RuleCurrency["Currency Check (INR)"]
        RuleApproval["Configurable Approval Gate"]
        RuleIdempotency["Idempotency Keys"]
    end

    subgraph Tool_Layer ["Separated Capability Tool Layer"]
        ReadTools["Read & Decision Tools"]
        MoneyTools["Privileged Money Tools"]
    end

    subgraph Payment_Layer ["Razorpay Rail & State Machine"]
        RazorpayClient["Razorpay Test API Client"]
        WebhookReceiver["Authoritative Webhook Receiver"]
        TxnStateMachine["Transaction State Machine"]
    end

    subgraph Audit_Layer ["Cryptographic Audit & Explainability"]
        HashChain["Hash Chain"]
        HMACSig["Digital Signatures"]
    end

    HumanBuyer --> IntentRouter
    AIBuyer -->|ACP / MCP API| IntentRouter
    IntentRouter --> CatalogAgent
    IntentRouter --> UpsellAgent
    IntentRouter --> CheckoutAgent

    CatalogAgent --> ReadTools
    UpsellAgent --> ReadTools
    CheckoutAgent --> GuardrailEngine

    GuardrailEngine --> RuleSpendLimit
    GuardrailEngine --> RuleCurrency
    GuardrailEngine --> RuleApproval
    GuardrailEngine --> RuleIdempotency

    GuardrailEngine -->|APPROVED| MoneyTools
    GuardrailEngine -->|DENIED| Audit_Layer

    MoneyTools --> RazorpayClient
    RazorpayClient --> WebhookReceiver
    WebhookReceiver --> TxnStateMachine
    TxnStateMachine --> Audit_Layer
    ReadTools --> Audit_Layer
```

---

## implementation

### client layer
human buyers, external ai buyers over acp/mcp, and the merchant dashboard all enter through the same intent router — one entry point regardless of who's asking.

### orchestrator
an event-driven workflow splits every incoming request into typed steps: intent routing, catalog lookup, upsell/cross-sell, checkout. none of these steps holds access to a money tool directly — they can only reach the guardrail.

### guardrail & policy engine
sits between the orchestrator and the money tools, independent of any model. checks spend limits, currency, approval requirements, and idempotency before anything is allowed through. limits are configurable, not hardcoded — set by the merchant, not baked into the code.

### tool layer
split by privilege. read/decision tools handle catalog and bundling logic and never touch money. money tools create orders and capture payments, and only unlock once the guardrail approves the request.

### payment layer
a razorpay test-mode client paired with an authoritative webhook receiver. an order stays pending until the webhook confirms it — the system never marks a payment complete on its own.

### audit layer
every decision, guardrail check, and payment event gets hash-chained and signed. tampering is detectable, and every action taken by the system can be traced back to why it happened.