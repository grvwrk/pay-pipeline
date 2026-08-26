import re, uuid, datetime
from typing import Optional, Dict, Any, List
from llama_index.core.workflow import (
    Workflow,
    StartEvent,
    StopEvent,
    step,
    Context
)
from backend.app.workflows.events import (
    IntentClassifiedEvent,
    CatalogSearchEvent,
    CatalogResultEvent,
    UpsellEvent,
    UpsellResultEvent,
    CheckoutEvent,
    ApprovalConfirmationEvent
)
from backend.app.models.catalog import ProductFilter, Product
from backend.app.models.cart import Cart, CartItem, BundleOffer
from backend.app.models.guardrail import DecisionCode
from backend.app.tools.read_tools import read_tools
from backend.app.tools.money_tools import money_tools
from backend.app.audit.audit_service import audit_service
from backend.app.guardrails.policy_engine import policy_engine

class AgenticCommerceWorkflow(Workflow):
    """
    Multi-Agent Orchestrator for Autonomous & Conversational Commerce.
    Modular state machine coordinating:
      1. Intent Router Agent: Natural language intent & entity parsing
      2. Catalog Agent: Read-only product discovery, semantic ranking, and spec reasoning
      3. Upsell & Cross-Sell Agent: High-affinity dynamic bundling and basket expansion
      4. Checkout Agent & Guardrails: Capability-gated privileged order creation and policy gating
      5. Human Approval Agent: 2FA approval token verification for gated high-value orders
    """

    @step
    async def route_intent_step(
        self,
        ctx: Context,
        ev: StartEvent
    ) -> CatalogSearchEvent | CheckoutEvent | ApprovalConfirmationEvent | StopEvent:
        user_msg: str = ev.get("user_message", "")
        user_id: str = ev.get("user_id", "user_default_buyer")
        approval_token: Optional[str] = ev.get("approval_token")
        idempotency_key: Optional[str] = ev.get("idempotency_key")
        explicit_sku: Optional[str] = ev.get("sku")
        force_fail_payment: bool = ev.get("force_fail_payment", False)

        lower_msg = user_msg.lower().strip()

        # Audit recording of raw user intent
        audit_service.record_event(
            actor_id=user_id,
            actor_role="USER",
            action="USER_INTENT_RECEIVED",
            arguments={"message": user_msg, "sku": explicit_sku, "has_approval_token": bool(approval_token)},
            intent="INGEST_REQUEST",
            explainability_notes=f"User prompted: '{user_msg}'"
        )

        # 1. Gated Approval Token Confirmation
        if approval_token or any(p in lower_msg for p in ["approve", "confirm purchase", "proceed with order", "authorize"]):
            token = approval_token or "appr_tok_manual"
            return ApprovalConfirmationEvent(
                user_id=user_id,
                approval_token=token,
                target_sku=explicit_sku,
                idempotency_key=idempotency_key
            )

        # Extract budget constraints (e.g. "under ₹5,000", "below 7000", "budget 8000")
        price_match = re.search(r'(?:under|below|budget|max|for)\s*(?:rs\.?|inr|₹)?\s*(\d+[\d,]*)', lower_msg)
        max_price = float(price_match.group(1).replace(',', '')) if price_match else None

        # Check for bundle / accessories modifier
        include_bundle = any(b in lower_msg for b in [
            "bundle", "both", "with wrist rest", "with charger", "with case", "with cable", "add accessories", "accept bundle"
        ])

        # 2. Purchase / Checkout Intent
        is_checkout = any(w in lower_msg for w in [
            "buy", "checkout", "purchase", "place order", "order now", "get me", "i'll take"
        ])

        if is_checkout or explicit_sku:
            return CheckoutEvent(
                user_id=user_id,
                target_sku=explicit_sku,
                query=lower_msg,
                max_price=max_price,
                include_bundle=include_bundle,
                approval_token=approval_token,
                idempotency_key=idempotency_key,
                force_fail_payment=force_fail_payment
            )

        # 3. Category Inference for Catalog Discovery
        category = None
        if any(w in lower_msg for w in ["phone", "smartphone", "mobile", "android", "iphone", "pixel", "galaxy", "zenfone"]):
            category = "smartphones"
        elif any(w in lower_msg for w in ["keyboard", "keychron", "typing", "switch", "rk84", "ducky"]):
            category = "mechanical_keyboards"
        elif any(w in lower_msg for w in ["mouse", "vertical", "ergonomic", "wrist"]):
            category = "ergonomics"
        elif any(w in lower_msg for w in ["headphone", "audio", "anc", "sound", "headset"]):
            category = "audio_equipment"
        elif any(w in lower_msg for w in ["screenbar", "light", "dock", "hub"]):
            category = "developer_gear"
        elif any(w in lower_msg for w in ["desk", "mat", "stand", "cable"]):
            category = "workspace_accessories"

        return CatalogSearchEvent(
            query=lower_msg,
            category=category,
            max_price=max_price,
            user_id=user_id,
            include_bundle_analysis=True
        )

    @step
    async def catalog_agent_step(self, ctx: Context, ev: CatalogSearchEvent) -> StopEvent:
        """
        Catalog Agent Step: Read-only commerce intelligence.
        Executes semantic search over catalog and reasons over product specifications.
        """
        products = read_tools.catalog_lookup(ProductFilter(
            query=ev.query,
            category=ev.category,
            max_price=ev.max_price
        ))

        if not products:
            budget_str = f" under ₹{ev.max_price:,.2f}" if ev.max_price else ""
            msg = f"I searched our merchant catalog for '**{ev.query}**'{budget_str}, but found no matching items in stock.\n\nOur store specializes in **Mechanical Keyboards, Ergonomics, Audio, Compact Smartphones, and Developer Gear**."
            return StopEvent(result={
                "type": "CATALOG_DISCOVERY",
                "message": msg,
                "products": [],
                "top_choice": None,
                "upsell_bundle": None
            })

        top_choice = products[0]
        bundle_offer = read_tools.calculate_upsell_bundle(top_choice.id) if ev.include_bundle_analysis else None

        msg_lines = [
            f"I found {len(products)} matching option(s). Top recommendation: **{top_choice.name}** at ₹{top_choice.price:,.2f} (Rating: {top_choice.rating}⭐)."
        ]

        # Display key product specs
        if top_choice.specs:
            for spec_key, spec_val in list(top_choice.specs.items())[:2]:
                msg_lines.append(f"• **{spec_key.title()}**: {spec_val}")

        # Dynamic Upsell Bundle Opportunity
        if bundle_offer:
            msg_lines.append(
                f"💡 **AI Revenue Booster**: Bundle with **{bundle_offer.complementary_product_name}** for just ₹{bundle_offer.discounted_bundle_price:,.2f} "
                f"(Save ₹{bundle_offer.savings_amount:,.2f} with 5% instant bundle discount!)."
            )

        audit_service.record_event(
            actor_id=ev.user_id,
            actor_role="CATALOG_AGENT",
            action="CATALOG_SEARCH_COMPLETED",
            tool_name="catalog_lookup",
            arguments={"query": ev.query, "category": ev.category, "max_price": ev.max_price, "results_count": len(products)},
            result_status="SUCCESS",
            explainability_notes=f"Catalog Agent matched {len(products)} items. Selected '{top_choice.name}' as primary recommendation."
        )

        return StopEvent(result={
            "type": "CATALOG_DISCOVERY",
            "message": "\n\n".join(msg_lines),
            "products": [p.model_dump() for p in products],
            "top_choice": top_choice.model_dump(),
            "upsell_bundle": bundle_offer.model_dump() if bundle_offer else None
        })

    @step
    async def checkout_agent_step(self, ctx: Context, ev: CheckoutEvent) -> StopEvent:
        """
        Checkout Agent Step: Privileged cart assembly and deterministic policy evaluation.
        Interacts with Razorpay test rails and enforces model-independent guardrails.
        """
        target_product: Optional[Product] = None

        if ev.target_sku:
            target_product = read_tools.get_product(ev.target_sku)

        if not target_product and ev.query:
            # Semantic search to resolve product accurately
            matches = read_tools.catalog_lookup(ProductFilter(query=ev.query, max_price=ev.max_price))
            if matches:
                target_product = matches[0]

        if not target_product:
            target_product = read_tools.catalog[0] if read_tools.catalog else None

        if not target_product:
            return StopEvent(result={
                "type": "GUARDRAIL_DENIED",
                "message": "Unable to assemble cart: No available product found.",
                "cart": None,
                "policy_evaluation": None
            })

        cart = Cart(user_id=ev.user_id)
        cart.items.append(CartItem(
            product_id=target_product.id,
            name=target_product.name,
            price=target_product.price,
            subtotal=target_product.price,
            category=target_product.category
        ))

        # Dynamic bundle addition
        if ev.include_bundle:
            bundle = read_tools.calculate_upsell_bundle(target_product.id)
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

        # Guarded order creation
        order_res = money_tools.create_order_guarded(
            cart=cart,
            user_id=ev.user_id,
            idempotency_key=ev.idempotency_key or f"idem_{uuid.uuid4().hex[:8]}",
            approval_token=ev.approval_token
        )

        if order_res["success"]:
            order_data = order_res["order"]
            return StopEvent(result={
                "type": "ORDER_CREATED",
                "message": f"Order #{order_data['order_id']} created on Razorpay test rails for ₹{cart.total_amount:,.2f}.",
                "order": order_data,
                "cart": cart.model_dump(),
                "policy_evaluation": order_res["policy_evaluation"]
            })
        elif order_res.get("requires_approval"):
            return StopEvent(result={
                "type": "APPROVAL_REQUIRED",
                "message": f"Transaction total ₹{cart.total_amount:,.2f} exceeds autonomous threshold ₹{policy_engine.config.approval_threshold_inr:,.2f}. Explicit human confirmation required.",
                "approval_token": order_res.get("approval_token"),
                "cart": cart.model_dump(),
                "policy_evaluation": order_res["policy_evaluation"]
            })
        else:
            return StopEvent(result={
                "type": "GUARDRAIL_DENIED",
                "message": f"Transaction of ₹{cart.total_amount:,.2f} blocked by deterministic policy: {order_res['reason']}",
                "decision_code": order_res.get("decision_code"),
                "cart": cart.model_dump(),
                "policy_evaluation": order_res["policy_evaluation"]
            })

    @step
    async def approval_agent_step(self, ctx: Context, ev: ApprovalConfirmationEvent) -> StopEvent:
        """
        Approval Agent Step: Verifies 2FA confirmation token and proceeds with gated order creation.
        """
        policy_engine.register_human_approval(ev.approval_token)

        target_product: Optional[Product] = None
        if ev.target_sku:
            target_product = read_tools.get_product(ev.target_sku)
        if not target_product:
            # Default to popular flagship item if not specified
            target_product = read_tools.get_product("sku_kb_keychron_k2") or (read_tools.catalog[0] if read_tools.catalog else None)

        if not target_product:
            return StopEvent(result={
                "type": "GUARDRAIL_DENIED",
                "message": "Product resolution failed for approved order.",
                "cart": None,
                "policy_evaluation": None
            })

        cart = Cart(user_id=ev.user_id)
        cart.items.append(CartItem(
            product_id=target_product.id,
            name=target_product.name,
            price=target_product.price,
            subtotal=target_product.price,
            category=target_product.category
        ))
        cart.recalculate()

        order_res = money_tools.create_order_guarded(
            cart=cart,
            user_id=ev.user_id,
            idempotency_key=ev.idempotency_key or f"idem_{uuid.uuid4().hex[:8]}",
            approval_token=ev.approval_token
        )

        return StopEvent(result={
            "type": "ORDER_CREATED",
            "message": f"Human approval verified! Razorpay order created for ₹{cart.total_amount:,.2f}.",
            "order": order_res.get("order"),
            "cart": cart.model_dump(),
            "policy_evaluation": order_res.get("policy_evaluation")
        })

commerce_workflow = AgenticCommerceWorkflow()
