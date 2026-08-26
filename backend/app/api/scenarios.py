import uuid
from fastapi import APIRouter
from backend.app.workflows.commerce_workflow import commerce_workflow
from backend.app.tools.money_tools import money_tools
from backend.app.tools.read_tools import read_tools
from backend.app.models.cart import Cart, CartItem
from backend.app.audit.audit_service import audit_service

router = APIRouter(prefix="/scenarios", tags=["Guided Demo Scenarios"])

@router.post("/run/{scenario_id}")
async def run_scenario(scenario_id: str):
    """Executes preset end-to-end evaluation scenarios for live demo judges."""
    
    if scenario_id == "discovery_and_reasoning":
        # Scenario 1: Natural language product search with budget constraints
        res = await commerce_workflow.run(
            user_message="Find me a good mechanical keyboard under ₹5000",
            user_id="judge_evaluator_01"
        )
        return {
            "scenario": "Discovery & Reasoning",
            "title": "Natural Language Search under ₹5,000",
            "description": "Catalog Agent analyzes intent, matches 75% mechanical keyboards, and reasons over specs.",
            "workflow_result": res
        }

    elif scenario_id == "upsell_basket_growth":
        # Scenario 2: Dynamic Upsell & Basket Expansion (Merchant Revenue Growth)
        kb = read_tools.get_product("sku_kb_keychron_k2") or read_tools.catalog[0]
        bundle = read_tools.calculate_upsell_bundle(kb.id)
        cart = Cart(user_id="judge_evaluator_01")
        cart.items.append(CartItem(
            product_id=kb.id,
            name=kb.name,
            price=kb.price,
            subtotal=kb.price,
            category=kb.category
        ))
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

        order_res = money_tools.create_order_guarded(cart, user_id="judge_evaluator_01")
        return {
            "scenario": "Revenue Growth & Dynamic Upsell",
            "title": "AOV Expansion: Keyboard + Solid Walnut Rest Bundle",
            "description": "Upsell Agent pairs Keychron K2 with Solid Walnut Wrist Rest (₹499) + 5% discount -> Cart ₹4,998 (< ₹5,000 limit).",
            "cart": cart.model_dump(),
            "order": order_res.get("order"),
            "policy_evaluation": order_res.get("policy_evaluation")
        }

    elif scenario_id == "graceful_failure_spend_limit":
        # Scenario 3: Bounded Deterministic Guardrail Interception (₹7,999 keyboard with ₹5,000 limit)
        res = await commerce_workflow.run(
            user_message="Buy me the AeroPro CNC Anodized Aluminium Gasket Keyboard for ₹7999",
            user_id="judge_evaluator_01"
        )
        return {
            "scenario": "Graceful Failure: Spend Limit Interception",
            "title": "Deterministic Denial of ₹7,999 Order against ₹5,000 Limit",
            "description": "Guardrail Engine intercepts and blocks privileged money tool execution. Model cannot override.",
            "workflow_result": res
        }

    elif scenario_id == "gated_approval_flow":
        # Scenario 4: Gated Human Approval Flow (> ₹3,000 threshold)
        res = await commerce_workflow.run(
            user_message="Buy Keychron K2 mechanical keyboard for ₹4499",
            user_id="judge_evaluator_01"
        )
        return {
            "scenario": "Gated Human-in-the-Loop Approval",
            "title": "Gating Orders > ₹3,000 with Approval Token",
            "description": "Order transitions to PENDING_APPROVAL requiring explicit human confirmation before money moves.",
            "workflow_result": res
        }

    elif scenario_id == "graceful_failure_payment_decline":
        # Scenario 5: Graceful Payment Failure & Webhook Handling
        cart = Cart(user_id="judge_evaluator_01")
        p = read_tools.get_product("sku_mouse_ergo_vertical") or read_tools.catalog[0]
        cart.items.append(CartItem(
            product_id=p.id,
            name=p.name,
            price=p.price,
            subtotal=p.price,
            category=p.category
        ))
        cart.recalculate()
        order_res = money_tools.create_order_guarded(cart, user_id="judge_evaluator_01")
        order_id = order_res["order"]["order_id"]

        # Simulate Payment Gateway Failure
        pay_res = money_tools.capture_payment_guarded(
            order_id=order_id,
            amount_inr=cart.total_amount,
            user_id="judge_evaluator_01",
            force_fail=True
        )

        return {
            "scenario": "Graceful Failure: Payment Gateway Decline",
            "title": "Authoritative Bank Decline & State Recovery",
            "description": "Bank declined payment. State machine transitions to PAYMENT_FAILED without hallucinatory success.",
            "order": order_res["order"],
            "payment_failure": pay_res
        }

    elif scenario_id == "acp_machine_buyer_transaction":
        # Scenario 6: External AI Buyer transacting via Agentic Commerce Protocol
        cart = Cart(user_id="external_agent_claude_3")
        p = read_tools.get_product("sku_dev_screenbar_light") or read_tools.catalog[0]
        cart.items.append(CartItem(product_id=p.id, name=p.name, price=p.price, subtotal=p.price, category=p.category))
        cart.recalculate()

        order_res = money_tools.create_order_guarded(cart, user_id="external_agent_claude_3", idempotency_key=f"acp_idem_{uuid.uuid4().hex[:8]}")
        return {
            "scenario": "Agentic Commerce Protocol (ACP)",
            "title": "Machine-to-Machine Autonomous Purchase",
            "description": "External AI Buyer directly discovered, quoted, and checked out ScreenBar LED over ACP endpoints.",
            "order": order_res.get("order"),
            "audit_proof": audit_service.chain[-1].model_dump()
        }

    return {"error": f"Unknown scenario {scenario_id}"}
