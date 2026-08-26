import hmac, hashlib, uuid, datetime
from typing import Dict, Any, Optional
from backend.app.config import settings
from backend.app.models.order import RazorpayOrder, PaymentCaptureResult, RefundResult, TransactionState

class RazorpayClientWrapper:
    def __init__(self):
        self.key_id = settings.RAZORPAY_KEY_ID
        self.key_secret = settings.RAZORPAY_KEY_SECRET
        self.webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
        self._orders_db: Dict[str, RazorpayOrder] = {}
        self._payments_db: Dict[str, PaymentCaptureResult] = {}
        self._refunds_db: Dict[str, RefundResult] = {}

    def create_order(
        self,
        amount_inr: float,
        cart_id: str,
        idempotency_key: Optional[str] = None,
        notes: Optional[Dict[str, str]] = None
    ) -> RazorpayOrder:
        order_id = f"order_{uuid.uuid4().hex[:14]}"
        receipt = f"rcpt_{uuid.uuid4().hex[:8]}"
        amount_in_paise = int(amount_inr * 100)

        order = RazorpayOrder(
            order_id=order_id,
            cart_id=cart_id,
            amount=amount_inr,
            amount_in_paise=amount_in_paise,
            currency="INR",
            status="created",
            receipt=receipt,
            notes=notes or {},
            state=TransactionState.ORDER_CREATED,
            idempotency_key=idempotency_key
        )
        self._orders_db[order_id] = order
        return order

    def simulate_payment_capture(
        self,
        order_id: str,
        amount_inr: float,
        method: str = "upi",
        force_fail: bool = False
    ) -> PaymentCaptureResult:
        order = self._orders_db.get(order_id)
        payment_id = f"pay_{uuid.uuid4().hex[:14]}"

        if force_fail:
            res = PaymentCaptureResult(
                payment_id=payment_id,
                order_id=order_id,
                amount=amount_inr,
                status="failed",
                method=method,
                webhook_verified=False,
                error_code="BAD_REQUEST_PAYMENT_DECLINED_BY_BANK",
                error_description="Card/UPI payment authorization declined by issuing bank."
            )
            self._payments_db[payment_id] = res
            if order:
                order.state = TransactionState.PAYMENT_FAILED
            return res

        payload_str = f"{order_id}|{payment_id}"
        sig = hmac.new(
            self.key_secret.encode("utf-8"),
            payload_str.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        res = PaymentCaptureResult(
            payment_id=payment_id,
            order_id=order_id,
            amount=amount_inr,
            status="captured",
            method=method,
            razorpay_signature=sig,
            webhook_verified=True
        )
        self._payments_db[payment_id] = res
        if order:
            order.state = TransactionState.PAYMENT_CAPTURED
        return res

    def process_refund(
        self,
        payment_id: str,
        amount_inr: float,
        reason: str = "Buyer requested cancellation"
    ) -> RefundResult:
        payment = self._payments_db.get(payment_id)
        if not payment or payment.status != "captured":
            raise ValueError(f"Cannot refund non-captured payment {payment_id}")

        if amount_inr > payment.amount:
            raise ValueError(f"Refund amount ₹{amount_inr} exceeds original payment ₹{payment.amount}")

        refund_id = f"rfnd_{uuid.uuid4().hex[:14]}"
        res = RefundResult(
            refund_id=refund_id,
            payment_id=payment_id,
            order_id=payment.order_id,
            amount=amount_inr,
            status="processed",
            reason=reason
        )
        self._refunds_db[refund_id] = res
        order = self._orders_db.get(payment.order_id)
        if order:
            order.state = TransactionState.REFUNDED
        return res

    def verify_webhook_signature(self, raw_body: str, signature: str) -> bool:
        expected = hmac.new(
            self.webhook_secret.encode("utf-8"),
            raw_body.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

razorpay_client = RazorpayClientWrapper()
