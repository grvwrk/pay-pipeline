import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Header
from typing import Optional, Dict
from backend.app.config import settings
from backend.app.models.acp import (
    ACPDiscoveryResponse,
    ACPProductSummary,
    ACPQuoteRequest,
    ACPQuoteResponse,
    ACPCheckoutRequest,
    ACPCheckoutResponse
)
from backend.app.models.cart import Cart, CartItem
from backend.app.tools.read_tools import read_tools
from backend.app.tools.money_tools import money_tools
from backend.app.guardrails.policy_engine import policy_engine
from backend.app.audit.audit_service import audit_service
from backend.app.database.repositories import audit_repo

router = APIRouter(prefix="/acp", tags=["Agentic Commerce Protocol (Machine-to-Machine)"])

# In-memory quote cache for machine-to-machine transactions
_quotes_db: Dict[str, Dict[str, object]] = {}

@router.get("/catalog", response_model=ACPDiscoveryResponse)
def get_machine_catalog():
    """Machine-readable catalog endpoint for external AI Buyers (ACP / AP2 specification)."""
    summaries = []
    for p in read_tools.catalog:
        summaries.append(ACPProductSummary(
            sku=p.id,
            name=p.name,
            category=p.category,
            price_inr=p.price,
            stock_status="IN_STOCK" if p.inventory > 0 else "OUT_OF_STOCK",
            spec_summary=p.specs,
            direct_checkout_supported=True
        ))
    
    audit_service.record_event(
        actor_id="EXTERNAL_AI_BUYER",
        actor_role="EXTERNAL_AI_BUYER",
        action="ACP_DISCOVERY_FETCH",
        arguments={"total_skus": len(summaries)},
        result_status="SUCCESS",
        explainability_notes="External AI buyer queried machine-readable catalog schema via ACP protocol."
    )

    return ACPDiscoveryResponse(
        protocol_version="ACP/1.0",
        merchant_id=settings.MERCHANT_ID,
        merchant_name=settings.MERCHANT_NAME,
        currency="INR",
        catalog=summaries,
        spend_limit_inr=policy_engine.config.max_transaction_amount_inr,
        direct_order_supported=True,
        mcp_tools_url="/api/v1/acp/mcp-schema"
    )

@router.post("/quote", response_model=ACPQuoteResponse)
def get_quote(req: ACPQuoteRequest):
    """Machine-readable quote and dynamic bundle pricing calculator."""
    cart = Cart(user_id=req.agent_id)
    for i, sku in enumerate(req.skus):
        p = read_tools.get_product(sku)
        if not p:
            raise HTTPException(status_code=404, detail=f"SKU {sku} not found in catalog")
        qty = req.quantities[i] if i < len(req.quantities) else 1
        cart.items.append(CartItem(
            product_id=p.id,
            name=p.name,
            price=p.price,
            quantity=qty,
            subtotal=p.price * qty,
            category=p.category
        ))

    if req.include_upsell_bundles and len(req.skus) == 1:
        bundle = read_tools.calculate_upsell_bundle(req.skus[0])
        if bundle:
            comp = read_tools.get_product(bundle.complementary_product_id)
            if comp:
                cart.items.append(CartItem(
                    product_id=comp.id,
                    name=comp.name,
                    price=comp.price,
                    subtotal=comp.price,
                    category=comp.category
                ))
                cart.applied_bundle = bundle

    cart.recalculate()
    policy_res = policy_engine.evaluate(cart=cart, user_id=req.agent_id)

    quote_id = f"quote_{uuid.uuid4().hex[:10]}"
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=300)
    # Preserve the exact priced cart. Checkout may not substitute an arbitrary
    # catalog item when a quote is missing or expired.
    _quotes_db[quote_id] = {"cart": cart.model_copy(deep=True), "expires_at": expires_at}

    return ACPQuoteResponse(
        quote_id=quote_id,
        skus=[item.product_id for item in cart.items],
        subtotal=cart.subtotal,
        bundle_discount=cart.discount_amount,
        total_amount=cart.total_amount,
        currency="INR",
        guardrail_precheck="PASS" if policy_res.allowed else "DENIED",
        expires_in_seconds=300,
        expires_at=expires_at.isoformat()
    )

@router.post("/checkout", response_model=ACPCheckoutResponse)
def execute_acp_checkout(req: ACPCheckoutRequest):
    """Programmatic transaction endpoint for external AI buyers using quoted items."""
    quote = _quotes_db.get(req.quote_id)
    if not quote:
        raise HTTPException(status_code=404, detail="Unknown quote_id. Request a quote before checkout.")
    if quote["expires_at"] <= datetime.now(timezone.utc):
        del _quotes_db[req.quote_id]
        raise HTTPException(status_code=410, detail="Quote has expired. Request a new quote before checkout.")

    cart = deepcopy(quote["cart"])
    cart.user_id = req.buyer_agent_id

    order_res = money_tools.create_order_guarded(
        cart=cart,
        user_id=req.buyer_agent_id,
        idempotency_key=req.idempotency_key
    )

    latest_audit = audit_repo.get_latest()
    audit_event_id = latest_audit.event_id if latest_audit else "EVT_INITIAL"
    signature = latest_audit.signature if latest_audit else "SIG_GENESIS"

    if not order_res["success"]:
        return ACPCheckoutResponse(
            status="DENIED",
            amount=cart.total_amount,
            currency="INR",
            audit_event_id=audit_event_id,
            signature=signature,
            message=f"Order rejected by policy: {order_res['reason']}"
        )

    order = order_res["order"]
    order_id = order["order_id"] if isinstance(order, dict) else order.order_id
    amount = order["amount"] if isinstance(order, dict) else order.amount
    currency = order["currency"] if isinstance(order, dict) else order.currency

    return ACPCheckoutResponse(
        status="ORDER_CREATED",
        order_id=order_id,
        amount=amount,
        currency=currency,
        razorpay_payment_link=f"https://rzp.io/i/{order_id}",
        audit_event_id=audit_event_id,
        signature=signature,
        message="Machine-to-machine checkout successfully authorized and order created."
    )
@router.get("/mcp-schema")
def get_mcp_tool_definitions():
    """Model Context Protocol (MCP) tool schema for autonomous agent integration."""
    return {
        "mcp_version": "2024-11-05",
        "tools": [
            {
                "name": "search_merchant_catalog",
                "description": "Look up machine-readable products, prices, and stock in pay-pipeline merchant catalog.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string"},
                        "max_price_inr": {"type": "number"},
                        "query": {"type": "string"}
                    }
                }
            },
            {
                "name": "request_commerce_quote",
                "description": "Calculate subtotal, bundle discounts, and policy pre-check.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skus": {"type": "array", "items": {"type": "string"}},
                        "include_upsell_bundles": {"type": "boolean"}
                    },
                    "required": ["skus"]
                }
            },
            {
                "name": "execute_agentic_checkout",
                "description": "Execute capability-gated order creation on Razorpay test rails with idempotency protection.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "quote_id": {"type": "string"},
                        "idempotency_key": {"type": "string"}
                    },
                    "required": ["quote_id", "idempotency_key"]
                }
            }
        ]
    }
