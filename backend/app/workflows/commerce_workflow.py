"""Event-driven, least-privilege agent orchestration for agentic commerce."""

import re
import uuid
from typing import Any, Dict, Optional, Union

from llama_index.core.workflow import Context, StartEvent, StopEvent, Workflow, step

from backend.app.audit.audit_service import audit_service
from backend.app.guardrails.policy_engine import policy_engine
from backend.app.models.cart import Cart, CartItem
from backend.app.models.catalog import ProductFilter
from backend.app.tools.money_tools import money_tools
from backend.app.tools.read_tools import read_tools
from backend.app.workflows.events import (
    ApprovalConfirmationEvent, CatalogResultEvent, CatalogSearchEvent,
    CheckoutCartEvent, CheckoutEvent, IntentClassifiedEvent,
)


def _trace(agent: str, thought: str, action: str, **extra: Any) -> Dict[str, Any]:
    """Explain actions and tool choices without exposing chain-of-thought."""
    return {"agent_name": agent, "thought": thought, "action": action, **extra}


def _category(query: str) -> Optional[str]:
    categories = {
        "nutrition_and_fitness": ("peanut", "protein", "nutrition", "chia", "shaker", "gym", "diet", "whey", "snack", "supplement"),
        "running_shoes": ("running", "shoes", "shoe", "sneaker", "pegasus", "marathon", "socks"),
        "mechanical_keyboards": ("keyboard", "keychron", "typing", "switch", "rk84", "ducky"),
        "ergonomics": ("mouse", "mice", "vertical", "ergonomic", "wrist"),
        "audio_equipment": ("headphone", "headset", "audio", "anc", "sound"),
        "smartphones": ("phone", "smartphone", "mobile", "android", "iphone", "pixel", "galaxy"),
        "developer_gear": ("screenbar", "dock", "hub", "usbc"),
        "workspace_accessories": ("desk", "deskmat", "stand", "cable", "mat"),
    }
    return next((name for name, words in categories.items() if any(word in query for word in words)), None)


def _budget(query: str) -> Optional[float]:
    found = re.search(r"(?:under|below|budget|max|for)\s*(?:rs\.?|inr|₹)?\s*(\d[\d,]*)", query)
    if not found:
        found = re.search(r"(\d[\d,]*)\s*(?:rs|inr|rupees|₹)", query)
    return float(found.group(1).replace(",", "")) if found else None


class AgenticCommerceWorkflow(Workflow):
    """Typed LlamaIndex multi-agent workflow with scoped tool permissions."""

    @step
    async def intent_router(self, ctx: Context, ev: StartEvent) -> IntentClassifiedEvent:
        query = ev.get("user_message", "").strip()
        lower = query.lower()
        approval = ev.get("approval_token")
        sku = ev.get("sku")
        checkout_words = ("buy", "checkout", "purchase", "place order", "order now", "get me", "i'll take")
        intent = "APPROVE" if approval else ("CHECKOUT" if sku or any(word in lower for word in checkout_words) else "DISCOVERY")
        return IntentClassifiedEvent(intent=intent, user_query=query, user_id=ev.get("user_id", "user_default_buyer"),
            target_sku=sku, target_category=_category(lower), max_price=_budget(lower),
            include_bundle=any(word in lower for word in ("bundle", "both", "wrist rest", "charger", "case", "cable", "accessories")),
            approval_token=approval, idempotency_key=ev.get("idempotency_key") or f"idem_{uuid.uuid4().hex[:12]}",
            force_fail_payment=ev.get("force_fail_payment", False))

    @step
    async def route_intent(self, ctx: Context, ev: IntentClassifiedEvent) -> Union[CatalogSearchEvent, CheckoutEvent, ApprovalConfirmationEvent]:
        if ev.intent == "DISCOVERY":
            return CatalogSearchEvent(query=ev.user_query, category=ev.target_category, max_price=ev.max_price, user_id=ev.user_id)
        if ev.intent == "APPROVE":
            return ApprovalConfirmationEvent(user_id=ev.user_id, approval_token=ev.approval_token or "", target_sku=ev.target_sku, idempotency_key=ev.idempotency_key)
        return CheckoutEvent(user_id=ev.user_id, target_sku=ev.target_sku, query=ev.user_query, max_price=ev.max_price,
            include_bundle=ev.include_bundle, approval_token=ev.approval_token, idempotency_key=ev.idempotency_key)

    @step
    async def approval_agent(self, ctx: Context, ev: ApprovalConfirmationEvent) -> CheckoutEvent:
        policy_engine.register_human_approval(ev.approval_token)
        return CheckoutEvent(user_id=ev.user_id, target_sku=ev.target_sku, query="approved checkout", approval_token=ev.approval_token, idempotency_key=ev.idempotency_key)

    @step
    async def catalog_agent(self, ctx: Context, ev: CatalogSearchEvent) -> CatalogResultEvent:
        products = read_tools.catalog_lookup(ProductFilter(query=ev.query, category=ev.category, max_price=ev.max_price))
        top = products[0] if products else None
        audit_service.record_event(actor_id=ev.user_id, actor_role="CATALOG_AGENT", action="CATALOG_SEARCH_COMPLETED", tool_name="catalog_lookup",
            arguments={"query": ev.query, "category": ev.category, "max_price": ev.max_price, "results_count": len(products)}, result_status="SUCCESS",
            explainability_notes="Catalog Agent executed a read-only catalog query.")
        return CatalogResultEvent(products=products, top_choice=top, upsell_bundle=None, user_query=ev.query or "", user_id=ev.user_id)

    @step
    async def upsell_agent(self, ctx: Context, ev: CatalogResultEvent) -> StopEvent:
        trace = [_trace("Catalog Agent", f"Read-only catalog search returned {len(ev.products)} candidate(s).", "SEARCH_CATALOG", tool_called="catalog_lookup")]
        if not ev.top_choice:
            return StopEvent(result={"type": "CATALOG_DISCOVERY", "message": "No in-stock catalog items match this request.", "products": [], "top_choice": None, "upsell_bundle": None, "reasoning_steps": trace})
        bundle = read_tools.calculate_upsell_bundle(ev.top_choice.id)
        if bundle:
            trace.append(_trace("Upsell Agent", f"Affinity rules found a complementary product for {ev.top_choice.name}.", "RECOMMEND_BUNDLE", tool_called="calculate_upsell_bundle", result_summary=f"Bundle saves ₹{bundle.savings_amount:,.2f}."))
        specs = "\n".join(f"• {key.replace('_', ' ').title()}: {value}" for key, value in list(ev.top_choice.specs.items())[:3])
        message = f"I found {len(ev.products)} matching option(s). Top recommendation: **{ev.top_choice.name}** at ₹{ev.top_choice.price:,.2f} (Rating: {ev.top_choice.rating}★)."
        if specs:
            message += f"\n\n{specs}"
        if bundle:
            message += f"\n\nSuggested bundle: **{bundle.complementary_product_name}**; total ₹{bundle.discounted_bundle_price:,.2f}, saving ₹{bundle.savings_amount:,.2f}."
        return StopEvent(result={"type": "CATALOG_DISCOVERY", "message": message, "products": [product.model_dump() for product in ev.products],
            "top_choice": ev.top_choice.model_dump(), "upsell_bundle": bundle.model_dump() if bundle else None, "reasoning_steps": trace})

    @step
    async def checkout_agent(self, ctx: Context, ev: CheckoutEvent) -> Union[CheckoutCartEvent, StopEvent]:
        product = read_tools.get_product(ev.target_sku) if ev.target_sku else None
        if not product:
            candidates = read_tools.catalog_lookup(ProductFilter(query=ev.query, max_price=ev.max_price))
            product = candidates[0] if candidates else None
        if not product:
            return StopEvent(result={"type": "CHECKOUT_UNAVAILABLE", "message": "No matching in-stock product can be checked out.", "reasoning_steps": [_trace("Checkout Agent", "No catalog item resolved for checkout.", "STOP")]})
        cart = Cart(user_id=ev.user_id)
        cart.items.append(CartItem(product_id=product.id, name=product.name, price=product.price, quantity=1, subtotal=product.price, category=product.category))
        if ev.include_bundle:
            bundle = read_tools.calculate_upsell_bundle(product.id)
            companion = read_tools.get_product(bundle.complementary_product_id) if bundle else None
            if bundle and companion:
                cart.items.append(CartItem(product_id=companion.id, name=companion.name, price=companion.price, quantity=1, subtotal=companion.price, category=companion.category))
                cart.applied_bundle = bundle
        cart.recalculate()
        return CheckoutCartEvent(cart=cart, user_id=ev.user_id, approval_token=ev.approval_token, idempotency_key=ev.idempotency_key,
            reasoning_steps=[_trace("Checkout Agent", f"Built cart for {len(cart.items)} item(s), total ₹{cart.total_amount:,.2f}.", "BUILD_CART", tool_called="cart_builder")])

    @step
    async def policy_agent(self, ctx: Context, ev: CheckoutCartEvent) -> StopEvent:
        # The only step permitted to call privileged money tools.
        result = money_tools.create_order_guarded(cart=ev.cart, user_id=ev.user_id, idempotency_key=ev.idempotency_key, approval_token=ev.approval_token)
        trace = ev.reasoning_steps
        if result["success"]:
            trace.append(_trace("Guardrail & Policy Agent", "Deterministic policy approved order creation.", "APPROVE", tool_called="create_order"))
            return StopEvent(result={"type": "ORDER_CREATED", "message": f"Order {result['order']['order_id']} created for ₹{ev.cart.total_amount:,.2f}. Await payment and webhook verification.", "order": result["order"], "cart": ev.cart.model_dump(), "policy_evaluation": result["policy_evaluation"], "reasoning_steps": trace})
        if result.get("requires_approval"):
            trace.append(_trace("Guardrail & Policy Agent", result["reason"], "GATED_APPROVAL_REQUIRED"))
            return StopEvent(result={"type": "APPROVAL_REQUIRED", "message": result["reason"], "approval_token": result.get("approval_token"), "cart": ev.cart.model_dump(), "policy_evaluation": result["policy_evaluation"], "reasoning_steps": trace})
        trace.append(_trace("Guardrail & Policy Agent", result["reason"], "DENY"))
        return StopEvent(result={"type": "GUARDRAIL_DENIED", "message": f"Transaction blocked: {result['reason']}", "decision_code": result["decision_code"].value, "cart": ev.cart.model_dump(), "policy_evaluation": result["policy_evaluation"], "reasoning_steps": trace})


commerce_workflow = AgenticCommerceWorkflow()
