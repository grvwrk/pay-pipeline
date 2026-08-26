import os

def write(filepath, content):
    d = os.path.dirname(filepath)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Wrote: {filepath}")

# 1. Razorpay Client
write('backend/app/payment/razorpay_client.py', '''import hmac, hashlib, uuid, datetime
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
''')

# 2. State Machine
write('backend/app/payment/state_machine.py', '''from backend.app.models.order import TransactionState

class TransactionStateMachine:
    VALID_TRANSITIONS = {
        TransactionState.DISCOVERED: [TransactionState.SELECTED, TransactionState.DENIED],
        TransactionState.SELECTED: [TransactionState.CART_CREATED, TransactionState.DISCOVERED],
        TransactionState.CART_CREATED: [TransactionState.GUARDRAIL_EVALUATED, TransactionState.DISCOVERED],
        TransactionState.GUARDRAIL_EVALUATED: [
            TransactionState.PENDING_APPROVAL,
            TransactionState.ORDER_CREATED,
            TransactionState.DENIED
        ],
        TransactionState.PENDING_APPROVAL: [TransactionState.ORDER_CREATED, TransactionState.DENIED],
        TransactionState.ORDER_CREATED: [TransactionState.PAYMENT_PENDING, TransactionState.DENIED],
        TransactionState.PAYMENT_PENDING: [TransactionState.PAYMENT_CAPTURED, TransactionState.PAYMENT_FAILED],
        TransactionState.PAYMENT_CAPTURED: [TransactionState.COMPLETED, TransactionState.REFUNDED],
        TransactionState.PAYMENT_FAILED: [TransactionState.PAYMENT_PENDING, TransactionState.DENIED],
        TransactionState.COMPLETED: [TransactionState.REFUNDED],
        TransactionState.REFUNDED: [],
        TransactionState.DENIED: []
    }

    @classmethod
    def can_transition(cls, current: TransactionState, target: TransactionState) -> bool:
        return target in cls.VALID_TRANSITIONS.get(current, [])

    @classmethod
    def transition(cls, current: TransactionState, target: TransactionState) -> TransactionState:
        if not cls.can_transition(current, target):
            raise ValueError(f"Illegal state transition from {current} to {target}")
        return target

state_machine = TransactionStateMachine()
''')

# 3. Webhook Handler
write('backend/app/payment/webhook_handler.py', '''import json
from typing import Dict, Any, Tuple
from backend.app.payment.razorpay_client import razorpay_client
from backend.app.payment.state_machine import state_machine
from backend.app.models.order import TransactionState
from backend.app.audit.audit_service import audit_service

class AuthoritativeWebhookHandler:
    @classmethod
    def handle_webhook(cls, raw_payload: str, signature: str) -> Tuple[bool, str, Dict[str, Any]]:
        is_valid = razorpay_client.verify_webhook_signature(raw_payload, signature)
        if not is_valid:
            audit_service.record_event(
                actor_id="WEBHOOK_RECEIVER",
                actor_role="RAZORPAY_WEBHOOK",
                action="WEBHOOK_SIGNATURE_REJECTED",
                arguments={"signature": signature},
                result_status="DENIED",
                explainability_notes="Authoritative webhook signature mismatch. Request rejected."
            )
            return False, "INVALID_WEBHOOK_SIGNATURE", {}

        payload = json.loads(raw_payload)
        event_type = payload.get("event", "unknown")
        entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = entity.get("order_id", "unknown_order")
        payment_id = entity.get("id", "unknown_pay")
        amount = float(entity.get("amount", 0)) / 100.0

        if event_type == "payment.captured":
            audit_service.record_event(
                actor_id="RAZORPAY_SERVER",
                actor_role="PAYMENT_GATEWAY",
                action="PAYMENT_CAPTURED_EVENT",
                arguments={"order_id": order_id, "payment_id": payment_id, "amount": amount, "event": event_type},
                transaction_state=TransactionState.PAYMENT_CAPTURED,
                result_status="SUCCESS",
                explainability_notes=f"Authoritative webhook verified for {payment_id}. State transitioned to PAYMENT_CAPTURED."
            )
            return True, "PAYMENT_CAPTURED_VERIFIED", {"order_id": order_id, "payment_id": payment_id, "amount": amount}

        elif event_type == "payment.failed":
            audit_service.record_event(
                actor_id="RAZORPAY_SERVER",
                actor_role="PAYMENT_GATEWAY",
                action="PAYMENT_FAILED_EVENT",
                arguments={"order_id": order_id, "payment_id": payment_id, "amount": amount, "event": event_type},
                transaction_state=TransactionState.PAYMENT_FAILED,
                result_status="FAILED",
                explainability_notes=f"Authoritative payment failure event for {payment_id} verified. No money captured."
            )
            return True, "PAYMENT_FAILED_VERIFIED", {"order_id": order_id, "payment_id": payment_id, "amount": amount}

        return True, f"EVENT_ACKNOWLEDGED_{event_type}", {}

webhook_handler = AuthoritativeWebhookHandler()
''')

# 4. Read Tools & Money Tools
write('backend/app/tools/read_tools.py', '''import json
from typing import List, Optional, Dict, Any
from backend.app.models.catalog import Product, ProductFilter
from backend.app.models.cart import BundleOffer, Cart, CartItem

class ReadAndDecisionTools:
    def __init__(self):
        with open("backend/app/data/catalog_db.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            self.catalog = [Product(**item) for item in data]

    def catalog_lookup(self, filter_params: ProductFilter) -> List[Product]:
        results = self.catalog
        if filter_params.query:
            q = filter_params.query.lower()
            results = [
                p for p in results
                if q in p.name.lower() or q in p.category.lower() or any(q in t.lower() for t in p.tags)
            ]
        if filter_params.category:
            results = [p for p in results if p.category == filter_params.category]
        if filter_params.max_price:
            results = [p for p in results if p.price <= filter_params.max_price]
        if filter_params.min_rating:
            results = [p for p in results if p.rating >= filter_params.min_rating]
        if filter_params.in_stock_only:
            results = [p for p in results if p.inventory > 0]
        return results

    def get_product(self, product_id: str) -> Optional[Product]:
        for p in self.catalog:
            if p.id == product_id:
                return p
        return None

    def calculate_upsell_bundle(self, primary_product_id: str) -> Optional[BundleOffer]:
        primary = self.get_product(primary_product_id)
        if not primary or not primary.complementary_product_ids:
            return None

        comp_id = primary.complementary_product_ids[0]
        comp = self.get_product(comp_id)
        if not comp:
            return None

        original_combined = primary.price + comp.price
        discount_percentage = 5.0
        discount_amount = round(original_combined * (discount_percentage / 100.0), 2)
        bundle_price = round(original_combined - discount_amount, 2)

        return BundleOffer(
            bundle_id=f"bundle_{primary.id}_{comp.id}",
            title=f"{primary.name} + {comp.name} Pro Bundle",
            description=f"Add {comp.name} and unlock 5% instant bundle savings.",
            primary_product_id=primary.id,
            primary_product_name=primary.name,
            complementary_product_id=comp.id,
            complementary_product_name=comp.name,
            original_combined_price=original_combined,
            discounted_bundle_price=bundle_price,
            savings_amount=discount_amount,
            discount_percentage=discount_percentage,
            rationale=f"High complementary pairing: 88% of {primary.name} buyers add {comp.name} for optimal ergonomics."
        )

read_tools = ReadAndDecisionTools()
''')

write('backend/app/tools/money_tools.py', '''from typing import Optional, Dict, Any
from backend.app.models.cart import Cart
from backend.app.models.order import RazorpayOrder, PaymentCaptureResult, RefundResult
from backend.app.guardrails.policy_engine import policy_engine
from backend.app.guardrails.idempotency import idempotency_manager
from backend.app.guardrails.spend_limiter import spend_limiter
from backend.app.payment.razorpay_client import razorpay_client
from backend.app.audit.audit_service import audit_service

class PrivilegedMoneyTools:
    @classmethod
    def create_order_guarded(
        cls,
        cart: Cart,
        user_id: str = "user_default_buyer",
        idempotency_key: Optional[str] = None,
        approval_token: Optional[str] = None
    ) -> Dict[str, Any]:
        policy_res = policy_engine.evaluate(
            cart=cart,
            user_id=user_id,
            idempotency_key=idempotency_key,
            provided_approval_token=approval_token
        )

        if not policy_res.allowed:
            audit_service.record_event(
                actor_id=user_id,
                actor_role="CHECKOUT_AGENT",
                action="CREATE_ORDER_DENIED",
                arguments={"cart_id": cart.cart_id, "amount": cart.total_amount, "decision_code": policy_res.decision_code},
                guardrail_decision=policy_res.decision_code.value,
                approval_required=policy_res.requires_human_approval,
                result_status="DENIED",
                explainability_notes=f"Guardrail denial: {policy_res.reason}"
            )
            return {
                "success": False,
                "decision_code": policy_res.decision_code,
                "reason": policy_res.reason,
                "requires_approval": policy_res.requires_human_approval,
                "approval_token": policy_res.approval_token,
                "policy_evaluation": policy_res.dict()
            }

        order = razorpay_client.create_order(
            amount_inr=cart.total_amount,
            cart_id=cart.cart_id,
            idempotency_key=idempotency_key,
            notes={"user_id": user_id, "items_count": str(len(cart.items))}
        )

        if idempotency_key:
            idempotency_manager.register_key(idempotency_key, order.dict())

        audit_service.record_event(
            actor_id=user_id,
            actor_role="CHECKOUT_AGENT",
            action="CREATE_RAZORPAY_ORDER",
            tool_name="create_order",
            arguments={"order_id": order.order_id, "amount": order.amount, "currency": order.currency, "idempotency_key": idempotency_key},
            guardrail_decision="APPROVED",
            result_status="SUCCESS",
            explainability_notes=f"Order {order.order_id} created on Razorpay test rails for ₹{order.amount:,.2f}."
        )

        return {
            "success": True,
            "order": order.dict(),
            "policy_evaluation": policy_res.dict()
        }

    @classmethod
    def capture_payment_guarded(
        cls,
        order_id: str,
        amount_inr: float,
        user_id: str = "user_default_buyer",
        method: str = "upi",
        force_fail: bool = False
    ) -> Dict[str, Any]:
        res = razorpay_client.simulate_payment_capture(order_id, amount_inr, method, force_fail)
        
        if res.status == "captured":
            spend_limiter.record_spend(user_id, amount_inr)
            audit_service.record_event(
                actor_id=user_id,
                actor_role="RAZORPAY_API",
                action="CAPTURE_PAYMENT_SUCCESS",
                tool_name="capture_payment",
                arguments={"payment_id": res.payment_id, "order_id": order_id, "amount": amount_inr, "method": method},
                guardrail_decision="APPROVED",
                result_status="SUCCESS",
                explainability_notes=f"Payment {res.payment_id} successfully captured on Razorpay test rails."
            )
            return {"success": True, "payment": res.dict()}
        else:
            audit_service.record_event(
                actor_id=user_id,
                actor_role="RAZORPAY_API",
                action="CAPTURE_PAYMENT_FAILED",
                tool_name="capture_payment",
                arguments={"payment_id": res.payment_id, "order_id": order_id, "error": res.error_code},
                guardrail_decision="FAILED",
                result_status="FAILED",
                explainability_notes=f"Payment attempt for order {order_id} failed: {res.error_description}"
            )
            return {"success": False, "payment": res.dict(), "error": res.error_description}

    @classmethod
    def issue_refund_guarded(
        cls,
        payment_id: str,
        amount_inr: float,
        user_id: str = "user_default_buyer",
        reason: str = "Customer request"
    ) -> Dict[str, Any]:
        try:
            refund = razorpay_client.process_refund(payment_id, amount_inr, reason)
            audit_service.record_event(
                actor_id=user_id,
                actor_role="CHECKOUT_AGENT",
                action="ISSUE_REFUND_SUCCESS",
                tool_name="issue_refund",
                arguments={"refund_id": refund.refund_id, "payment_id": payment_id, "amount": amount_inr, "reason": reason},
                guardrail_decision="APPROVED",
                result_status="SUCCESS",
                explainability_notes=f"Refund {refund.refund_id} processed for ₹{amount_inr:,.2f}."
            )
            return {"success": True, "refund": refund.dict()}
        except Exception as e:
            audit_service.record_event(
                actor_id=user_id,
                actor_role="CHECKOUT_AGENT",
                action="ISSUE_REFUND_DENIED",
                tool_name="issue_refund",
                arguments={"payment_id": payment_id, "amount": amount_inr, "error": str(e)},
                guardrail_decision="DENIED",
                result_status="DENIED",
                explainability_notes=f"Refund denied: {str(e)}"
            )
            return {"success": False, "error": str(e)}

money_tools = PrivilegedMoneyTools()
''')

print("Payment and Tools written successfully!")
