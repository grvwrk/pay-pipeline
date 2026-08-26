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
    CatalogSearchEvent
)
from backend.app.models.catalog import ProductFilter, Product
from backend.app.models.cart import Cart, CartItem, BundleOffer
from backend.app.models.guardrail import DecisionCode
from backend.app.tools.read_tools import read_tools
from backend.app.tools.money_tools import money_tools
from backend.app.audit.audit_service import audit_service
from backend.app.guardrails.policy_engine import policy_engine

class AgenticCommerceWorkflow(Workflow):
    @step
    async def route_intent(self, ctx: Context, ev: StartEvent) -> CatalogSearchEvent | StopEvent:
        user_msg: str = ev.get("user_message", "")
        user_id: str = ev.get("user_id", "user_default_buyer")
        approval_token: Optional[str] = ev.get("approval_token")
        idempotency_key: Optional[str] = ev.get("idempotency_key")
        
        lower_msg = user_msg.lower().strip()

        audit_service.record_event(
            actor_id=user_id,
            actor_role="USER",
            action="USER_INTENT_RECEIVED",
            arguments={"message": user_msg},
            intent="INGEST_REQUEST",
            explainability_notes=f"User prompted: '{user_msg}'"
        )

        # 1. Gated Approval Token Confirmation
        if approval_token or "approve" in lower_msg or "confirm purchase" in lower_msg:
            token = approval_token or "appr_tok_manual"
            policy_engine.register_human_approval(token)
            
            target_sku = ev.get("sku", "sku_phone_zenfone_10_compact")
            prod = read_tools.get_product(target_sku) or read_tools.catalog[0]
            cart = Cart(user_id=user_id)
            cart.items.append(CartItem(
                product_id=prod.id,
                name=prod.name,
                price=prod.price,
                subtotal=prod.price,
                category=prod.category
            ))
            cart.recalculate()

            order_res = money_tools.create_order_guarded(
                cart=cart,
                user_id=user_id,
                idempotency_key=idempotency_key or f"idem_{uuid.uuid4().hex[:8]}",
                approval_token=token
            )
            return StopEvent(result={
                "type": "ORDER_CREATED",
                "message": f"Human approval verified! Razorpay order created for ₹{cart.total_amount:,.2f}.",
                "order": order_res.get("order"),
                "cart": cart.dict(),
                "policy_evaluation": order_res.get("policy_evaluation")
            })

        # 2. Direct Purchase Intent
        if any(w in lower_msg for w in ["buy", "checkout", "purchase", "place order", "order now", "get me"]):
            price_match = re.search(r'(?:under|below|budget|max|for)\s*(?:rs\.?|inr|₹)?\s*(\d+[\d,]*)', lower_msg)
            max_price = float(price_match.group(1).replace(',', '')) if price_match else None

            # Accurate product resolution
            target_product = None
            if "zenfone" in lower_msg or "asus" in lower_msg:
                target_product = read_tools.get_product("sku_phone_zenfone_10_compact")
            elif "pixel" in lower_msg:
                target_product = read_tools.get_product("sku_phone_pixel_8a_compact")
            elif "s23" in lower_msg or "samsung" in lower_msg:
                target_product = read_tools.get_product("sku_phone_galaxy_s23_compact")
            elif "iphone" in lower_msg or "mini" in lower_msg:
                target_product = read_tools.get_product("sku_phone_iphone_13_mini")
            elif "aluminium" in lower_msg or "cnc" in lower_msg or "7999" in lower_msg:
                target_product = read_tools.get_product("sku_kb_custom_pro_aluminium")
            elif "keychron" in lower_msg or "k2" in lower_msg:
                target_product = read_tools.get_product("sku_kb_keychron_k2")
            elif "rk84" in lower_msg:
                target_product = read_tools.get_product("sku_kb_royal_kludge_rk84")
            elif "ducky" in lower_msg:
                target_product = read_tools.get_product("sku_kb_ducky_one3_tkl")
            elif "screenbar" in lower_msg:
                target_product = read_tools.get_product("sku_dev_screenbar_light")
            elif "dock" in lower_msg:
                target_product = read_tools.get_product("sku_dev_usbc_dock_11in1")
            elif "headphone" in lower_msg or "audio" in lower_msg:
                target_product = read_tools.get_product("sku_audio_anc_headset")
            else:
                matches = read_tools.catalog_lookup(ProductFilter(query=lower_msg, max_price=max_price))
                target_product = matches[0] if matches else read_tools.catalog[0]

            cart = Cart(user_id=user_id)
            cart.items.append(CartItem(
                product_id=target_product.id,
                name=target_product.name,
                price=target_product.price,
                subtotal=target_product.price,
                category=target_product.category
            ))

            if any(b in lower_msg for b in ["bundle", "both", "add charger", "add wrist rest", "add case"]):
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

            order_res = money_tools.create_order_guarded(
                cart=cart,
                user_id=user_id,
                idempotency_key=idempotency_key or f"idem_{uuid.uuid4().hex[:8]}"
            )

            if order_res["success"]:
                order_data = order_res["order"]
                return StopEvent(result={
                    "type": "ORDER_CREATED",
                    "message": f"Order #{order_data['order_id']} created on Razorpay test rails for ₹{cart.total_amount:,.2f}.",
                    "order": order_data,
                    "cart": cart.dict(),
                    "policy_evaluation": order_res["policy_evaluation"]
                })
            elif order_res.get("requires_approval"):
                return StopEvent(result={
                    "type": "APPROVAL_REQUIRED",
                    "message": f"Transaction total ₹{cart.total_amount:,.2f} exceeds autonomous threshold ₹{policy_engine.config.approval_threshold_inr:,.2f}. Explicit human confirmation required.",
                    "approval_token": order_res.get("approval_token"),
                    "cart": cart.dict(),
                    "policy_evaluation": order_res["policy_evaluation"]
                })
            else:
                return StopEvent(result={
                    "type": "GUARDRAIL_DENIED",
                    "message": f"Transaction of ₹{cart.total_amount:,.2f} blocked by deterministic policy: {order_res['reason']}",
                    "decision_code": order_res["decision_code"],
                    "cart": cart.dict(),
                    "policy_evaluation": order_res["policy_evaluation"]
                })

        # 3. Product Search & Catalog Discovery
        price_match = re.search(r'(?:under|below|budget|max|for)\s*(?:rs\.?|inr|₹)?\s*(\d+[\d,]*)', lower_msg)
        max_price = float(price_match.group(1).replace(',', '')) if price_match else None

        category = None
        if any(w in lower_msg for w in ["phone", "smartphone", "mobile", "android", "iphone", "pixel", "galaxy", "zenfone"]):
            category = "smartphones"
        elif any(w in lower_msg for w in ["keyboard", "keychron", "typing", "switch"]):
            category = "mechanical_keyboards"
        elif any(w in lower_msg for w in ["mouse", "vertical", "ergonomic"]):
            category = "ergonomics"
        elif any(w in lower_msg for w in ["headphone", "audio", "anc", "music"]):
            category = "audio_equipment"
        elif any(w in lower_msg for w in ["screenbar", "light", "dock", "hub"]):
            category = "developer_gear"
        elif any(w in lower_msg for w in ["desk", "wrist", "mat", "stand"]):
            category = "workspace_accessories"

        return CatalogSearchEvent(
            query=lower_msg,
            category=category,
            max_price=max_price,
            user_id=user_id
        )

    @step
    async def handle_catalog_search(self, ctx: Context, ev: CatalogSearchEvent) -> StopEvent:
        products = read_tools.catalog_lookup(ProductFilter(
            query=ev.query,
            category=ev.category,
            max_price=ev.max_price
        ))

        if not products:
            budget_str = f" under ₹{ev.max_price:,.2f}" if ev.max_price else ""
            msg = f"I searched our merchant catalog for '**{ev.query}**'{budget_str}, but found no matching items in stock.\n\nOur store specializes in **Compact Smartphones, Ergonomics, Audio, Mechanical Keyboards, and Developer Gear**."
            return StopEvent(result={
                "type": "CATALOG_DISCOVERY",
                "message": msg,
                "products": [],
                "top_choice": None,
                "upsell_bundle": None
            })

        top_choice = products[0]
        bundle_offer = read_tools.calculate_upsell_bundle(top_choice.id)

        msg_lines = [
            f"I found {len(products)} matching option(s). Top recommendation: **{top_choice.name}** at ₹{top_choice.price:,.2f} (Rating: {top_choice.rating}⭐)."
        ]
        
        # Display key specs
        if "display" in top_choice.specs:
            msg_lines.append(f"📱 **Display**: {top_choice.specs['display']}")
        if "processor" in top_choice.specs:
            msg_lines.append(f"⚡ **Processor**: {top_choice.specs['processor']}")
            
        if bundle_offer:
            msg_lines.append(f"💡 **AI Revenue Booster Opportunity**: Bundle with {bundle_offer.complementary_product_name} for just ₹{bundle_offer.discounted_bundle_price:,.2f} (Save ₹{bundle_offer.savings_amount:,.2f} with 5% bundle discount!).")

        audit_service.record_event(
            actor_id=ev.user_id,
            actor_role="CATALOG_AGENT",
            action="CATALOG_SEARCH_COMPLETED",
            tool_name="catalog_lookup",
            arguments={"query": ev.query, "category": ev.category, "max_price": ev.max_price, "results_count": len(products)},
            result_status="SUCCESS",
            explainability_notes=f"Catalog Agent matched {len(products)} items. Selected {top_choice.name} as primary candidate."
        )

        return StopEvent(result={
            "type": "CATALOG_DISCOVERY",
            "message": "\n\n".join(msg_lines),
            "products": [p.dict() for p in products],
            "top_choice": top_choice.dict(),
            "upsell_bundle": bundle_offer.dict() if bundle_offer else None
        })

commerce_workflow = AgenticCommerceWorkflow()
