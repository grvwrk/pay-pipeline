import type {
  AuditRecord, Campaign, Cart, ChatResponse, GuardedOrderResult, GuardrailConfig,
  Health, MerchantAnalytics, Order, Product, ReconcileResult, ReconcileSummary, RefundResult,
} from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "";
const V1 = `${BASE}/api/v1`;

/** Error carrying the FastAPI `detail` string, so pages can show the real reason. */
export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError(0, "Cannot reach the backend. Is uvicorn running on :8000?");
  }

  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      // FastAPI puts a string here, or a list of validation objects for 422.
      if (typeof body?.detail === "string") detail = body.detail;
      else if (Array.isArray(body?.detail)) detail = body.detail.map((d: { msg: string }) => d.msg).join("; ");
    } catch {
      /* non-JSON error body; keep the status line */
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body ?? {}) });

function qs(params: Record<string, string | number | boolean | undefined | null>) {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export const api = {
  health: () => request<Health>(`${BASE}/health`),

  // --- catalog ---
  listProducts: (p: { query?: string; category?: string; max_price?: number; in_stock_only?: boolean } = {}) =>
    request<Product[]>(`${V1}/products${qs(p)}`),
  getProduct: (id: string) => request<Product>(`${V1}/products/${encodeURIComponent(id)}`),

  // --- cart ---
  createCart: (body: { user_id: string; items: Array<{ product_id: string; quantity?: number; include_bundle?: boolean }>; promo_code?: string | null }) =>
    post<Cart>(`${V1}/cart`, body),
  getCart: (cartId: string) => request<Cart>(`${V1}/cart/${encodeURIComponent(cartId)}`),
  addCartItem: (cartId: string, body: { product_id: string; quantity: number }) =>
    post<Cart>(`${V1}/cart/${encodeURIComponent(cartId)}/items`, body),
  removeCartItem: (cartId: string, productId: string) =>
    request<Cart>(`${V1}/cart/${encodeURIComponent(cartId)}/items/${encodeURIComponent(productId)}`, { method: "DELETE" }),

  // --- checkout / approval ---
  checkout: (body: { cart_id: string; user_id: string; idempotency_key?: string | null; approval_token?: string | null }) =>
    post<GuardedOrderResult>(`${V1}/checkout`, body),
  approve: (approval_token: string) =>
    post<{ status: string; approval_token: string; message: string }>(`${V1}/approve`, { approval_token }),

  // --- orders / payments / refunds ---
  listOrders: (limit = 50) => request<Order[]>(`${V1}/orders${qs({ limit })}`),
  getOrder: (id: string) => request<Order>(`${V1}/orders/${encodeURIComponent(id)}`),
  initiatePayment: (body: { order_id: string; amount_inr: number; method?: string; simulate_failure?: boolean; user_id?: string }) =>
    post<Record<string, unknown>>(`${V1}/payments/initiate`, body),
  getPayment: (id: string) => request<Record<string, unknown>>(`${V1}/payments/${encodeURIComponent(id)}`),
  reconcile: (orderId: string) =>
    post<ReconcileResult>(`${V1}/payments/reconcile/${encodeURIComponent(orderId)}`),
  reconcilePending: (limit = 50) =>
    post<ReconcileSummary>(`${V1}/payments/reconcile-pending${qs({ limit })}`),
  refund: (body: { payment_id: string; amount_inr: number; user_id: string; reason?: string }) =>
    post<{ success: boolean; refund: RefundResult }>(`${V1}/refund`, body),

  // --- guardrails ---
  getGuardrails: () => request<GuardrailConfig>(`${V1}/guardrails/config`),
  updateGuardrails: (config: GuardrailConfig) => post<GuardrailConfig>(`${V1}/guardrails/config`, config),

  // --- audit ---
  auditChain: () => request<{ total_events: number; chain: AuditRecord[] }>(`${V1}/audit/chain`),
  auditVerify: () => request<{ status: string; message: string; is_valid: boolean }>(`${V1}/audit/verify`),

  // --- merchant ---
  analytics: () => request<MerchantAnalytics>(`${V1}/merchant/analytics`),
  createCampaign: (campaign: Campaign) =>
    post<{ status: string; message: string }>(`${V1}/merchant/campaigns`, campaign),

  // --- agent ---
  chat: (body: {
    user_message: string; user_id: string; approval_token?: string | null;
    idempotency_key?: string | null; sku?: string | null; force_fail_payment?: boolean;
    include_bundle?: boolean;
  }) => post<ChatResponse>(`${V1}/chat`, body),

  runScenario: (id: string) => post<Record<string, unknown>>(`${V1}/scenarios/run/${encodeURIComponent(id)}`),
};
