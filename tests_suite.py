import os

def write(filepath, content):
    d = os.path.dirname(filepath)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Wrote: {filepath}")

write('tests/__init__.py', '')

write('tests/test_guardrails.py', '''import pytest
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
''')

write('tests/test_audit_chain.py', '''import pytest
from backend.app.audit.audit_service import AuditService

def test_cryptographic_hash_chain_integrity():
    audit = AuditService()
    
    # Record multiple events
    audit.record_event(
        actor_id="user_1",
        actor_role="USER",
        action="CATALOG_SEARCH",
        arguments={"query": "keyboard"},
        guardrail_decision="APPROVED"
    )
    audit.record_event(
        actor_id="user_1",
        actor_role="CHECKOUT_AGENT",
        action="CREATE_ORDER",
        arguments={"amount": 4499.0, "order_id": "order_123"},
        guardrail_decision="APPROVED"
    )

    # Verify untampered chain
    verification = audit.verify_chain_integrity()
    assert verification.is_valid
    assert verification.total_records == 3 # Genesis + 2 records
    assert verification.tampered_index is None

def test_cryptographic_tamper_detection():
    audit = AuditService()
    
    audit.record_event(
        actor_id="user_1",
        actor_role="CHECKOUT_AGENT",
        action="CREATE_ORDER",
        arguments={"amount": 4499.0, "order_id": "order_123"},
        guardrail_decision="APPROVED"
    )

    # Tamper with the log entry
    audit.tamper_simulation(target_index=1, fake_amount=100.0)

    # Verify detection
    verification = audit.verify_chain_integrity()
    assert not verification.is_valid
    assert verification.tampered_index == 1
    assert "mismatch" in verification.error_detail.lower() or "alteration" in verification.error_detail.lower()
''')

write('tests/test_acp.py', '''import pytest
from backend.app.tools.read_tools import read_tools
from backend.app.tools.money_tools import money_tools
from backend.app.models.cart import Cart, CartItem

def test_acp_machine_catalog_readability():
    catalog = read_tools.catalog
    assert len(catalog) >= 5
    for item in catalog:
        assert item.id.startswith("sku_")
        assert item.price > 0
        assert item.currency == "INR"
        assert len(item.specs) > 0

def test_dynamic_upsell_calculation():
    bundle = read_tools.calculate_upsell_bundle("sku_kb_keychron_k2")
    assert bundle is not None
    assert bundle.complementary_product_id == "sku_acc_wrist_rest_walnut"
    assert bundle.discount_percentage == 5.0
    assert bundle.savings_amount > 0
    assert bundle.discounted_bundle_price < bundle.original_combined_price
''')

print("Test suite written successfully!")
