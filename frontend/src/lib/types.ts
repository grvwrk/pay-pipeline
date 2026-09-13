export interface Product {
  id: string;
  name: string;
  category: string;
  price: number;
  currency: string;
  inventory: number;
  rating: number;
  review_count: number;
  shipping_eta_hours: number;
  tags: string[];
  specs: Record<string, unknown>;
  complementary_product_ids: string[];
  image_url?: string | null;
  description: string;
}

export interface CartItem {
  product_id: string;
  name: string;
  price: number;
  quantity: number;
  subtotal: number;
  category: string;
  specs: Record<string, unknown>;
}

export interface BundleOffer {
  bundle_id: string;
  title: string;
  description: string;
  primary_product_id: string;
  primary_product_name: string;
  complementary_product_id: string;
  complementary_product_name: string;
  original_combined_price: number;
  discounted_bundle_price: number;
  savings_amount: number;
  discount_percentage: number;
  rationale: string;
}

export interface Cart {
  cart_id: string;
  user_id: string;
  items: CartItem[];
  subtotal_amount: number;
  discount_amount: number;
  applied_bundle?: BundleOffer | null;
  shipping_fee: number;
  total_amount: number;
  currency: string;
}

export type TransactionState =
  | "DISCOVERED" | "SELECTED" | "CART_CREATED" | "GUARDRAIL_EVALUATED"
  | "PENDING_APPROVAL" | "ORDER_CREATED" | "PAYMENT_PENDING"
  | "PAYMENT_CAPTURED" | "PAYMENT_FAILED" | "COMPLETED" | "REFUNDED" | "DENIED";

export interface Order {
  order_id: string;
  cart_id: string;
  amount: number;
  amount_in_paise?: number | null;
  currency: string;
  status: string;
  receipt: string;
  created_at: string;
  notes: Record<string, string>;
  state: TransactionState;
  idempotency_key?: string | null;
}

export interface PolicyRuleEvaluation {
  rule_name: string;
  passed: boolean;
  description: string;
  threshold_value: unknown;
  actual_value: unknown;
}

export interface PolicyEvaluation {
  allowed: boolean;
  decision_code: string;
  reason: string;
  requires_human_approval: boolean;
  approval_token?: string | null;
  rule_evaluations: PolicyRuleEvaluation[];
  evaluated_at: string;
  bounded_amount: number;
  max_allowed_amount: number;
}

/** Shape returned by money_tools.create_order_guarded (checkout + chat). */
export interface GuardedOrderResult {
  success: boolean;
  order?: Order;
  payment_link?: string | null;
  policy_evaluation?: PolicyEvaluation;
  requires_approval?: boolean;
  approval_token?: string | null;
  reason?: string;
  decision_code?: string;
  /** Why no `payment_link` was issued, when the gateway refused to mint one. */
  payment_link_error?: string | null;
}

export interface PaymentResult {
  payment_id: string;
  order_id: string;
  amount: number;
  currency: string;
  status: string;
  method: string;
  captured_at: string;
  webhook_verified: boolean;
  error_code?: string | null;
  error_description?: string | null;
}

export interface RefundResult {
  refund_id: string;
  payment_id: string;
  order_id?: string | null;
  amount: number;
  currency: string;
  status: string;
  reason: string;
  processed_at: string;
}

export interface GuardrailConfig {
  max_transaction_amount_inr: number;
  max_cumulative_spend_inr: number;
  approval_threshold_inr: number;
  max_item_quantity: number;
  allowed_currency: string;
  allowed_categories: string[];
  merchant_whitelist: string[];
}

export interface AuditRecord {
  index: number;
  timestamp: string;
  event_id: string;
  prev_hash: string;
  record_hash: string;
  actor_id: string;
  actor_role: string;
  action: string;
  intent?: string | null;
  tool_name?: string | null;
  arguments: Record<string, unknown>;
  guardrail_decision?: string | null;
  approval_required: boolean;
  transaction_state?: string | null;
  result_status: string;
  signature: string;
  explainability_notes: string;
  latency_ms: number;
}

export interface MerchantAnalytics {
  kpis: {
    total_revenue_inr: number;
    average_order_value_inr: number;
    baseline_aov_without_agent_inr: number;
    aov_growth_percentage: number;
    upsell_conversion_rate: number;
    cart_abandonment_rate: number;
    guardrail_interceptions_count: number;
    total_orders_processed: number;
  };
  segments: Array<{
    id: string; name: string; description: string;
    affinity_categories: string[]; average_order_value: number;
    customer_count: number; upsell_propensity_score: number;
  }>;
  campaigns: Campaign[];
}

export interface Campaign {
  id: string;
  title: string;
  target_segment: string;
  trigger_condition: string;
  bundle_offer: string;
  discount_percentage: number;
  max_budget_inr: number;
  spent_budget_inr: number;
  conversions: number;
  revenue_generated_inr: number;
  status: string;
}

export interface ReasoningStep {
  agent_name: string;
  thought: string;
  action: string;
  latency_ms: number;
  tool_called?: string;
  arguments?: Record<string, unknown>;
  result_summary?: string;
}

export type ChatResponseType =
  | "CATALOG_DISCOVERY" | "ORDER_CREATED" | "APPROVAL_REQUIRED" | "GUARDRAIL_DENIED"
  | "REFUND_PROCESSED" | "REFUND_DENIED" | "REFUND_REQUIRES_INFO"
  | "ORDER_STATUS" | "PAYMENT_STATUS" | "STATUS_NOT_FOUND"
  | "CHECKOUT_UNAVAILABLE" | "UNKNOWN_INTENT";

export interface ChatResponse {
  type: ChatResponseType;
  message: string;
  products?: Product[];
  top_choice?: Product | null;
  upsell_bundle?: BundleOffer | null;
  order?: Order | Record<string, unknown>;
  payment_link?: string | null;
  /** Why no `payment_link` was issued, when the gateway refused to mint one. */
  payment_link_error?: string | null;
  cart?: Cart;
  policy_evaluation?: PolicyEvaluation;
  approval_token?: string | null;
  decision_code?: string;
  refund?: RefundResult;
  payment?: PaymentResult;
  reasoning_steps?: ReasoningStep[];
}

export interface Health {
  status: string;
  system: string;
  payment_mode: string;
  llm_provider: string;
  database: string;
}

/**
 * Result of pulling an order's authoritative status from Razorpay instead of
 * waiting for a webhook. `outcome` is the gateway's verdict, `state` the local
 * transaction state after applying it.
 */
export interface ReconcileResult {
  order_id: string;
  changed: boolean;
  outcome: "captured" | "failed" | "pending" | "already_settled" | "unsupported" | "unreachable" | "rejected" | "error";
  code?: string;
  state: TransactionState;
  detail: string;
  payment_id?: string | null;
}

export interface ReconcileSummary {
  checked: number;
  updated: number;
  results: ReconcileResult[];
}
