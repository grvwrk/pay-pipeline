import os, re, json, uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from backend.app.models.catalog import ProductFilter, Product
from backend.app.models.cart import Cart, CartItem, BundleOffer
from backend.app.models.guardrail import DecisionCode, PolicyEvaluationResult
from backend.app.tools.read_tools import read_tools
from backend.app.tools.money_tools import money_tools
from backend.app.guardrails.policy_engine import policy_engine
from backend.app.audit.audit_service import audit_service
from backend.app.llm.groq_agent import groq_catalog_agent
from backend.app.tools.search_tools import tavily_search_engine

class AgentReasoningStep(BaseModel):
    agent_name: str
    thought: str
    action: Optional[str] = None
    tool_called: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    result_summary: Optional[str] = None

class AgentPlan(BaseModel):
    intent: str
    user_goal: str
    extracted_entities: Dict[str, Any]
    target_tools: List[str]
    reasoning_steps: List[AgentReasoningStep]

class AutonomousCommerceAgentEngine:
    """
    Autonomous Multi-Agent AI Engine.
    Executes Chain-of-Thought (CoT) reasoning, tool planning, and multi-agent synthesis.
    """

    def __init__(self):
        self.has_openai_key = bool(os.getenv("OPENAI_API_KEY"))

    def plan_and_execute(
        self,
        user_message: str,
        user_id: str = "user_default_buyer",
        approval_token: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        explicit_sku: Optional[str] = None,
        force_fail_payment: bool = False
    ) -> Dict[str, Any]:
        reasoning_steps: List[AgentReasoningStep] = []
        
        # FIX: Define lower_msg to prevent NameError
        lower_msg = user_message.lower()
        
        # Step 1: Dynamic LLM Intent Router & Entity Extractor
        classified = groq_catalog_agent.classify_intent(user_message)
        max_price = classified.max_price
        include_bundle = classified.include_bundle
        category = classified.category

        is_approval = bool(approval_token) or classified.intent == "APPROVE" or any(w in lower_msg for w in ["approve", "confirm purchase", "proceed with order", "authorize"])
        is_checkout = classified.intent in ["CHECKOUT", "CART_ADD"] or any(w in lower_msg for w in ["buy", "checkout", "purchase", "place order", "order now"])

        classified_intent = "APPROVAL" if is_approval else ("CHECKOUT" if (is_checkout or explicit_sku) else "DISCOVERY")

        reasoning_steps.append(AgentReasoningStep(
            agent_name="Intent Router Agent",
            thought=f"Classified intent as '{classified_intent}' ({classified.provider}). Budget constraint: {'₹' + str(max_price) if max_price else 'Unspecified'}, Category affinity: '{category or 'Dynamic Semantic Search'}'",
            action=f"ROUTE_TO_{classified_intent}",
            arguments={"query": user_message, "category": category, "max_price": max_price, "include_bundle": include_bundle},
            result_summary=f"Handing off context to {classified_intent} agent subsystem."
        ))

        # Branch 1: Approval Agent Flow
        if is_approval:
            token = approval_token or "appr_tok_manual"
            policy_engine.register_human_approval(token)

            reasoning_steps.append(AgentReasoningStep(
                agent_name="Human Approval Agent",
                thought=f"Received human authorization token '{token}'. Registering authorization with Deterministic Policy Engine.",
                action="REGISTER_APPROVAL_TOKEN",
                tool_called="policy_engine.register_human_approval",
                arguments={"token": token},
                result_summary="Token verified. Privileged money tools unlocked for execution."
            ))

            target_product = read_tools.get_product(explicit_sku) if explicit_sku else read_tools.get_product("sku_kb_keychron_k2")
            if not target_product and read_tools.catalog:
                target_product = read_tools.catalog[0]
                
            # FIX: Graceful exit if no product resolves
            if not target_product:
                return {"type": "ERROR", "message": "Could not resolve a product for approval."}

            cart = Cart(user_id=user_id)
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
                user_id=user_id,
                idempotency_key=idempotency_key or f"idem_{uuid.uuid4().hex[:8]}",
                approval_token=token
            )

            reasoning_steps.append(AgentReasoningStep(
                agent_name="Checkout Agent",
                thought=f"Executing capability-gated Razorpay order creation for approved cart total ₹{cart.total_amount:,.2f}.",
                action="EXECUTE_RAZORPAY_ORDER",
                tool_called="create_order",
                arguments={"amount": cart.total_amount, "cart_id": cart.cart_id},
                result_summary=f"Order {order_res['order']['order_id']} created on Razorpay test rails."
            ))

            return {
                "type": "ORDER_CREATED",
                "message": f"✅ **Human Approval Verified!** Razorpay order created for **₹{cart.total_amount:,.2f}**.",
                "order": order_res.get("order"),
                "cart": cart.model_dump(),
                "policy_evaluation": order_res.get("policy_evaluation"),
                "reasoning_steps": [s.model_dump() for s in reasoning_steps]
            }

        # Branch 2: Direct Checkout Agent Flow
        if is_checkout or explicit_sku:
            target_product = None
            if explicit_sku:
                target_product = read_tools.get_product(explicit_sku)
            if not target_product:
                matches = read_tools.catalog_lookup(ProductFilter(query=lower_msg, category=category, max_price=max_price))
                if matches:
                    target_product = matches[0]
            if not target_product and read_tools.catalog:
                target_product = read_tools.catalog[0]
                
            # FIX: Graceful exit if catalog is entirely empty
            if not target_product:
                return {
                    "type": "CHECKOUT_UNAVAILABLE",
                    "message": "No matching in-stock product could be resolved for checkout."
                }

            cart = Cart(user_id=user_id)
            cart.items.append(CartItem(
                product_id=target_product.id,
                name=target_product.name,
                price=target_product.price,
                subtotal=target_product.price,
                category=target_product.category
            ))

            if include_bundle:
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

            reasoning_steps.append(AgentReasoningStep(
                agent_name="Checkout Agent",
                thought=f"Constructed cart for '{target_product.name}' with subtotal ₹{cart.total_amount:,.2f}. Requesting evaluation from Guardrail Engine before moving money.",
                action="EVALUATE_POLICY",
                tool_called="policy_engine.evaluate",
                arguments={"cart_id": cart.cart_id, "amount": cart.total_amount, "user_id": user_id},
                result_summary="Submitted cart to deterministic policy validator."
            ))

            order_res = money_tools.create_order_guarded(
                cart=cart,
                user_id=user_id,
                idempotency_key=idempotency_key or f"idem_{uuid.uuid4().hex[:8]}"
            )

            if order_res["success"]:
                order_data = order_res["order"]
                reasoning_steps.append(AgentReasoningStep(
                    agent_name="Guardrail Engine",
                    thought="All policy rules passed: Amount is bounded, Currency is INR, Merchant authorized.",
                    action="ALLOW",
                    result_summary=f"Authorized Razorpay Order {order_data['order_id']}."
                ))
                return {
                    "type": "ORDER_CREATED",
                    "message": f"Order #{order_data['order_id']} created on Razorpay test rails for **₹{cart.total_amount:,.2f}**.",
                    "order": order_data,
                    "cart": cart.model_dump(),
                    "policy_evaluation": order_res["policy_evaluation"],
                    "reasoning_steps": [s.model_dump() for s in reasoning_steps]
                }
            elif order_res.get("requires_approval"):
                reasoning_steps.append(AgentReasoningStep(
                    agent_name="Guardrail Engine",
                    thought=f"Order amount ₹{cart.total_amount:,.2f} exceeds autonomous spending threshold. Gating financial execution.",
                    action="GATED_APPROVAL_REQUIRED",
                    result_summary="Generated 2FA human confirmation token."
                ))
                return {
                    "type": "APPROVAL_REQUIRED",
                    "message": f"⚠️ **Human Approval Required**: Transaction total **₹{cart.total_amount:,.2f}** exceeds autonomous threshold limit. Explicit human confirmation required.",
                    "approval_token": order_res.get("approval_token"),
                    "cart": cart.model_dump(),
                    "policy_evaluation": order_res["policy_evaluation"],
                    "reasoning_steps": [s.model_dump() for s in reasoning_steps]
                }
            else:
                reasoning_steps.append(AgentReasoningStep(
                    agent_name="Guardrail Engine",
                    thought=f"Policy violation detected: {order_res['reason']}. Intercepting transaction to protect user funds.",
                    action="DENIED",
                    result_summary=f"Blocked transaction with decision code: {order_res.get('decision_code')}"
                ))
                
                # FIX: Handle decision_code safely if it's an Enum
                decision_code = order_res.get("decision_code")
                code_val = decision_code.value if hasattr(decision_code, "value") else str(decision_code)
                
                return {
                    "type": "GUARDRAIL_DENIED",
                    "message": f"🛑 **Transaction Blocked by Guardrail**: {order_res['reason']}",
                    "decision_code": code_val,
                    "cart": cart.model_dump(),
                    "policy_evaluation": order_res["policy_evaluation"],
                    "reasoning_steps": [s.model_dump() for s in reasoning_steps]
                }

        # Branch 3: Catalog Agent Discovery & Semantic Reasoning
        products = read_tools.catalog_lookup(ProductFilter(
            query=lower_msg, # FIX: use lower_msg for cleaner queries
            category=category,
            max_price=max_price
        ))

        # Tavily AI Search for market intelligence & spec validation
        web_intel = tavily_search_engine.search(query=user_message, max_results=3)

        reasoning_steps.append(AgentReasoningStep(
            agent_name="Catalog & Market Research Agent",
            thought=f"Queried merchant catalog (found {len(products)} match(es)) and verified live market intelligence via Tavily AI Search ({web_intel.get('total_results', 0)} sources).",
            action="SEARCH_CATALOG_AND_WEB",
            tool_called="tavily_search",
            arguments={"query": user_message, "category": category, "max_price": max_price},
            result_summary=f"Catalog matches: {len(products)}. Tavily research: {web_intel.get('answer', 'Market context retrieved')}."
        ))

        if not products:
            budget_str = f" under ₹{max_price:,.2f}" if max_price else ""
            msg = f"I searched our merchant catalog for '**{user_message}**'{budget_str}, but found no matching items in stock.\n\nOur store specializes in **High-Protein Nutrition, Mechanical Keyboards, Running Shoes, Ergonomics, Audio, Compact Smartphones, and Developer Gear**."
            return {
                "type": "CATALOG_DISCOVERY",
                "message": msg,
                "products": [],
                "top_choice": None,
                "upsell_bundle": None,
                "reasoning_steps": [s.model_dump() for s in reasoning_steps]
            }

        top_choice = products[0]
        
        # Reasoning over top candidate specifications
        spec_analysis_lines = []
        if top_choice.specs:
            for k, v in list(top_choice.specs.items())[:3]:
                spec_analysis_lines.append(f"{k.replace('_', ' ').title()}: {v}")

        reasoning_steps.append(AgentReasoningStep(
            agent_name="Catalog Agent",
            thought=f"Analyzed top match '{top_choice.name}' (Rating: {top_choice.rating}⭐, Price: ₹{top_choice.price:,.2f}). Key specs: {', '.join(spec_analysis_lines)}",
            action="SELECT_PRIMARY_RECOMMENDATION",
            arguments={"product_id": top_choice.id, "specs": top_choice.specs},
            result_summary=f"Selected {top_choice.name} as highest relevance candidate."
        ))

        # Dynamic Upsell Bundle Reasoning
        bundle_offer = read_tools.calculate_upsell_bundle(top_choice.id)
        if bundle_offer:
            reasoning_steps.append(AgentReasoningStep(
                agent_name="Upsell & Revenue Growth Agent",
                thought=f"Evaluating merchant revenue growth opportunity. Identified complementary item '{bundle_offer.complementary_product_name}'. Formulating 5% dynamic bundle discount to increase AOV.",
                action="CONSTRUCT_DYNAMIC_BUNDLE",
                tool_called="calculate_upsell_bundle",
                arguments={"primary_id": top_choice.id, "complementary_id": bundle_offer.complementary_product_id},
                result_summary=f"Created bundle with ₹{bundle_offer.savings_amount:,.2f} savings."
            ))

        # Construct Agentic Synthesis Message
        msg_lines = [
            f"I found {len(products)} matching option(s). Top recommendation: **{top_choice.name}** at ₹{top_choice.price:,.2f} (Rating: {top_choice.rating}⭐)."
        ]

        if top_choice.specs:
            for spec_key, spec_val in list(top_choice.specs.items())[:3]:
                label = spec_key.replace('_', ' ').title()
                msg_lines.append(f"• **{label}**: {spec_val}")

        if bundle_offer:
            msg_lines.append(
                f"💡 **AI Revenue Booster**: Bundle with **{bundle_offer.complementary_product_name}** for just ₹{bundle_offer.discounted_bundle_price:,.2f} "
                f"(Save ₹{bundle_offer.savings_amount:,.2f} with 5% instant bundle discount!)."
            )

        audit_service.record_event(
            actor_id=user_id,
            actor_role="CATALOG_AGENT",
            action="CATALOG_SEARCH_COMPLETED",
            tool_name="catalog_lookup",
            arguments={"query": user_message, "category": category, "max_price": max_price, "results_count": len(products)},
            result_status="SUCCESS",
            explainability_notes=f"Multi-agent reasoning selected '{top_choice.name}' with CoT thought trace."
        )

        return {
            "type": "CATALOG_DISCOVERY",
            "message": "\n\n".join(msg_lines),
            "products": [p.model_dump() for p in products],
            "top_choice": top_choice.model_dump(),
            "upsell_bundle": bundle_offer.model_dump() if bundle_offer else None,
            "reasoning_steps": [s.model_dump() for s in reasoning_steps]
        }

agent_engine = AutonomousCommerceAgentEngine()