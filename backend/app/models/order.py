from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Dict, Any
from enum import Enum
import datetime


class TransactionState(str, Enum):
    DISCOVERED = "DISCOVERED"
    SELECTED = "SELECTED"
    CART_CREATED = "CART_CREATED"
    GUARDRAIL_EVALUATED = "GUARDRAIL_EVALUATED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ORDER_CREATED = "ORDER_CREATED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAYMENT_CAPTURED = "PAYMENT_CAPTURED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    COMPLETED = "COMPLETED"
    REFUNDED = "REFUNDED"
    DENIED = "DENIED"


class RazorpayOrder(BaseModel):
    order_id: str
    cart_id: str
    amount: float  # in INR
    amount_in_paise: Optional[int] = None
    currency: str = "INR"
    status: str = "created"
    receipt: str
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    notes: Dict[str, str] = Field(default_factory=dict)
    state: TransactionState = TransactionState.ORDER_CREATED
    idempotency_key: Optional[str] = None

    @model_validator(mode="after")
    def compute_paise(self) -> "RazorpayOrder":
        if self.amount_in_paise is None:
            self.amount_in_paise = int(round(self.amount * 100))
        return self


class PaymentCaptureResult(BaseModel):
    payment_id: str
    order_id: str
    amount: float
    currency: str = "INR"
    status: str  # "captured" or "failed"
    method: str = "upi"
    captured_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    razorpay_signature: Optional[str] = None
    webhook_verified: bool = False
    error_code: Optional[str] = None
    error_description: Optional[str] = None


class RefundResult(BaseModel):
    refund_id: str
    payment_id: str
    order_id: Optional[str] = None
    amount: float
    currency: str = "INR"
    status: str = "processed"
    reason: str = "Customer requested refund"
    processed_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())