import pytest
from backend.app.payment.razorpay_client import razorpay_client
from backend.app.tools.money_tools import money_tools
from backend.app.models.cart import Cart, CartItem


def test_valid_and_excessive_refund():
    # 1. Setup order and payment of ₹1,899
    cart = Cart(user_id="user_refund_test")
    cart.items.append(CartItem(
        product_id="sku_mouse_ergo_vertical",
        name="Vertical Mouse",
        price=1899.0,
        subtotal=1899.0,
        category="ergonomics"
    ))
    cart.recalculate()

    order_res = money_tools.create_order_guarded(cart, user_id="user_refund_test")
    order_id = order_res["order"]["order_id"]
    pay_res = money_tools.capture_payment_guarded(order_id, 1899.0, user_id="user_refund_test")
    payment_id = pay_res["payment"]["payment_id"]

    # 2. Test Excessive Refund Denial (attempting ₹2,500 on ₹1,899 payment)
    excess_res = money_tools.issue_refund_guarded(
        payment_id=payment_id,
        amount_inr=2500.0,
        user_id="user_refund_test"
    )
    assert not excess_res["success"]
    assert excess_res["decision_code"] == "REFUND_EXCEEDS_ORIGINAL_AMOUNT"
    assert "exceeds remaining refundable balance" in excess_res["error"]

    # 3. Test Valid Partial Refund (₹500 on ₹1,899 payment)
    valid_res = money_tools.issue_refund_guarded(
        payment_id=payment_id,
        amount_inr=500.0,
        user_id="user_refund_test"
    )
    assert valid_res["success"]
    assert valid_res["refund"]["amount"] == 500.0
    assert valid_res["refund"]["status"] == "processed"

    # 4. Test Second Partial Refund (₹1,000 on remaining ₹1,399 balance)
    second_res = money_tools.issue_refund_guarded(
        payment_id=payment_id,
        amount_inr=1000.0,
        user_id="user_refund_test"
    )
    assert second_res["success"]

    # 5. Test Remaining Balance Limit (attempting ₹500 when only ₹399 remaining)
    over_res = money_tools.issue_refund_guarded(
        payment_id=payment_id,
        amount_inr=500.0,
        user_id="user_refund_test"
    )
    assert not over_res["success"]
    assert over_res["decision_code"] == "REFUND_EXCEEDS_ORIGINAL_AMOUNT"
