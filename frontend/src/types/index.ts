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
  specs: Record<string, any>;
  complementary_product_ids: string[];
  image_url?: string;
  description: string;
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

export interface CartItem {
  product_id: string;
  name: string;
  price: number;
  quantity: number;
  subtotal: number;
  category: string;
}

export interface Cart {
  cart_id: string;
  user_id: string;
  items: CartItem[];
  subtotal: number;
  discount_amount: number;
  applied_bundle?: BundleOffer;
  shipping_fee: number;
  total_amount: number;
  currency: string;
}

export interface PolicyRuleEvaluation {
  rule_name: string;
  passed: boolean;
  description: string;
  threshold_value: any;
  actual_value: any;
}

export interface PolicyEvaluationResult {
  allowed: boolean;
  decision_code: string;
  reason: string;
  requires_human_approval: boolean;
  approval_token?: string;
  rule_evaluations: PolicyRuleEvaluation[];
  evaluated_at: string;
  bounded_amount: number;
  max_allowed_amount: number;
}

export interface RazorpayOrder {
  order_id: string;
  cart_id: string;
  amount: number;
  amount_in_paise: number;
  currency: string;
  status: string;
  receipt: string;
  created_at: string;
  notes: Record<string, string>;
  state: string;
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
  intent?: string;
  tool_name?: string;
  arguments: Record<string, any>;
  guardrail_decision?: string;
  approval_required: boolean;
  transaction_state?: string;
  result_status: string;
  signature: string;
  explainability_notes: string;
}

export interface AuditChainVerificationResult {
  is_valid: boolean;
  total_records: number;
  genesis_hash: string;
  latest_hash: string;
  tampered_index?: number;
  error_detail?: string;
  verified_at: string;
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

export interface MerchantKPIs {
  total_revenue_inr: number;
  average_order_value_inr: number;
  baseline_aov_without_agent_inr: number;
  aov_growth_percentage: number;
  upsell_conversion_rate: number;
  cart_abandonment_rate: number;
  guardrail_interceptions_count: number;
  total_orders_processed: number;
}

export interface CustomerSegment {
  id: string;
  name: string;
  description: string;
  affinity_categories: string[];
  average_order_value: number;
  customer_count: number;
  upsell_propensity_score: number;
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

export interface AgentReasoningStep {
  agent_name: string;
  thought: string;
  action?: string;
  tool_called?: string;
  arguments?: Record<string, any>;
  result_summary?: string;
}

export interface ChatMessage {
  id: string;
  sender: "user" | "agent" | "system";
  text: string;
  timestamp: string;
  products?: Product[];
  upsell_bundle?: BundleOffer;
  order?: RazorpayOrder;
  policy_evaluation?: PolicyEvaluationResult;
  requires_approval?: boolean;
  approval_token?: string;
  guardrail_denied?: boolean;
  reasoning_steps?: AgentReasoningStep[];
}
