import asyncio
import time
import uuid
import re
from typing import Any, Dict, Optional, Union
from llama_index.core.workflow import Context, StartEvent, StopEvent, Workflow, step

from backend.app.audit.audit_service import audit_service
from backend.app.guardrails.policy_engine import policy_engine
from backend.app.models.cart import Cart, CartItem
from backend.app.models.catalog import ProductFilter
from backend.app.tools.money_tools import money_tools
from backend.app.tools.read_tools import read_tools
from backend.app.llm.groq_agent import groq_catalog_agent
from backend.app.workflows.events import (
    ApprovalConfirmationEvent, CatalogResultEvent, CatalogSearchEvent,
    CheckoutCartEvent, CheckoutEvent, IntentClassifiedEvent,
    RefundRequestEvent, StatusQueryEvent
)


def _trace(agent: str, thought: str, action: str, latency_ms: float = 0.0, **extra: Any) -> Dict[str, Any]:
    return {
        "agent_name": agent,
        "thought": thought,
        "action": action,
        "latency_ms": round(latency_ms, 2),
        **extra
    }


class AgenticCommerceWorkflow(Workflow):
    """
    Event-driven LlamaIndex multi-agent commerce workflow.
    Coordinates Intent Router, Catalog Agent, Upsell Agent, Checkout Agent,
    Refund Agent, and Policy Agent through controlled tool interfaces.
    """

    @step
    async def intent_router(self, ctx: Context, ev: StartEvent) -> IntentClassifiedEvent:
        start_t = time.perf_counter()
        query = ev.get("user_message", "").strip()
        user_id = ev.get("user_id", "user_default_buyer")
        approval = ev.get("approval_token")
        sku = ev.get("sku")
        order_id = ev.get("order_id")
        payment_id = ev.get("payment_id")

        classified = await asyncio.to_thread(groq_catalog_agent.route_intent, query, user_id)
        latency = (time.perf_counter() - start_t) * 1000.0

        intent = "APPROVE" if approval else classified.intent

        if not order_id:
            ord_m = re.search(r'(order_[a-zA-Z0-9]+)', query)
            if ord_m:
                order_id = ord_m.group(1)
        if not payment_id:
            pay_m = re.search(r'(pay_[a-zA-Z0-9]+)', query)
            if pay_m:
                payment_id = pay_m.group(1)

        refund_amt = None
        if intent == "REFUND":
            amt_m = re.search(r'(?:rs\.?|inr|₹)\s*(\d[\d,.]*)', query, re.IGNORECASE)
            if amt_m:
                try:
                    refund_amt = float(amt_m.group(1).replace(",", ""))
                except Exception:
                    refund_amt = None

        audit_service.record_event(
            actor_id=user_id,
            actor_role="INTENT_ROUTER",
            action="INTENT_CLASSIFIED",
            intent=intent,
            arguments={"query": query, "intent": intent, "entities": classified.entities},
            guardrail_decision="APPROVED",
            result_status="SUCCESS",
            latency_ms=latency,
            explainability_notes=f"Classified prompt intent as '{intent}' with confidence {classified.confidence:.2f} via {classified.provider}."
        )

        return IntentClassifiedEvent(
            intent=intent,
            user_query=query,
            user_id=user_id,
            target_sku=sku or classified.sku,
            target_category=classified.category,
            max_price=classified.max_price,
            include_bundle=classified.include_bundle,
            approval_token=approval,
            idempotency_key=ev.get("idempotency_key") or f"idem_{uuid.uuid4().hex[:12]}",
            force_fail_payment=ev.get("force_fail_payment", False),
            order_id=order_id,
            payment_id=payment_id,
            refund_amount=refund_amt
        )

    @step
    async def route_intent(
        self,
        ctx: Context,
        ev: IntentClassifiedEvent
    ) -> Union[CatalogSearchEvent, CheckoutEvent, ApprovalConfirmationEvent, RefundRequestEvent, StatusQueryEvent, StopEvent]:
        if ev.intent in {"PRODUCT_SEARCH", "PRODUCT_DETAILS", "PRODUCT_RECOMMENDATION", "GENERAL_COMMERCE_QUERY", "DISCOVERY"}:
            return CatalogSearchEvent(
                query=ev.user_query,
                category=ev.target_category,
                max_price=ev.max_price,
                user_id=ev.user_id,
                intent=ev.intent
            )
        elif ev.intent == "APPROVE":
            return ApprovalConfirmationEvent(
                user_id=ev.user_id,
                approval_token=ev.approval_token or "",
                target_sku=ev.target_sku,
                idempotency_key=ev.idempotency_key,
                include_bundle=ev.include_bundle,
                force_fail_payment=ev.force_fail_payment,
                max_price=ev.max_price,
                user_query=ev.user_query
            )
        elif ev.intent == "REFUND":
            # BUG FIX: Prevent fallthrough to CheckoutEvent if payment_id is missing
            if ev.payment_id:
                return RefundRequestEvent(
                    payment_id=ev.payment_id,
                    refund_amount=ev.refund_amount,
                    user_id=ev.user_id,
                    reason=f"User requested refund via chat: {ev.user_query}"
                )
            else:
                return StopEvent(result={
                    "type": "REFUND_REQUIRES_INFO",
                    "message": "⚠️ **Missing Information**: Please specify your Payment ID (e.g., `pay_12345678`) to initiate a refund.",
                    "reasoning_steps": [_trace("Refund Agent", "Refund requested without a valid Payment ID.", "PROMPT_PAYMENT_ID")]
                })
        elif ev.intent in {"ORDER_STATUS", "PAYMENT_STATUS"}:
            return StatusQueryEvent(
                query_type="ORDER" if ev.intent == "ORDER_STATUS" else "PAYMENT",
                entity_id=ev.order_id or ev.payment_id or "unknown",
                user_id=ev.user_id
            )
        elif ev.intent in {"CHECKOUT", "CART_ADD", "BUY"}:
            return CheckoutEvent(
                user_id=ev.user_id,
                target_sku=ev.target_sku,
                query=ev.user_query,
                max_price=ev.max_price,
                include_bundle=ev.include_bundle,
                approval_token=ev.approval_token,
                idempotency_key=ev.idempotency_key,
                force_fail_payment=ev.force_fail_payment
            )
        else:
            # Fallback for unrecognized intent to prevent unexpected charges
            return StopEvent(result={
                "type": "UNKNOWN_INTENT",
                "message": "I could not determine your request. Please ask a product question or specify a purchase.",
                "reasoning_steps": [_trace("Intent Router", f"Unhandled intent '{ev.intent}' gracefully stopped.", "HALT")]
            })

    @step
    async def approval_agent(self, ctx: Context, ev: ApprovalConfirmationEvent) -> CheckoutEvent:
        await asyncio.to_thread(policy_engine.register_human_approval, ev.approval_token)
        # BUG FIX: Forward preserved bundle and testing flags into CheckoutEvent
        return CheckoutEvent(
            user_id=ev.user_id,
            target_sku=ev.target_sku,
            query=ev.user_query or "approved checkout",
            approval_token=ev.approval_token,
            idempotency_key=ev.idempotency_key,
            include_bundle=ev.include_bundle,
            force_fail_payment=ev.force_fail_payment,
            max_price=ev.max_price
        )

    @step
    async def catalog_agent(self, ctx: Context, ev: CatalogSearchEvent) -> CatalogResultEvent:
        start_t = time.perf_counter()
        agent_result = await asyncio.to_thread(groq_catalog_agent.run, ev.query or "", ev.category, ev.max_price)
        latency = (time.perf_counter() - start_t) * 1000.0

        products = agent_result.products
        top = products[0] if products else None

        audit_service.record_event(
            actor_id=ev.user_id,
            actor_role="CATALOG_AGENT",
            action="CATALOG_SEARCH_COMPLETED",
            tool_name="search_products",
            arguments={"query": ev.query, "category": ev.category, "max_price": ev.max_price, "results_count": len(products)},
            guardrail_decision="APPROVED",
            result_status="SUCCESS",
            latency_ms=latency,
            explainability_notes=f"Catalog Agent retrieved {len(products)} matching candidate(s) via {agent_result.provider}."
        )

        return CatalogResultEvent(
            products=products,
            top_choice=top,
            upsell_bundle=None,
            user_query=ev.query or "",
            user_id=ev.user_id,
            agent_summary=agent_result.summary,
            tool_calls=agent_result.tool_calls,
            provider=agent_result.provider
        )

    @step
    async def upsell_agent(self, ctx: Context, ev: CatalogResultEvent) -> StopEvent:
        trace = [_trace("Catalog Agent", f"Read-only catalog search returned {len(ev.products)} candidate(s) via {ev.provider}.", "SEARCH_CATALOG", tool_called="search_catalog", arguments={"tool_calls": ev.tool_calls})]

        if not ev.top_choice:
            return StopEvent(result={
                "type": "CATALOG_DISCOVERY",
                "message": "No in-stock catalog items match your request.",
                "products": [],
                "top_choice": None,
                "upsell_bundle": None,
                "reasoning_steps": trace
            })

        bundle = await asyncio.to_thread(read_tools.calculate_upsell_bundle, ev.top_choice.id)
        if bundle:
            trace.append(_trace("Upsell Agent", f"Identified high-affinity companion accessory for {ev.top_choice.name}.", "RECOMMEND_BUNDLE", tool_called="calculate_upsell_bundle", result_summary=f"Bundle discount saves ₹{bundle.savings_amount:,.2f}."))

        specs = "\n".join(f"• {k.replace('_', ' ').title()}: {v}" for k, v in list(ev.top_choice.specs.items())[:3])
        message = f"I found {len(ev.products)} matching option(s). Top recommendation: **{ev.top_choice.name}** at ₹{ev.top_choice.price:,.2f} (Rating: {ev.top_choice.rating}★)."
        if specs:
            message += f"\n\n{specs}"
        if ev.agent_summary:
            message += f"\n\n{ev.agent_summary}"
        if bundle:
            message += f"\n\nSuggested bundle: **{bundle.complementary_product_name}**; total ₹{bundle.discounted_bundle_price:,.2f}, saving ₹{bundle.savings_amount:,.2f}."

        return StopEvent(result={
            "type": "CATALOG_DISCOVERY",
            "message": message,
            "products": [p.model_dump() for p in ev.products],
            "top_choice": ev.top_choice.model_dump(),
            "upsell_bundle": bundle.model_dump() if bundle else None,
            "reasoning_steps": trace
        })

    @step
    async def checkout_agent(self, ctx: Context, ev: CheckoutEvent) -> Union[CheckoutCartEvent, StopEvent]:
        product = await asyncio.to_thread(read_tools.get_product, ev.target_sku) if ev.target_sku else None
        if not product:
            candidates = await asyncio.to_thread(read_tools.catalog_lookup, ProductFilter(query=ev.query, max_price=ev.max_price))
            product = candidates[0] if candidates else None

        if not product:
            return StopEvent(result={
                "type": "CHECKOUT_UNAVAILABLE",
                "message": "No matching in-stock product could be resolved for checkout.",
                "reasoning_steps": [_trace("Checkout Agent", "No catalog item resolved for checkout.", "STOP")]
            })

        cart = await asyncio.to_thread(
            read_tools.build_cart,
            user_id=ev.user_id,
            items=[{"product_id": product.id, "quantity": 1, "include_bundle": ev.include_bundle}]
        )

        return CheckoutCartEvent(
            cart=cart,
            user_id=ev.user_id,
            approval_token=ev.approval_token,
            idempotency_key=ev.idempotency_key,
            force_fail_payment=ev.force_fail_payment,
            reasoning_steps=[_trace("Checkout Agent", f"Constructed server-side cart for {len(cart.items)} item(s), total ₹{cart.total_amount:,.2f}.", "BUILD_CART", tool_called="build_cart")]
        )

    @step
    async def policy_agent(self, ctx: Context, ev: CheckoutCartEvent) -> StopEvent:
        start_t = time.perf_counter()
        result = await asyncio.to_thread(
            money_tools.create_order_guarded,
            cart=ev.cart,
            user_id=ev.user_id,
            idempotency_key=ev.idempotency_key,
            approval_token=ev.approval_token
        )
        latency = (time.perf_counter() - start_t) * 1000.0

        trace = ev.reasoning_steps
        if result.get("success"):
            trace.append(_trace("Guardrail & Policy Agent", "Deterministic policy approved order creation.", "APPROVE", latency_ms=latency, tool_called="create_order"))
            return StopEvent(result={
                "type": "ORDER_CREATED",
                "message": f"Order {result['order']['order_id']} created for ₹{ev.cart.total_amount:,.2f}. Awaiting payment initiation.",
                "order": result["order"],
                "cart": ev.cart.model_dump(),
                "policy_evaluation": result["policy_evaluation"],
                "reasoning_steps": trace
            })

        if result.get("requires_approval"):
            trace.append(_trace("Guardrail & Policy Agent", result["reason"], "GATED_APPROVAL_REQUIRED", latency_ms=latency))
            return StopEvent(result={
                "type": "APPROVAL_REQUIRED",
                "message": result["reason"],
                "approval_token": result.get("approval_token"),
                "cart": ev.cart.model_dump(),
                "policy_evaluation": result["policy_evaluation"],
                "reasoning_steps": trace
            })

        decision_code = result.get("decision_code")
        code_val = decision_code.value if hasattr(decision_code, "value") else str(decision_code)

        trace.append(_trace("Guardrail & Policy Agent", result.get("reason", "Policy violation"), "DENY", latency_ms=latency))
        return StopEvent(result={
            "type": "GUARDRAIL_DENIED",
            "message": f"Transaction blocked by policy: {result.get('reason', 'Policy check failed')}",
            "decision_code": code_val,
            "cart": ev.cart.model_dump(),
            "policy_evaluation": result.get("policy_evaluation"),
            "reasoning_steps": trace
        })

    @step
    async def refund_agent(self, ctx: Context, ev: RefundRequestEvent) -> StopEvent:
        amt = ev.refund_amount or 0.0
        reason = getattr(ev, "reason", "Customer requested refund")
        res = await asyncio.to_thread(
            money_tools.issue_refund_guarded,
            payment_id=ev.payment_id,
            amount_inr=amt,
            user_id=ev.user_id,
            reason=reason
        )
        if res.get("success"):
            return StopEvent(result={
                "type": "REFUND_PROCESSED",
                "message": f"Refund of ₹{amt:,.2f} processed for payment {ev.payment_id}.",
                "refund": res.get("refund")
            })
        else:
            return StopEvent(result={
                "type": "REFUND_DENIED",
                "message": f"Refund blocked: {res.get('error')}",
                "decision_code": res.get("decision_code")
            })

    @step
    async def status_agent(self, ctx: Context, ev: StatusQueryEvent) -> StopEvent:
        if ev.query_type == "ORDER":
            order = await asyncio.to_thread(read_tools.get_order_status, ev.entity_id)
            if order:
                amt = order.get('amount') or 0.0
                return StopEvent(result={
                    "type": "ORDER_STATUS",
                    "message": f"Order {ev.entity_id} status: {order.get('status')} (State: {order.get('state')}) for ₹{amt:,.2f}.",
                    "order": order
                })
        else:
            payment = await asyncio.to_thread(read_tools.get_payment_status, ev.entity_id)
            if payment:
                amt = payment.get('amount') or 0.0
                return StopEvent(result={
                    "type": "PAYMENT_STATUS",
                    "message": f"Payment {ev.entity_id} status: {payment.get('status')} for ₹{amt:,.2f}.",
                    "payment": payment
                })

        return StopEvent(result={
            "type": "STATUS_NOT_FOUND",
            "message": f"{ev.query_type} record '{ev.entity_id}' not found."
        })


commerce_workflow = AgenticCommerceWorkflow()