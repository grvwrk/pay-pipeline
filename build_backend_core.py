import os, json, uuid, datetime
from typing import List, Optional, Dict, Any

def write(filepath, content):
    d = os.path.dirname(filepath)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Wrote: {filepath}")

# 1. Package Init & Config
write('backend/app/__init__.py', '__version__ = "1.0.0"\n')

write('backend/app/config.py', '''import os
from pydantic import BaseModel
from typing import Optional, List

class Settings(BaseModel):
    PROJECT_NAME: str = "AeroPay - Agentic Commerce & Revenue Growth Engine"
    API_V1_STR: str = "/api/v1"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    # Razorpay Test Credentials (supports mock simulation or real live test mode)
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "rzp_test_aeropay_demo_key")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "rzp_test_secret_aeropay_2026")
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "whsec_aeropay_webhook_secret_9988")
    
    # Cryptographic Audit Secret
    AUDIT_HMAC_SECRET: str = os.getenv("AUDIT_HMAC_SECRET", "aeropay_cryptographic_audit_signing_key_402")
    
    # Deterministic Guardrail Defaults
    DEFAULT_MAX_TXN_AMOUNT_INR: float = 5000.0   # max ₹5,000 per order
    DEFAULT_MAX_CUMULATIVE_SPEND_INR: float = 15000.0  # max ₹15,000 cumulative
    DEFAULT_APPROVAL_THRESHOLD_INR: float = 3000.0  # orders > ₹3,000 require human confirmation
    DEFAULT_MAX_ITEM_QUANTITY: int = 5
    ALLOWED_CURRENCY: str = "INR"
    ALLOWED_CATEGORIES: List[str] = [
        "mechanical_keyboards",
        "computer_peripherals",
        "workspace_accessories",
        "developer_gear",
        "ergonomics",
        "audio_equipment"
    ]
    MERCHANT_ID: str = "merch_aeropay_electronics_01"
    MERCHANT_NAME: str = "AeroNation Tech & Lifestyle Store"

settings = Settings()
''')

# 2. Models
write('backend/app/models/catalog.py', '''from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class Product(BaseModel):
    id: str = Field(..., description="Unique Product SKU/ID")
    name: str = Field(..., description="Product display name")
    category: str = Field(..., description="Category classification")
    price: float = Field(..., description="Price in INR")
    currency: str = Field("INR", description="Currency code")
    inventory: int = Field(..., description="Available stock count")
    rating: float = Field(4.5, description="Product customer rating (0-5)")
    review_count: int = Field(0, description="Number of verified reviews")
    shipping_eta_hours: int = Field(24, description="Expected dispatch time in hours")
    tags: List[str] = Field(default_factory=list, description="Search and semantic tags")
    specs: Dict[str, Any] = Field(default_factory=dict, description="Technical specifications")
    complementary_product_ids: List[str] = Field(default_factory=list, description="Affinity product IDs for upsell/cross-sell")
    image_url: Optional[str] = None
    description: str = ""

class ProductFilter(BaseModel):
    query: Optional[str] = None
    category: Optional[str] = None
    max_price: Optional[float] = None
    min_rating: Optional[float] = None
    in_stock_only: bool = True
    tags: Optional[List[str]] = None
''')

write('backend/app/models/cart.py', '''from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid

class CartItem(BaseModel):
    product_id: str
    name: str
    price: float
    quantity: int = 1
    subtotal: float
    category: str = ""
    specs: Dict[str, Any] = Field(default_factory=dict)

class BundleOffer(BaseModel):
    bundle_id: str
    title: str
    description: str
    primary_product_id: str
    primary_product_name: str
    complementary_product_id: str
    complementary_product_name: str
    original_combined_price: float
    discounted_bundle_price: float
    savings_amount: float
    discount_percentage: float
    rationale: str

class Cart(BaseModel):
    cart_id: str = Field(default_factory=lambda: f"cart_{uuid.uuid4().hex[:10]}")
    user_id: str = "user_default_buyer"
    items: List[CartItem] = Field(default_factory=list)
    subtotal: float = 0.0
    discount_amount: float = 0.0
    applied_bundle: Optional[BundleOffer] = None
    shipping_fee: float = 0.0
    total_amount: float = 0.0
    currency: str = "INR"

    def recalculate(self):
        self.subtotal = sum(item.subtotal for item in self.items)
        if self.applied_bundle:
            self.discount_amount = self.applied_bundle.savings_amount
        else:
            self.discount_amount = 0.0
        self.total_amount = max(0.0, self.subtotal - self.discount_amount + self.shipping_fee)
''')

write('backend/app/models/guardrail.py', '''from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
import datetime

class DecisionCode(str, Enum):
    APPROVED = "APPROVED"
    DENIED_SPEND_LIMIT = "DENIED_SPEND_LIMIT"
    DENIED_CUMULATIVE_LIMIT = "DENIED_CUMULATIVE_LIMIT"
    DENIED_UNAUTHORIZED_CATEGORY = "DENIED_UNAUTHORIZED_CATEGORY"
    DENIED_UNAUTHORIZED_MERCHANT = "DENIED_UNAUTHORIZED_MERCHANT"
    DENIED_CURRENCY_MISMATCH = "DENIED_CURRENCY_MISMATCH"
    DENIED_QUANTITY_EXCEEDED = "DENIED_QUANTITY_EXCEEDED"
    DENIED_IDEMPOTENCY_COLLISION = "DENIED_IDEMPOTENCY_COLLISION"
    GATED_APPROVAL_REQUIRED = "GATED_APPROVAL_REQUIRED"

class PolicyRuleEvaluation(BaseModel):
    rule_name: str
    passed: bool
    description: str
    threshold_value: Any = None
    actual_value: Any = None

class PolicyEvaluationResult(BaseModel):
    allowed: bool
    decision_code: DecisionCode
    reason: str
    requires_human_approval: bool = False
    approval_token: Optional[str] = None
    rule_evaluations: List[PolicyRuleEvaluation] = Field(default_factory=list)
    evaluated_at: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    bounded_amount: float
    max_allowed_amount: float

class GuardrailConfig(BaseModel):
    max_transaction_amount_inr: float = 5000.0
    max_cumulative_spend_inr: float = 15000.0
    approval_threshold_inr: float = 3000.0
    max_item_quantity: int = 5
    allowed_currency: str = "INR"
    allowed_categories: List[str] = [
        "mechanical_keyboards",
        "computer_peripherals",
        "workspace_accessories",
        "developer_gear",
        "ergonomics",
        "audio_equipment"
    ]
    merchant_whitelist: List[str] = ["merch_aeropay_electronics_01"]
''')

write('backend/app/models/order.py', '''from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
import datetime

class TransactionState(str, Enum):
    DISCOVERED = "DISCOVERED"
    SELECTED = "SELECTED"
    CART_CREATED = "CART_CREATED"
    GUARDRAIL_EVALUATED = "GUARDRAIL_EVALUATED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ORDER_CREATED = "ORDER_CREATED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAYMENT_CAPTURED = "PAYMENT_CAPTURED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    COMPLETED = "COMPLETED"
    REFUNDED = "REFUNDED"
    DENIED = "DENIED"

class RazorpayOrder(BaseModel):
    order_id: str
    cart_id: str
    amount: float # in INR
    amount_in_paise: int
    currency: str = "INR"
    status: str = "created"
    receipt: str
    created_at: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    notes: Dict[str, str] = Field(default_factory=dict)
    state: TransactionState = TransactionState.ORDER_CREATED
    idempotency_key: Optional[str] = None

class PaymentCaptureResult(BaseModel):
    payment_id: str
    order_id: str
    amount: float
    currency: str = "INR"
    status: str # "captured" or "failed"
    method: str = "upi"
    captured_at: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    razorpay_signature: Optional[str] = None
    webhook_verified: bool = False
    error_code: Optional[str] = None
    error_description: Optional[str] = None

class RefundResult(BaseModel):
    refund_id: str
    payment_id: str
    order_id: str
    amount: float
    currency: str = "INR"
    status: str = "processed"
    reason: str
    processed_at: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
''')

write('backend/app/models/audit.py', '''from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import datetime

class AuditRecord(BaseModel):
    index: int
    timestamp: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    event_id: str
    prev_hash: str
    record_hash: str
    actor_id: str
    actor_role: str # USER, INTENT_ROUTER, CATALOG_AGENT, UPSELL_AGENT, CHECKOUT_AGENT, GUARDRAIL_ENGINE, RAZORPAY_API, WEBHOOK_RECEIVER, EXTERNAL_AI_BUYER
    action: str
    intent: Optional[str] = None
    tool_name: Optional[str] = None
    arguments: Dict[str, Any] = Field(default_factory=dict)
    guardrail_decision: Optional[str] = None
    approval_required: bool = False
    transaction_state: Optional[str] = None
    result_status: str # SUCCESS, DENIED, FAILED, PENDING
    signature: str # HMAC-SHA256 signature
    explainability_notes: str = ""

class AuditChainVerificationResult(BaseModel):
    is_valid: bool
    total_records: int
    genesis_hash: str
    latest_hash: str
    tampered_index: Optional[int] = None
    error_detail: Optional[str] = None
    verified_at: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")

class ExplainabilityReport(BaseModel):
    event_id: str
    timestamp: str
    user_intent: str
    selected_items: List[Dict[str, Any]]
    agent_reasoning: str
    upsell_contribution: Dict[str, Any]
    guardrail_check_summary: Dict[str, Any]
    money_action_proof: Dict[str, Any]
    cryptographic_hash: str
    signature: str
''')

write('backend/app/models/acp.py', '''from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ACPProductSummary(BaseModel):
    sku: str
    name: str
    category: str
    price_inr: float
    stock_status: str
    spec_summary: Dict[str, Any]
    direct_checkout_supported: bool = True

class ACPDiscoveryResponse(BaseModel):
    protocol_version: str = "ACP/1.0"
    merchant_id: str
    merchant_name: str
    currency: str = "INR"
    catalog: List[ACPProductSummary]
    spend_limit_inr: float
    direct_order_supported: bool = True
    mcp_tools_url: str

class ACPQuoteRequest(BaseModel):
    skus: List[str]
    quantities: List[int] = Field(default_factory=lambda: [1])
    include_upsell_bundles: bool = True
    agent_id: str = "ai_buyer_agent_ext"

class ACPQuoteResponse(BaseModel):
    quote_id: str
    skus: List[str]
    subtotal: float
    bundle_discount: float
    total_amount: float
    currency: str = "INR"
    guardrail_precheck: str # "PASS" or "DENIED"
    expires_in_seconds: int = 300

class ACPCheckoutRequest(BaseModel):
    quote_id: str
    idempotency_key: str
    buyer_agent_id: str
    delivery_instructions: str = "Digital/Express Dispatch"

class ACPCheckoutResponse(BaseModel):
    status: str # "ORDER_CREATED" or "DENIED"
    order_id: Optional[str] = None
    amount: float
    currency: str = "INR"
    razorpay_payment_link: Optional[str] = None
    audit_event_id: str
    signature: str
    message: str
''')

write('backend/app/models/campaign.py', '''from pydantic import BaseModel, Field
from typing import List, Optional

class CustomerSegment(BaseModel):
    id: str
    name: str
    description: str
    affinity_categories: List[str]
    average_order_value: float
    customer_count: int
    upsell_propensity_score: float # 0.0 to 1.0

class Campaign(BaseModel):
    id: str
    title: str
    target_segment: str
    trigger_condition: str
    bundle_offer: str
    discount_percentage: float
    max_budget_inr: float
    spent_budget_inr: float = 0.0
    conversions: int = 0
    revenue_generated_inr: float = 0.0
    status: str = "ACTIVE" # ACTIVE, PAUSED, COMPLETED
''')

# 3. Data
catalog_data = [
    {
        "id": "sku_kb_keychron_k2",
        "name": "Keychron K2 V2 Wireless Mechanical Keyboard",
        "category": "mechanical_keyboards",
        "price": 4499.0,
        "currency": "INR",
        "inventory": 28,
        "rating": 4.8,
        "review_count": 342,
        "shipping_eta_hours": 24,
        "tags": ["mechanical_keyboard", "wireless", "bluetooth", "hot_swappable", "mac_windows", "rgb", "brown_switch"],
        "specs": {"switches": "Gateron G Pro Brown", "layout": "75% compact (84 keys)", "battery": "4000mAh", "connectivity": "Bluetooth 5.1 & Type-C"},
        "complementary_product_ids": ["sku_acc_wrist_rest_walnut", "sku_acc_keycap_puller_kit"],
        "image_url": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=600&auto=format&fit=crop&q=80",
        "description": "75% layout compact wireless mechanical keyboard designed for maximum productivity and premium tactile typing."
    },
    {
        "id": "sku_kb_royal_kludge_rk84",
        "name": "Royal Kludge RK84 Tri-Mode RGB Mechanical Keyboard",
        "category": "mechanical_keyboards",
        "price": 3999.0,
        "currency": "INR",
        "inventory": 45,
        "rating": 4.6,
        "review_count": 512,
        "shipping_eta_hours": 24,
        "tags": ["mechanical_keyboard", "tri_mode", "rgb", "hot_swappable", "red_switch", "budget_friendly"],
        "specs": {"switches": "RK Red Linear Switches", "layout": "84 Keys", "connectivity": "2.4Ghz, BT 5.0, USB-C", "battery": "3750mAh"},
        "complementary_product_ids": ["sku_acc_wrist_rest_walnut", "sku_acc_custom_coiled_cable"],
        "image_url": "https://images.unsplash.com/photo-1618384887929-16ec33fab9ef?w=600&auto=format&fit=crop&q=80",
        "description": "Ultra-versatile 84-key mechanical keyboard with tri-mode connectivity and smooth linear switches."
    },
    {
        "id": "sku_kb_ducky_one3_tkl",
        "name": "Ducky One 3 TKL Pure White Mechanical Keyboard",
        "category": "mechanical_keyboards",
        "price": 4899.0,
        "currency": "INR",
        "inventory": 14,
        "rating": 4.9,
        "review_count": 189,
        "shipping_eta_hours": 48,
        "tags": ["mechanical_keyboard", "tkl", "cherry_mx", "pbt_keycaps", "audiophile_acoustics"],
        "specs": {"switches": "Cherry MX Blue / Brown", "layout": "Tenkeyless (80%)", "keycaps": "Double-Shot PBT", "foam": "Silicone sound dampening"},
        "complementary_product_ids": ["sku_acc_wrist_rest_walnut", "sku_acc_deskmat_leather"],
        "image_url": "https://images.unsplash.com/photo-1595225476474-87563907a212?w=600&auto=format&fit=crop&q=80",
        "description": "Enthusiast grade mechanical keyboard with sound-dampening silicone layer and Cherry MX switches."
    },
    {
        "id": "sku_kb_custom_pro_aluminium",
        "name": "AeroPro CNC Anodized Aluminium Gasket Keyboard",
        "category": "mechanical_keyboards",
        "price": 7999.0,
        "currency": "INR",
        "inventory": 8,
        "rating": 4.95,
        "review_count": 87,
        "shipping_eta_hours": 24,
        "tags": ["mechanical_keyboard", "premium", "gasket_mount", "aluminium_body", "high_end"],
        "specs": {"body": "CNC 6063 Aluminum", "weight": "1.8kg", "mount": "Gasket with Poron Foam", "switches": "Gateron Oil King"},
        "complementary_product_ids": ["sku_acc_custom_coiled_cable", "sku_acc_deskmat_leather"],
        "image_url": "https://images.unsplash.com/photo-1541140532154-b024d705b909?w=600&auto=format&fit=crop&q=80",
        "description": "Flagship full CNC-machined aluminium gasket mounted keyboard for connoisseurs."
    },
    {
        "id": "sku_acc_wrist_rest_walnut",
        "name": "Ergonomic Solid Walnut Wood Keyboard Wrist Rest",
        "category": "workspace_accessories",
        "price": 499.0,
        "currency": "INR",
        "inventory": 120,
        "rating": 4.85,
        "review_count": 430,
        "shipping_eta_hours": 12,
        "tags": ["wrist_rest", "ergonomics", "walnut_wood", "keyboard_accessory", "anti_slip"],
        "specs": {"material": "Natural Solid Walnut Wood", "size": "317mm x 80mm x 19mm", "finish": "Natural Organic Wax Oil"},
        "complementary_product_ids": ["sku_kb_keychron_k2", "sku_kb_royal_kludge_rk84"],
        "image_url": "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=600&auto=format&fit=crop&q=80",
        "description": "Handcrafted solid walnut wrist rest designed to maintain neutral wrist posture during long sessions."
    },
    {
        "id": "sku_acc_custom_coiled_cable",
        "name": "Aviator Coiled USB-C Braided Keyboard Cable",
        "category": "computer_peripherals",
        "price": 799.0,
        "currency": "INR",
        "inventory": 60,
        "rating": 4.7,
        "review_count": 210,
        "shipping_eta_hours": 24,
        "tags": ["cable", "aviator_connector", "coiled_cable", "usb_c", "custom_keyboard"],
        "specs": {"connector": "GX12 4-Pin Aviator", "sleeve": "Double-sleeved Paracord + Techflex", "length": "1.5m + 15cm coil"},
        "complementary_product_ids": ["sku_kb_keychron_k2", "sku_kb_royal_kludge_rk84"],
        "image_url": "https://images.unsplash.com/photo-1544652478-6653e09f18a2?w=600&auto=format&fit=crop&q=80",
        "description": "Custom mechanical keyboard cable with metallic aviator detachable connector."
    },
    {
        "id": "sku_acc_deskmat_leather",
        "name": "AeroNation Premium Vegan Leather Desk Mat (90x40cm)",
        "category": "workspace_accessories",
        "price": 699.0,
        "currency": "INR",
        "inventory": 90,
        "rating": 4.75,
        "review_count": 380,
        "shipping_eta_hours": 24,
        "tags": ["deskmat", "mousepad", "waterproof", "vegan_leather", "desk_pad"],
        "specs": {"dimensions": "900 x 400 x 2mm", "material": "Dual-sided PU Leather", "features": "Waterproof, easy wipe clean"},
        "complementary_product_ids": ["sku_kb_keychron_k2", "sku_mouse_ergo_vertical"],
        "image_url": "https://images.unsplash.com/photo-1629429408209-1f912961dbd8?w=600&auto=format&fit=crop&q=80",
        "description": "Spacious water-resistant desk protector mat for keyboard and mouse precision."
    },
    {
        "id": "sku_mouse_ergo_vertical",
        "name": "AeroGrip Ergonomic Wireless Vertical Mouse",
        "category": "ergonomics",
        "price": 1899.0,
        "currency": "INR",
        "inventory": 55,
        "rating": 4.7,
        "review_count": 295,
        "shipping_eta_hours": 24,
        "tags": ["mouse", "ergonomic", "vertical_mouse", "wireless", "rsi_prevention"],
        "specs": {"angle": "57 degrees natural handshake angle", "dpi": "800-1600-2400 DPI", "sensor": "Optical Precision", "battery": "Rechargeable Type-C"},
        "complementary_product_ids": ["sku_acc_deskmat_leather", "sku_acc_wrist_rest_walnut"],
        "image_url": "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=600&auto=format&fit=crop&q=80",
        "description": "Ergonomically sculpted vertical mouse designed to prevent carpal tunnel strain and arm fatigue."
    },
    {
        "id": "sku_audio_anc_headset",
        "name": "AeroSound Pro Hybrid ANC Wireless Headphones",
        "category": "audio_equipment",
        "price": 3499.0,
        "currency": "INR",
        "inventory": 32,
        "rating": 4.8,
        "review_count": 220,
        "shipping_eta_hours": 24,
        "tags": ["audio", "anc", "noise_cancelling", "bluetooth_5_3", "spatial_audio", "hi_res"],
        "specs": {"drivers": "40mm Titanium Dynamic", "anc_depth": "38dB Hybrid Active Noise Cancellation", "battery_life": "50 Hours Playtime"},
        "complementary_product_ids": ["sku_acc_headphone_stand_wood"],
        "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&auto=format&fit=crop&q=80",
        "description": "Immersive studio headphones with high-res active noise cancellation for deep work focus."
    },
    {
        "id": "sku_acc_headphone_stand_wood",
        "name": "Minimalist Solid Oak Headphone Stand",
        "category": "workspace_accessories",
        "price": 599.0,
        "currency": "INR",
        "inventory": 40,
        "rating": 4.6,
        "review_count": 110,
        "shipping_eta_hours": 24,
        "tags": ["headphone_stand", "desk_accessory", "wood", "minimalist"],
        "specs": {"material": "Solid Oak + Matte Aluminium Pillar", "base": "Weighted anti-slip silicon base"},
        "complementary_product_ids": ["sku_audio_anc_headset"],
        "image_url": "https://images.unsplash.com/photo-1584679109597-c656b19974c9?w=600&auto=format&fit=crop&q=80",
        "description": "Architectural headphone display stand keeping desk clear and organized."
    },
    {
        "id": "sku_dev_screenbar_light",
        "name": "AeroBeam Pro Monitor ScreenBar LED Light Bar",
        "category": "developer_gear",
        "price": 2299.0,
        "currency": "INR",
        "inventory": 38,
        "rating": 4.85,
        "review_count": 310,
        "shipping_eta_hours": 24,
        "tags": ["screenbar", "desk_light", "eye_care", "anti_glare", "touch_control"],
        "specs": {"lighting": "Asymmetric Optical Design (Zero Screen Glare)", "color_temp": "2800K - 6500K Adjustable", "power": "USB 5V/1A"},
        "complementary_product_ids": ["sku_acc_deskmat_leather", "sku_kb_keychron_k2"],
        "image_url": "https://images.unsplash.com/photo-1593642632823-8f785ba67e45?w=600&auto=format&fit=crop&q=80",
        "description": "Asymmetric glare-free monitor light bar engineered to protect eyes during late-night coding sessions."
    },
    {
        "id": "sku_dev_usbc_dock_11in1",
        "name": "AeroConnect 11-in-1 Dual 4K USB-C Hub & Dock",
        "category": "developer_gear",
        "price": 2999.0,
        "currency": "INR",
        "inventory": 25,
        "rating": 4.7,
        "review_count": 190,
        "shipping_eta_hours": 24,
        "tags": ["usb_hub", "docking_station", "dual_4k_hdmi", "100w_power_delivery", "gigabit_ethernet"],
        "specs": {"ports": "2x HDMI 4K@60Hz, 1x 100W PD USB-C, 3x USB 3.0, 1x Gigabit RJ45, SD/TF, Audio Jack", "chassis": "Aerospace Grade Aluminum"},
        "complementary_product_ids": ["sku_dev_screenbar_light", "sku_kb_keychron_k2"],
        "image_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=600&auto=format&fit=crop&q=80",
        "description": "High speed 100W Power Delivery 11-in-1 multi-port docking station for multi-monitor developer setups."
    }
]

write('backend/app/data/catalog_db.json', json.dumps(catalog_data, indent=2))

campaigns_data = {
    "segments": [
        {
            "id": "seg_gamers_coders",
            "name": "Mechanical Keyboard & Workstation Enthusiasts",
            "description": "Buyers looking for tactile productivity gear, compact keyboards, and custom accessories.",
            "affinity_categories": ["mechanical_keyboards", "workspace_accessories", "developer_gear"],
            "average_order_value": 4200.0,
            "customer_count": 1420,
            "upsell_propensity_score": 0.88
        },
        {
            "id": "seg_ergonomic_focused",
            "name": "Ergonomic Health & Posture Focused Buyers",
            "description": "Professionals prioritizing wrist comfort, vertical ergonomics, and eye care.",
            "affinity_categories": ["ergonomics", "workspace_accessories", "developer_gear"],
            "average_order_value": 2850.0,
            "customer_count": 890,
            "upsell_propensity_score": 0.76
        },
        {
            "id": "seg_creators_audio",
            "name": "Creators, Streamers & Audio Producers",
            "description": "Buyers demanding high fidelity noise cancellation and acoustic workstation setups.",
            "affinity_categories": ["audio_equipment", "workspace_accessories"],
            "average_order_value": 3900.0,
            "customer_count": 620,
            "upsell_propensity_score": 0.81
        }
    ],
    "campaigns": [
        {
            "id": "camp_kb_tactile_bundle",
            "title": "Tactile Precision: Keyboard + Walnut Rest Bundle",
            "target_segment": "seg_gamers_coders",
            "trigger_condition": "When user adds mechanical keyboard to cart",
            "bundle_offer": "Get Solid Walnut Wrist Rest (Rs 499) at Rs 0 + 5% cart discount",
            "discount_percentage": 5.0,
            "max_budget_inr": 50000.0,
            "spent_budget_inr": 12450.0,
            "conversions": 83,
            "revenue_generated_inr": 414834.0,
            "status": "ACTIVE"
        },
        {
            "id": "camp_dev_eye_focus",
            "title": "Deep Work Focus: ScreenBar + Desk Mat Combo",
            "target_segment": "seg_ergonomic_focused",
            "trigger_condition": "When user views developer gear / desk accessories",
            "bundle_offer": "Save Rs 300 when bundling ScreenBar LED with Vegan Leather Desk Mat",
            "discount_percentage": 10.0,
            "max_budget_inr": 30000.0,
            "spent_budget_inr": 8100.0,
            "conversions": 54,
            "revenue_generated_inr": 161460.0,
            "status": "ACTIVE"
        }
    ]
}

write('backend/app/data/campaigns_db.json', json.dumps(campaigns_data, indent=2))
print("Part 1 successfully executed!")
