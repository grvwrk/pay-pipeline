import pytest
from backend.app.database.db import init_db
from backend.app.database.repositories import (
    product_repo, cart_repo, order_repo, payment_repo,
    refund_repo, approval_repo, audit_repo, spend_repo, idempotency_repo
)
from backend.app.models.cart import Cart, CartItem
from backend.app.models.order import RazorpayOrder, PaymentCaptureResult, RefundResult, TransactionState


def test_database_initialization_and_products():
    init_db()
    products = product_repo.get_all()
    assert len(products) >= 20
    kb = product_repo.get_by_id("sku_kb_keychron_k2")
    assert kb is not None
    assert kb.price == 4499.0
    assert kb.inventory > 0


def test_inventory_atomic_decrement():
    p_id = "sku_acc_wrist_rest_walnut"
    initial_inv = product_repo.get_by_id(p_id).inventory
    assert initial_inv > 0

    success = product_repo.decrement_inventory(p_id, 2)
    assert success
    assert product_repo.get_by_id(p_id).inventory == initial_inv - 2

    # Restore inventory
    product_repo.increment_inventory(p_id, 2)
    assert product_repo.get_by_id(p_id).inventory == initial_inv


def test_cart_persistence():
    cart = Cart(cart_id="test_cart_persisted_01", user_id="user_db_test")
    cart.items.append(CartItem(
        product_id="sku_mouse_ergo_vertical",
        name="Vertical Mouse",
        price=1899.0,
        quantity=2,
        subtotal=3798.0,
        category="ergonomics"
    ))
    cart_repo.save_cart(cart)

    retrieved = cart_repo.get_cart("test_cart_persisted_01")
    assert retrieved is not None
    assert retrieved.user_id == "user_db_test"
    assert len(retrieved.items) == 1
    assert retrieved.items[0].quantity == 2
    assert retrieved.total_amount == 3798.0


def test_order_and_payment_persistence():
    order = RazorpayOrder(
        order_id="order_db_test_123",
        cart_id="cart_db_test_123",
        amount=2500.0,
        amount_in_paise=250000,
        currency="INR",
        status="created",
        receipt="rcpt_db_123",
        state=TransactionState.ORDER_CREATED,
        notes={"user_id": "user_db_test"}
    )
    order_repo.create_order(order)

    fetched_order = order_repo.get_order("order_db_test_123")
    assert fetched_order is not None
    assert fetched_order.amount == 2500.0
    assert fetched_order.state == TransactionState.ORDER_CREATED

    payment = PaymentCaptureResult(
        payment_id="pay_db_test_123",
        order_id="order_db_test_123",
        amount=2500.0,
        currency="INR",
        status="captured",
        method="upi"
    )
    payment_repo.record_payment(payment, user_id="user_db_test")

    fetched_pay = payment_repo.get_payment("pay_db_test_123")
    assert fetched_pay is not None
    assert fetched_pay.status == "captured"
