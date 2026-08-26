import json
import re
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from backend.app.database.db import SessionLocal
from backend.app.database.models import (
    ProductModel, CartModel, CartItemModel, OrderModel,
    PaymentModel, RefundModel, ApprovalModel, AuditRecordModel,
    UserSpendModel, IdempotencyModel
)
from backend.app.models.catalog import Product, ProductFilter
from backend.app.models.cart import Cart, CartItem, BundleOffer
from backend.app.models.order import RazorpayOrder, PaymentCaptureResult, RefundResult, TransactionState
from backend.app.models.audit import AuditRecord


def _product_model_to_domain(pm: ProductModel) -> Product:
    return Product(
        id=pm.id,
        name=pm.name,
        category=pm.category,
        price=pm.price,
        inventory=pm.inventory,
        rating=pm.rating,
        specs=pm.specs,
        tags=pm.tags,
        complementary_product_ids=pm.complementary_product_ids,
        description=pm.description
    )


class ProductRepository:
    def get_all(self) -> List[Product]:
        with SessionLocal() as db:
            models = db.query(ProductModel).all()
            return [_product_model_to_domain(m) for m in models]

    def get_by_id(self, product_id: str) -> Optional[Product]:
        with SessionLocal() as db:
            pm = db.query(ProductModel).filter(ProductModel.id == product_id).first()
            return _product_model_to_domain(pm) if pm else None

    def filter_products(self, filter_params: ProductFilter) -> List[Product]:
        with SessionLocal() as db:
            query = db.query(ProductModel)

            if filter_params.in_stock_only:
                query = query.filter(ProductModel.inventory > 0)

            if filter_params.max_price is not None and filter_params.max_price > 0:
                query = query.filter(ProductModel.price <= filter_params.max_price)

            candidates = [_product_model_to_domain(m) for m in query.all()]

            if filter_params.category:
                cat_matches = [p for p in candidates if p.category.lower() == filter_params.category.lower()]
                if cat_matches:
                    candidates = cat_matches

            if filter_params.query:
                raw_query = filter_params.query.lower()
                stop_words = {
                    "find", "me", "the", "best", "available", "good", "under", "below",
                    "rs", "inr", "rupees", "for", "a", "an", "with", "around", "i", "need", "want", "show", "buy"
                }
                tokens = [t for t in re.findall(r'[a-zA-Z0-9_.]+', raw_query) if t not in stop_words and len(t) > 1]
                wants_highest_protein = any(p in raw_query for p in ["highest protein", "high protein", "max protein", "protein %", "protein percent"])

                scored_items = []
                for p in candidates:
                    score = 0
                    searchable_text = f"{p.name} {p.category} {' '.join(p.tags)} {' '.join(str(v) for v in p.specs.values())} {p.description}".lower()

                    for token in tokens:
                        if token in p.name.lower():
                            score += 35
                        if any(token == tag.lower() or token in tag.lower() for tag in p.tags):
                            score += 30
                        if token in p.category.lower():
                            score += 20
                        if token in searchable_text:
                            score += 15

                    if p.name.lower() in raw_query or any(tag.lower() in raw_query for tag in p.tags):
                        score += 40

                    if wants_highest_protein and "protein_percentage" in p.specs:
                        prot_match = re.search(r'(\d+)%', str(p.specs["protein_percentage"]))
                        if prot_match:
                            score += int(prot_match.group(1)) * 3

                    if score > 0 or not tokens:
                        scored_items.append((score, p))

                scored_items.sort(key=lambda x: (x[0], x[1].rating, -x[1].price), reverse=True)
                return [item[1] for item in scored_items]

            return candidates

    def decrement_inventory(self, product_id: str, quantity: int = 1) -> bool:
        with SessionLocal() as db:
            pm = db.query(ProductModel).filter(ProductModel.id == product_id).first()
            if pm and pm.inventory >= quantity:
                pm.inventory -= quantity
                db.commit()
                return True
            return False

    def increment_inventory(self, product_id: str, quantity: int = 1) -> bool:
        with SessionLocal() as db:
            pm = db.query(ProductModel).filter(ProductModel.id == product_id).first()
            if pm:
                pm.inventory += quantity
                db.commit()
                return True
            return False


class CartRepository:
    def get_cart(self, cart_id: str) -> Optional[Cart]:
        with SessionLocal() as db:
            cm = db.query(CartModel).filter(CartModel.cart_id == cart_id).first()
            if not cm:
                return None
            items = []
            for im in cm.items:
                items.append(CartItem(
                    product_id=im.product_id,
                    name=im.name,
                    price=im.price,
                    quantity=im.quantity,
                    subtotal=im.subtotal,
                    category=im.category
                ))
            bundle = None
            if cm.applied_bundle_json:
                try:
                    bundle = BundleOffer(**json.loads(cm.applied_bundle_json))
                except Exception:
                    bundle = None

            cart = Cart(
                cart_id=cm.cart_id,
                user_id=cm.user_id,
                currency=cm.currency,
                items=items,
                subtotal_amount=cm.subtotal_amount,
                discount_amount=cm.discount_amount,
                total_amount=cm.total_amount,
                applied_bundle=bundle
            )
            return cart

    def save_cart(self, cart: Cart) -> Cart:
        cart.recalculate()
        with SessionLocal() as db:
            cm = db.query(CartModel).filter(CartModel.cart_id == cart.cart_id).first()
            if not cm:
                cm = CartModel(
                    cart_id=cart.cart_id,
                    user_id=cart.user_id,
                    currency=cart.currency,
                    subtotal_amount=cart.subtotal_amount,
                    discount_amount=cart.discount_amount,
                    total_amount=cart.total_amount,
                    applied_bundle_json=cart.applied_bundle.model_dump_json() if cart.applied_bundle else None
                )
                db.add(cm)
            else:
                cm.user_id = cart.user_id
                cm.currency = cart.currency
                cm.subtotal_amount = cart.subtotal_amount
                cm.discount_amount = cart.discount_amount
                cm.total_amount = cart.total_amount
                cm.applied_bundle_json = cart.applied_bundle.model_dump_json() if cart.applied_bundle else None
                # Clear existing items
                db.query(CartItemModel).filter(CartItemModel.cart_id == cart.cart_id).delete()

            for item in cart.items:
                im = CartItemModel(
                    cart_id=cart.cart_id,
                    product_id=item.product_id,
                    name=item.name,
                    price=item.price,
                    quantity=item.quantity,
                    subtotal=item.subtotal,
                    category=item.category
                )
                db.add(im)

            db.commit()
            return cart


class OrderRepository:
    def create_order(self, order: RazorpayOrder) -> RazorpayOrder:
        with SessionLocal() as db:
            om = OrderModel(
                order_id=order.order_id,
                cart_id=order.cart_id,
                user_id=order.notes.get("user_id", "user_default_buyer") if order.notes else "user_default_buyer",
                amount=order.amount,
                amount_in_paise=order.amount_in_paise,
                currency=order.currency,
                status=order.status,
                receipt=order.receipt,
                state=order.state.value if isinstance(order.state, TransactionState) else str(order.state),
                notes_json=json.dumps(order.notes or {}),
                idempotency_key=order.idempotency_key
            )
            db.merge(om)
            db.commit()
            return order

    def get_order(self, order_id: str) -> Optional[RazorpayOrder]:
        with SessionLocal() as db:
            om = db.query(OrderModel).filter(OrderModel.order_id == order_id).first()
            if not om:
                return None
            return RazorpayOrder(
                order_id=om.order_id,
                cart_id=om.cart_id,
                amount=om.amount,
                amount_in_paise=om.amount_in_paise,
                currency=om.currency,
                status=om.status,
                receipt=om.receipt or "",
                notes=om.notes,
                state=TransactionState(om.state) if om.state in TransactionState._value2member_map_ else TransactionState.ORDER_CREATED,
                idempotency_key=om.idempotency_key
            )

    def update_order_state(self, order_id: str, status: str, state: TransactionState) -> Optional[RazorpayOrder]:
        with SessionLocal() as db:
            om = db.query(OrderModel).filter(OrderModel.order_id == order_id).first()
            if om:
                om.status = status
                om.state = state.value if isinstance(state, TransactionState) else str(state)
                db.commit()
                return self.get_order(order_id)
            return None

    def list_orders(self, limit: int = 50) -> List[RazorpayOrder]:
        with SessionLocal() as db:
            models = db.query(OrderModel).order_by(OrderModel.created_at.desc()).limit(limit).all()
            res = []
            for om in models:
                res.append(RazorpayOrder(
                    order_id=om.order_id,
                    cart_id=om.cart_id,
                    amount=om.amount,
                    amount_in_paise=om.amount_in_paise,
                    currency=om.currency,
                    status=om.status,
                    receipt=om.receipt or "",
                    notes=om.notes,
                    state=TransactionState(om.state) if om.state in TransactionState._value2member_map_ else TransactionState.ORDER_CREATED,
                    idempotency_key=om.idempotency_key
                ))
            return res


class PaymentRepository:
    def record_payment(self, payment: PaymentCaptureResult, user_id: str = "user_default_buyer") -> PaymentCaptureResult:
        with SessionLocal() as db:
            pm = PaymentModel(
                payment_id=payment.payment_id,
                order_id=payment.order_id,
                user_id=user_id,
                amount=payment.amount,
                currency=payment.currency,
                method=payment.method,
                status=payment.status,
                error_code=payment.error_code,
                error_description=payment.error_description,
                verified_at=datetime.now(timezone.utc) if payment.status == "captured" else None
            )
            db.merge(pm)
            db.commit()
            return payment

    def get_payment(self, payment_id: str) -> Optional[PaymentCaptureResult]:
        with SessionLocal() as db:
            pm = db.query(PaymentModel).filter(PaymentModel.payment_id == payment_id).first()
            if not pm:
                return None
            return PaymentCaptureResult(
                payment_id=pm.payment_id,
                order_id=pm.order_id,
                amount=pm.amount,
                currency=pm.currency,
                status=pm.status,
                method=pm.method,
                error_code=pm.error_code,
                error_description=pm.error_description
            )

    def update_status(self, payment_id: str, status: str, error_code: Optional[str] = None, error_desc: Optional[str] = None) -> Optional[PaymentCaptureResult]:
        with SessionLocal() as db:
            pm = db.query(PaymentModel).filter(PaymentModel.payment_id == payment_id).first()
            if pm:
                pm.status = status
                if error_code:
                    pm.error_code = error_code
                if error_desc:
                    pm.error_description = error_desc
                if status == "captured":
                    pm.verified_at = datetime.now(timezone.utc)
                db.commit()
                return self.get_payment(payment_id)
            return None


class RefundRepository:
    def create_refund(self, refund: RefundResult, user_id: str = "user_default_buyer") -> RefundResult:
        with SessionLocal() as db:
            rm = RefundModel(
                refund_id=refund.refund_id,
                payment_id=refund.payment_id,
                order_id=None,
                user_id=user_id,
                amount=refund.amount,
                currency=refund.currency,
                status=refund.status
            )
            db.merge(rm)
            db.commit()
            return refund

    def get_refund(self, refund_id: str) -> Optional[RefundResult]:
        with SessionLocal() as db:
            rm = db.query(RefundModel).filter(RefundModel.refund_id == refund_id).first()
            if not rm:
                return None
            return RefundResult(
                refund_id=rm.refund_id,
                payment_id=rm.payment_id,
                amount=rm.amount,
                currency=rm.currency,
                status=rm.status
            )

    def get_total_refunded(self, payment_id: str) -> float:
        with SessionLocal() as db:
            records = db.query(RefundModel).filter(
                RefundModel.payment_id == payment_id,
                RefundModel.status == "processed"
            ).all()
            return sum(r.amount for r in records)


class ApprovalRepository:
    def create_approval(self, token: str, user_id: str, amount: float, cart_id: Optional[str] = None, reason: Optional[str] = None):
        with SessionLocal() as db:
            app = ApprovalModel(
                token=token,
                user_id=user_id,
                amount=amount,
                cart_id=cart_id,
                reason=reason,
                status="PENDING"
            )
            db.merge(app)
            db.commit()

    def register_approval(self, token: str) -> bool:
        with SessionLocal() as db:
            app = db.query(ApprovalModel).filter(ApprovalModel.token == token).first()
            if app:
                app.status = "APPROVED"
                app.approved_at = datetime.now(timezone.utc)
                db.commit()
                return True
            else:
                # Direct registration
                app = ApprovalModel(
                    token=token,
                    user_id="user_default_buyer",
                    amount=0.0,
                    status="APPROVED",
                    approved_at=datetime.now(timezone.utc)
                )
                db.add(app)
                db.commit()
                return True

    def is_approved(self, token: str) -> bool:
        with SessionLocal() as db:
            app = db.query(ApprovalModel).filter(ApprovalModel.token == token).first()
            return bool(app and app.status == "APPROVED")


class AuditRepository:
    def save_record(self, record: AuditRecord) -> AuditRecord:
        with SessionLocal() as db:
            arm = AuditRecordModel(
                index=record.index,
                event_id=record.event_id,
                timestamp=record.timestamp,
                prev_hash=record.prev_hash,
                record_hash=record.record_hash,
                actor_id=record.actor_id,
                actor_role=record.actor_role,
                action=record.action,
                intent=record.intent,
                tool_name=record.tool_name,
                arguments_json=json.dumps(record.arguments or {}),
                guardrail_decision=record.guardrail_decision,
                approval_required=record.approval_required,
                transaction_state=record.transaction_state,
                result_status=record.result_status,
                signature=record.signature,
                latency_ms=getattr(record, "latency_ms", 0.0) or 0.0,
                explainability_notes=record.explainability_notes or ""
            )
            db.merge(arm)
            db.commit()
            return record

    def get_all(self) -> List[AuditRecord]:
        with SessionLocal() as db:
            models = db.query(AuditRecordModel).order_by(AuditRecordModel.index.asc()).all()
            records = []
            for m in models:
                records.append(AuditRecord(
                    index=m.index,
                    timestamp=m.timestamp,
                    event_id=m.event_id,
                    prev_hash=m.prev_hash,
                    record_hash=m.record_hash,
                    actor_id=m.actor_id,
                    actor_role=m.actor_role,
                    action=m.action,
                    intent=m.intent,
                    tool_name=m.tool_name,
                    arguments=json.loads(m.arguments_json or "{}"),
                    guardrail_decision=m.guardrail_decision,
                    approval_required=m.approval_required,
                    transaction_state=m.transaction_state,
                    result_status=m.result_status,
                    signature=m.signature,
                    explainability_notes=m.explainability_notes
                ))
            return records

    def get_latest(self) -> Optional[AuditRecord]:
        with SessionLocal() as db:
            m = db.query(AuditRecordModel).order_by(AuditRecordModel.index.desc()).first()
            if not m:
                return None
            return AuditRecord(
                index=m.index,
                timestamp=m.timestamp,
                event_id=m.event_id,
                prev_hash=m.prev_hash,
                record_hash=m.record_hash,
                actor_id=m.actor_id,
                actor_role=m.actor_role,
                action=m.action,
                intent=m.intent,
                tool_name=m.tool_name,
                arguments=json.loads(m.arguments_json or "{}"),
                guardrail_decision=m.guardrail_decision,
                approval_required=m.approval_required,
                transaction_state=m.transaction_state,
                result_status=m.result_status,
                signature=m.signature,
                explainability_notes=m.explainability_notes
            )


class SpendRepository:
    def get_user_cumulative_spend(self, user_id: str) -> float:
        with SessionLocal() as db:
            s = db.query(UserSpendModel).filter(UserSpendModel.user_id == user_id).first()
            return s.cumulative_spend_inr if s else 0.0

    def record_spend(self, user_id: str, amount: float):
        with SessionLocal() as db:
            s = db.query(UserSpendModel).filter(UserSpendModel.user_id == user_id).first()
            if s:
                s.cumulative_spend_inr += amount
            else:
                s = UserSpendModel(user_id=user_id, cumulative_spend_inr=amount)
                db.add(s)
            db.commit()

    def reset_spend(self, user_id: str):
        with SessionLocal() as db:
            s = db.query(UserSpendModel).filter(UserSpendModel.user_id == user_id).first()
            if s:
                s.cumulative_spend_inr = 0.0
                db.commit()


class IdempotencyRepository:
    def check_key(self, key: str) -> Optional[Dict[str, Any]]:
        with SessionLocal() as db:
            im = db.query(IdempotencyModel).filter(IdempotencyModel.key == key).first()
            if im:
                try:
                    return json.loads(im.response_json)
                except Exception:
                    return {}
            return None

    def register_key(self, key: str, data: Dict[str, Any]):
        with SessionLocal() as db:
            im = IdempotencyModel(key=key, response_json=json.dumps(data))
            db.merge(im)
            db.commit()


# Singleton repository instances
product_repo = ProductRepository()
cart_repo = CartRepository()
order_repo = OrderRepository()
payment_repo = PaymentRepository()
refund_repo = RefundRepository()
approval_repo = ApprovalRepository()
audit_repo = AuditRepository()
spend_repo = SpendRepository()
idempotency_repo = IdempotencyRepository()
