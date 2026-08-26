import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.db import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_products_endpoint():
    res = client.get("/api/v1/products")
    assert res.status_code == 200
    products = res.json()
    assert len(products) > 0

    single = client.get("/api/v1/products/sku_kb_keychron_k2")
    assert single.status_code == 200
    assert "Keychron K2" in single.json()["name"]


def test_cart_and_checkout_endpoints():
    # 1. Create cart
    cart_res = client.post("/api/v1/cart", json={
        "user_id": "test_api_buyer",
        "items": [{"product_id": "sku_mouse_ergo_vertical", "quantity": 1}]
    })
    assert cart_res.status_code == 200
    cart_data = cart_res.json()
    cart_id = cart_data["cart_id"]
    assert cart_data["total_amount"] == 1899.0

    # 2. Get cart
    get_res = client.get(f"/api/v1/cart/{cart_id}")
    assert get_res.status_code == 200
    assert get_res.json()["cart_id"] == cart_id

    # 3. Direct checkout endpoint
    checkout_res = client.post("/api/v1/checkout", json={
        "cart_id": cart_id,
        "user_id": "test_api_buyer"
    })
    assert checkout_res.status_code == 200
    chk_data = checkout_res.json()
    assert chk_data["success"]
    order_id = chk_data["order"]["order_id"]

    # 4. Get order endpoint
    order_res = client.get(f"/api/v1/orders/{order_id}")
    assert order_res.status_code == 200
    assert order_res.json()["order_id"] == order_id


def test_approve_endpoint():
    res = client.post("/api/v1/approve", json={"approval_token": "appr_test_token_12345"})
    assert res.status_code == 200
    assert res.json()["status"] == "APPROVED"


def test_audit_verify_endpoint():
    res = client.get("/api/v1/audit/verify")
    assert res.status_code == 200
    assert res.json()["is_valid"] is True
