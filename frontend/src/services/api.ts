import {
  Product,
  GuardrailConfig,
  MerchantKPIs,
  Campaign,
  AuditRecord,
  AuditChainVerificationResult,
  CustomerSegment
} from "../types";

const BASE_URL = "/api/v1";

export const api = {
  // Chat
  sendChatMessage: async (message: string, approvalToken?: string, idempotencyKey?: string, sku?: string) => {
    const res = await fetch(`${BASE_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_message: message,
        approval_token: approvalToken,
        idempotency_key: idempotencyKey,
        sku: sku
      })
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // ACP Machine Discovery & Quote
  getACPCatalog: async () => {
    const res = await fetch(`${BASE_URL}/acp/catalog`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  getACPQuote: async (skus: string[], includeBundles: boolean = true) => {
    const res = await fetch(`${BASE_URL}/acp/quote`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        skus,
        include_upsell_bundles: includeBundles,
        agent_id: "external_ai_buyer_eval"
      })
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  executeACPCheckout: async (quoteId: string, idempotencyKey: string) => {
    const res = await fetch(`${BASE_URL}/acp/checkout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        quote_id: quoteId,
        idempotency_key: idempotencyKey,
        buyer_agent_id: "external_ai_buyer_eval"
      })
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  getMCPToolsSchema: async () => {
    const res = await fetch(`${BASE_URL}/acp/mcp-schema`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // Merchant Analytics & Campaigns
  getMerchantAnalytics: async (): Promise<{ kpis: MerchantKPIs; segments: CustomerSegment[]; campaigns: Campaign[] }> => {
    const res = await fetch(`${BASE_URL}/merchant/analytics`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  createCampaign: async (campaign: Partial<Campaign>) => {
    const res = await fetch(`${BASE_URL}/merchant/campaigns`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(campaign)
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // Guardrails
  getGuardrailConfig: async (): Promise<GuardrailConfig> => {
    const res = await fetch(`${BASE_URL}/guardrails/config`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  updateGuardrailConfig: async (config: GuardrailConfig): Promise<GuardrailConfig> => {
    const res = await fetch(`${BASE_URL}/guardrails/config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config)
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // Cryptographic Audit
  getAuditRecords: async (): Promise<AuditRecord[]> => {
    const res = await fetch(`${BASE_URL}/audit/records`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  verifyAuditChain: async (): Promise<AuditChainVerificationResult> => {
    const res = await fetch(`${BASE_URL}/audit/verify`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  simulateTampering: async (recordIndex: number, alteredAmount: number) => {
    const res = await fetch(`${BASE_URL}/audit/tamper-test`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        record_index: recordIndex,
        altered_amount: alteredAmount
      })
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // Guided Scenarios Runner
  runScenario: async (scenarioId: string) => {
    const res = await fetch(`${BASE_URL}/scenarios/run/${scenarioId}`, {
      method: "POST"
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }
};
