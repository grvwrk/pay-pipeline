import pytest
from backend.app.models.cart import Cart, CartItem
from backend.app.models.guardrail import DecisionCode, GuardrailConfig
from backend.app.guardrails.policy_engine import DeterministicPolicyEngine

def test_guardrail_spend_limit_denial():
    engine = DeterministicPolicyEngine()
    cart = Cart()
    # Adding item exceeding default ₹5,000 spend limit
    cart.items.append(CartItem(
        product_id="sku_kb_custom_pro_aluminium",
        name="CNC Keyboard",
        price=7999.0,
        subtotal=7999.0
    ))
    cart.recalculate()
    
    res = engine.evaluate(cart)
    assert not res.allowed
    assert res.decision_code == DecisionCode.DENIED_SPEND_LIMIT
    assert "exceeds" in res.reason

def test_guardrail_approval_gating():
    engine = DeterministicPolicyEngine()
    cart = Cart()
    # ₹4,499 item (between approval threshold ₹3,000 and max limit ₹5,000)
    cart.items.append(CartItem(
        product_id="sku_kb_keychron_k2",
        name="Keychron K2",
        price=4499.0,
        subtotal=4499.0
    ))
    cart.recalculate()

    # Without approval token -> Gated
    res1 = engine.evaluate(cart)
    assert not res1.allowed
    assert res1.requires_human_approval
    assert res1.decision_code == DecisionCode.GATED_APPROVAL_REQUIRED
    assert res1.approval_token is not None

    # With valid approval token -> Passes
    engine.register_human_approval(res1.approval_token)
    res2 = engine.evaluate(cart, provided_approval_token=res1.approval_token)
    assert res2.allowed
    assert res2.decision_code == DecisionCode.APPROVED

def test_guardrail_currency_check():
    engine = DeterministicPolicyEngine()
    cart = Cart(currency="USD")
    cart.items.append(CartItem(
        product_id="sku_kb_keychron_k2",
        name="Keychron K2",
        price=100.0,
        subtotal=100.0
    ))
    cart.recalculate()

    res = engine.evaluate(cart)
    assert not res.allowed
    assert res.decision_code == DecisionCode.DENIED_CURRENCY_MISMATCH
