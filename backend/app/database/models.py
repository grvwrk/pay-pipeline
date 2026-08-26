from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class ProductModel(Base):
    __tablename__ = "products"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    price = Column(Float, nullable=False)
    inventory = Column(Integer, default=0)
    rating = Column(Float, default=4.5)
    specs_json = Column(Text, default="{}")
    tags_json = Column(Text, default="[]")
    complementary_ids_json = Column(Text, default="[]")
    description = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    @property
    def specs(self) -> Dict[str, Any]:
        try:
            return json.loads(self.specs_json or "{}")
        except Exception:
            return {}

    @property
    def tags(self) -> List[str]:
        try:
            return json.loads(self.tags_json or "[]")
        except Exception:
            return []

    @property
    def complementary_product_ids(self) -> List[str]:
        try:
            return json.loads(self.complementary_ids_json or "[]")
        except Exception:
            return []


class CartItemModel(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cart_id = Column(String(64), ForeignKey("carts.cart_id"), nullable=False, index=True)
    product_id = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, default=1)
    subtotal = Column(Float, nullable=False)
    category = Column(String(100), default="general")

    cart = relationship("CartModel", back_populates="items")


class CartModel(Base):
    __tablename__ = "carts"

    cart_id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    currency = Column(String(10), default="INR")
    subtotal_amount = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    status = Column(String(32), default="ACTIVE")
    applied_bundle_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    items = relationship("CartItemModel", back_populates="cart", cascade="all, delete-orphan")


class OrderModel(Base):
    __tablename__ = "orders"

    order_id = Column(String(64), primary_key=True, index=True)
    cart_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), default="user_default_buyer", index=True)
    amount = Column(Float, nullable=False)
    amount_in_paise = Column(Integer, nullable=False)
    currency = Column(String(10), default="INR")
    status = Column(String(32), default="created")
    receipt = Column(String(64), nullable=True)
    state = Column(String(64), default="ORDER_CREATED")
    notes_json = Column(Text, default="{}")
    idempotency_key = Column(String(128), nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    @property
    def notes(self) -> Dict[str, str]:
        try:
            return json.loads(self.notes_json or "{}")
        except Exception:
            return {}


class PaymentModel(Base):
    __tablename__ = "payments"

    payment_id = Column(String(64), primary_key=True, index=True)
    order_id = Column(String(64), ForeignKey("orders.order_id"), nullable=False, index=True)
    user_id = Column(String(64), default="user_default_buyer", index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR")
    method = Column(String(32), default="upi")
    status = Column(String(32), default="pending")  # captured, failed, pending
    error_code = Column(String(64), nullable=True)
    error_description = Column(Text, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class RefundModel(Base):
    __tablename__ = "refunds"

    refund_id = Column(String(64), primary_key=True, index=True)
    payment_id = Column(String(64), ForeignKey("payments.payment_id"), nullable=False, index=True)
    order_id = Column(String(64), nullable=True)
    user_id = Column(String(64), default="user_default_buyer")
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR")
    reason = Column(Text, default="Customer requested refund")
    status = Column(String(32), default="processed")  # processed, failed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ApprovalModel(Base):
    __tablename__ = "approvals"

    token = Column(String(128), primary_key=True, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    cart_id = Column(String(64), nullable=True)
    reason = Column(Text, nullable=True)
    status = Column(String(32), default="PENDING")  # PENDING, APPROVED, REJECTED, EXPIRED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    approved_at = Column(DateTime, nullable=True)


class AuditRecordModel(Base):
    __tablename__ = "audit_records"

    index = Column(Integer, primary_key=True)
    event_id = Column(String(64), unique=True, index=True)
    timestamp = Column(String(64), nullable=False)
    prev_hash = Column(String(128), nullable=False)
    record_hash = Column(String(128), nullable=False, index=True)
    actor_id = Column(String(64), default="SYSTEM")
    actor_role = Column(String(64), default="SYSTEM")
    action = Column(String(64), nullable=False)
    intent = Column(String(64), nullable=True)
    tool_name = Column(String(64), nullable=True)
    arguments_json = Column(Text, default="{}")
    guardrail_decision = Column(String(64), nullable=True)
    approval_required = Column(Boolean, default=False)
    transaction_state = Column(String(64), nullable=True)
    result_status = Column(String(32), default="SUCCESS")
    signature = Column(String(256), nullable=False)
    latency_ms = Column(Float, default=0.0)
    explainability_notes = Column(Text, default="")


class UserSpendModel(Base):
    __tablename__ = "user_spends"

    user_id = Column(String(64), primary_key=True, index=True)
    cumulative_spend_inr = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class IdempotencyModel(Base):
    __tablename__ = "idempotency_keys"

    key = Column(String(128), primary_key=True, index=True)
    response_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
