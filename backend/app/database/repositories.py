import json
import re
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
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
    def get_all(self, db: Optional[Session] = None) -> List[Product]:
        s = db or SessionLocal()
        try:
            models = s.query(ProductModel).all()
            return [_product_model_to_domain(m) for m in models]
        finally:
            if not db:
                s.close()

    def get_by_id(self, product_id: str, db: Optional[Session] = None) -> Optional[Product]:
        s = db or SessionLocal()
        try:
            pm = s.query(ProductModel).filter(ProductModel.id == product_id).first()
            return _product_model_to_domain(pm) if pm else None
        finally:
            if not db:
                s.close()

    def filter_products(self, filter_params: ProductFilter, db: Optional[Session] = None) -> List[Product]:
        s = db or SessionLocal()
        try:
            query = s.query(ProductModel)

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
        finally:
            if not db:
                s.close()

    def decrement_inventory(self, product_id: str, quantity: int = 1, db: Optional[Session] = None) -> bool:
        s = db or SessionLocal()
        try:
            rows_updated = s.query(ProductModel).filter(
                ProductModel.id == product_id,
                ProductModel.inventory >= quantity
            ).update(
                {ProductModel.inventory: ProductModel.inventory - quantity},
                synchronize_session=False
            )
            if not db:
                s.commit()
            return rows_updated > 0
        except Exception:
            if not db:
                s.rollback()
            raise
        finally:
            if not db:
                s.close()

    def increment_inventory(self, product_id: str, quantity: int = 1, db: Optional[Session] = None) -> bool:
        s = db or SessionLocal()
        try:
            rows_updated = s.query(ProductModel).filter(
                ProductModel.id == product_id
            ).update(
                {ProductModel.inventory: ProductModel.inventory + quantity},
                synchronize_session=False
            )
            if not db:
                s.commit()
            return rows_updated > 0
        except Exception:
            if not db:
                s.rollback()
            raise
        finally:
            if not db:
                s.close()


class CartRepository:
    def get_cart(self, cart_id: str, db: Optional[Session] = None) -> Optional[Cart]:
        s = db or SessionLocal()
        try:
            cm = s.query(CartModel).filter(CartModel.cart_id == cart_id).first()
            if not cm:
                return None
            items = [
                CartItem(
                    product_id=im.product_id,
                    name=im.name,
                    price=im.price,
                    quantity=im.quantity,
                    subtotal=im.subtotal,
                    category=im.category
                ) for im in cm.items
            ]
            bundle = None
            if cm.applied_bundle_json:
                try:
                    bundle = BundleOffer(**json.loads(cm.applied_bundle_json))
                except Exception:
                    bundle = None

            return Cart(
                cart_id=cm.cart_id,
                user_id=cm.user_id,
                currency=cm.currency,
                items=items,
                subtotal_amount=cm.subtotal_amount,
                discount_amount=cm.discount_amount,
                total_amount=cm.total_amount,
                applied_bundle=bundle
            )
        finally:
            if not db:
                s.close()

    def save_cart(self, cart: Cart, db: Optional[Session] = None) -> Cart:
        cart.recalculate()
        s = db or SessionLocal()
        try:
            cm = s.query(CartModel).filter(CartModel.cart_id == cart.cart_id).first()
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
                s.add(cm)
            else:
                cm.user_id = cart.user_id
                cm.currency = cart.currency
                cm.subtotal_amount = cart.subtotal_amount
                cm.discount_amount = cart.discount_amount
                cm.total_amount = cart.total_amount
                cm.applied_bundle_json = cart.applied_bundle.model_dump_json() if cart.applied_bundle else None
                s.query(CartItemModel).filter(CartItemModel.cart_id == cart.cart_id).delete()

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
                s.add(im)

            if not db:
                s.commit()
            return cart
        except Exception:
            if not db:
                s.rollback()
            raise
        finally:
            if not db:
                s.close()

    def clear_cart(self, cart_id: str, db: Optional[Session] = None) -> bool:
        s = db or SessionLocal()
        try:
            s.query(CartItemModel).filter(CartItemModel.cart_id == cart_id).delete()
            cm = s.query(CartModel).filter(CartModel.cart_id == cart_id).first()
            if cm:
                cm.subtotal_amount = 0.0
                cm.discount_amount = 0.0
                cm.total_amount = 0.0
                cm.applied_bundle_json = None
            if not db:
                s.commit()
            return True
        except Exception:
            if not db:
                s.rollback()
            raise
        finally:
            if not db:
                s.close()

    def delete_cart(self, cart_id: str, db: Optional[Session] = None) -> bool:
        s = db or SessionLocal()
        try:
            s.query(CartItemModel).filter(CartItemModel.cart_id == cart_id).delete()
            rows = s.query(CartModel).filter(CartModel.cart_id == cart_id).delete()
            if not db:
                s.commit()
            return rows > 0
        except Exception:
            if not db:
                s.rollback()
            raise
        finally:
            if not db:
                s.close()


class OrderRepository:
    def create_order(self, order: RazorpayOrder, db: Optional[Session] = None) -> RazorpayOrder:
        s = db or SessionLocal()
        try:
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
                notes_json=json.dumps(order.notes or {}, default=str),
                idempotency_key=order.idempotency_key
            )
            s.merge(om)
            if not db:
                s.commit()
            return order
        except Exception:
            if not db:
                s.rollback()
            raise
        finally:
            if not db:
                s.close()

    def get_order(self, order_id: str, db: Optional[Session] = None) -> Optional[RazorpayOrder]:
        s = db or SessionLocal()
        try:
            om = s.query(OrderModel).filter(OrderModel.order_id == order_id).first()
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
        finally:
            if not db:
                s.close()

    def update_order_state(self, order_id: str, status: str, state: TransactionState, db: Optional[Session] = None) -> Optional[RazorpayOrder]:
        s = db or SessionLocal()
        try:
            om = s.query(OrderModel).filter(OrderModel.order_id == order_id).first()
            if om:
                om.status = status
                om.state = state.value if isinstance(state, TransactionState) else str(state)
                if not db:
                    s.commit()
                return self.get_order(order_id, db=s)
            return None
        except Exception:
            if not db:
                s.rollback()
            raise
        finally:
            if not db:
                s.close()

    def list_orders(self, user_id: str, db: Optional[Session] = None) -> List[RazorpayOrder]:
        s = db or SessionLocal()
        try:
            models = s.query(OrderModel).filter(OrderModel.user_id == user_id).all()
            results = []
            for om in models:
                results.append(RazorpayOrder(
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
            return results
        finally:
            if not db:
                s.close()


class PaymentRepository:
    def record_payment(self, payment: PaymentCaptureResult, user_id: str = "user_default_buyer", db: Optional[Session] = None) -> PaymentCaptureResult:
        s = db or SessionLocal()
        try:
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
            s.merge(pm)
            if not db:
                s.commit()
            return payment
        except Exception:
            if not db:
                s.rollback()
            raise
        finally:
            if not db:
                s.close()

    def get_payment(self, payment_id: str, db: Optional[Session] = None) -> Optional[PaymentCaptureResult]:
        s = db or SessionLocal()
        try:
            pm = s.query(PaymentModel).filter(PaymentModel.payment_id == payment_id).first()
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
        finally:
            if not db:
                s.close()

    def update_status(self, payment_id: str, status: str, error_code: Optional[str] = None, error_desc: Optional[str] = None, db: Optional[Session] = None) -> Optional[PaymentCaptureResult]:
        s = db or SessionLocal()
        try:
            pm = s.query(PaymentModel).filter(PaymentModel.payment_id == payment_id).first()
            if pm:
                pm.status = status
                if error_code:
                    pm.error_code = error_code
                if error_desc:
                    pm.error_description = error_desc
                if status == "captured":
                    pm.verified_at = datetime.now(timezone.utc)
                if not db:
                    s.commit()
                return self.get_payment(payment_id, db=s)
            return None
        except Exception:
            if not db:
                s.rollback()
            raise
        finally:
            if not db:
                s.close()


class RefundRepository:
    def create_refund(self, refund: RefundResult, user_id: str = "user_default_buyer", db: Optional[Session] = None) -> RefundResult:
        s = db or SessionLocal()
        try:
            rm = RefundModel(
                refund_id=refund.refund_id,
                payment_id=refund.payment_id,
                order_id=refund.order_id,
                user_id=user_id,
                amount=refund.amount,
                currency=refund.currency,
                status=refund.status
            )
            s.merge(rm)
            if not db:
                s.commit()
            return refund
        except Exception:
            if not db:
                s.rollback()
            raise
        finally:
            if not db:
                s.close()

    def get_refund(self, refund_id: str, db: Optional[Session] = None) -> Optional[RefundResult]:
        s = db or SessionLocal()
        try:
            rm = s.query(RefundModel).filter(RefundModel.refund_id == refund_id).first()
            if not rm:
                return None
            return RefundResult(
                refund_id=rm.refund_id,
                payment_id=rm.payment_id,
                order_id=rm.order_id,
                amount=rm.amount,
                currency=rm.currency,
                status=rm.status
            )
        finally:
            if not db:
                s.close()

    def get_total_refunded(self, payment_id: str, db: Optional[Session] = None) -> float:
        s = db or SessionLocal()
        try:
            result = s.query(func.sum(RefundModel.amount)).filter(
                RefundModel.payment_id == payment_id,
                RefundModel.status == "processed"
            ).scalar()
            return float(result or 0.0)
        finally:
            if not db:
                s.close()


class ApprovalRepository:
    def create_approval(self, token: str, user_id: str, amount: float, cart_id: str, reason: str, db: Optional[Session] = None) -> ApprovalModel:
        s = db or SessionLocal()
        try:
            app = ApprovalModel(
                token=token,
                user_id=user_id,
                amount=amount,
                cart_id=cart_id,
                status="PENDING",
                reason=reason
            )
            s.add(app)
            if not db:
                s.commit()
            return app
        except Exception:
            if not db:
                s.rollback()
            raise
        finally:
            if not db:
                s.close()

    def is_approved(self, token: str, max_age_seconds: int = 900, db: Optional[Session] = None) -> bool:
        s = db or SessionLocal()
        try:
            app = s.query(ApprovalModel).filter(ApprovalModel.token == token).first()
            if not app or app.status != "APPROVED":
                return False
            
            if app.approved_at:
                now = datetime.now(timezone.utc)
                app_time = app.approved_at if app.approved_at.tzinfo else app.approved_at.replace(tzinfo=timezone.utc)
                if (now - app_time).total_seconds() > max_age_seconds:
                    return False
            return True
        finally:
            if not db:
                s.close()

    def get_approval(self, token: str, db: Optional[Session] = None) -> Optional[ApprovalModel]:
        s = db or SessionLocal()
        try:
            return s.query(ApprovalModel).filter(ApprovalModel.token == token).first()
        finally:
            if not db:
                s.close()

    def approve(self, token: str, db: Optional[Session] = None) -> bool:
        s = db or SessionLocal()
        try:
            app = s.query(ApprovalModel).filter(ApprovalModel.token == token).first()
            if app:
                app.status = "APPROVED"
                app.approved_at = datetime.now(timezone.utc)
                if not db:
                    s.commit()
                return True
            return False
        except Exception:
            if not db:
                s.rollback()
            raise
        finally:
            if not db:
                s.close()


class SpendRepository:
    def get_user_cumulative_spend(self, user_id: str, db: Optional[Session] = None) -> float:
        s = db or SessionLocal()
        try:
            record = s.query(UserSpendModel).filter(UserSpendModel.user_id == user_id).first()
            return float(record.cumulative_spend_inr) if record else 0.0
        finally:
            if not db:
                s.close()

    def record_spend(self, user_id: str, amount: float, db: Optional[Session] = None):
        s = db or SessionLocal()
        try:
            record = s.query(UserSpendModel).filter(UserSpendModel.user_id == user_id).first()
            if record:
                s.query(UserSpendModel).filter(UserSpendModel.user_id == user_id).update(
                    {UserSpendModel.cumulative_spend_inr: UserSpendModel.cumulative_spend_inr + amount},
                    synchronize_session=False
                )
            else:
                s.add(UserSpendModel(user_id=user_id, cumulative_spend_inr=amount))
            if not db:
                s.commit()
        except Exception:
            if not db:
                s.rollback()
            raise
        finally:
            if not db:
                s.close()

    def decrement_spend(self, user_id: str, amount: float, db: Optional[Session] = None):
        s = db or SessionLocal()
        try:
            record = s.query(UserSpendModel).filter(UserSpendModel.user_id == user_id).first()
            if record:
                new_balance = max(0.0, record.cumulative_spend_inr - amount)
                s.query(UserSpendModel).filter(UserSpendModel.user_id == user_id).update(
                    {UserSpendModel.cumulative_spend_inr: new_balance},
                    synchronize_session=False
                )
            if not db:
                s.commit()
        except Exception:
            if not db:
                s.rollback()
            raise
        finally:
            if not db:
                s.close()

    def reset_spend(self, user_id: str, db: Optional[Session] = None):
        s = db or SessionLocal()
        try:
            s.query(UserSpendModel).filter(UserSpendModel.user_id == user_id).update(
                {UserSpendModel.cumulative_spend_inr: 0.0},
                synchronize_session=False
            )
            if not db:
                s.commit()
        except Exception:
            if not db:
                s.rollback()
            raise
        finally:
            if not db:
                s.close()


class AuditRepository:
    def save_record(self, audit_record: AuditRecord, db: Optional[Session] = None) -> AuditRecord:
        s = db or SessionLocal()
        try:
            am = AuditRecordModel(
                index=audit_record.index,
                event_id=audit_record.event_id,
                timestamp=audit_record.timestamp,
                prev_hash=audit_record.prev_hash,
                record_hash=audit_record.record_hash,
                actor_id=audit_record.actor_id,
                actor_role=audit_record.actor_role,
                action=audit_record.action,
                intent=audit_record.intent,
                tool_name=audit_record.tool_name,
                arguments_json=json.dumps(audit_record.arguments or {}, default=str),
                guardrail_decision=audit_record.guardrail_decision,
                approval_required=audit_record.approval_required,
                transaction_state=audit_record.transaction_state,
                result_status=audit_record.result_status,
                signature=audit_record.signature,
                latency_ms=audit_record.latency_ms,
                explainability_notes=audit_record.explainability_notes
            )
            s.add(am)
            if not db:
                s.commit()
            return audit_record
        except Exception:
            if not db:
                s.rollback()
            raise
        finally:
            if not db:
                s.close()

    record_audit = save_record

    def get_latest(self, db: Optional[Session] = None) -> Optional[AuditRecord]:
        s = db or SessionLocal()
        try:
            am = s.query(AuditRecordModel).order_by(AuditRecordModel.index.desc()).first()
            if not am:
                return None
            try:
                args = json.loads(am.arguments_json or "{}")
            except Exception:
                args = {}
            return AuditRecord(
                index=am.index,
                timestamp=am.timestamp,
                event_id=am.event_id,
                prev_hash=am.prev_hash,
                record_hash=am.record_hash,
                actor_id=am.actor_id,
                actor_role=am.actor_role,
                action=am.action,
                intent=am.intent,
                tool_name=am.tool_name,
                arguments=args,
                guardrail_decision=am.guardrail_decision,
                approval_required=am.approval_required,
                transaction_state=am.transaction_state,
                result_status=am.result_status,
                signature=am.signature,
                latency_ms=am.latency_ms or 0.0,
                explainability_notes=am.explainability_notes or ""
            )
        finally:
            if not db:
                s.close()

    def get_all(self, db: Optional[Session] = None) -> List[AuditRecord]:
        s = db or SessionLocal()
        try:
            models = s.query(AuditRecordModel).order_by(AuditRecordModel.index.asc()).all()
            results = []
            for am in models:
                try:
                    args = json.loads(am.arguments_json or "{}")
                except Exception:
                    args = {}
                results.append(AuditRecord(
                    index=am.index,
                    timestamp=am.timestamp,
                    event_id=am.event_id,
                    prev_hash=am.prev_hash,
                    record_hash=am.record_hash,
                    actor_id=am.actor_id,
                    actor_role=am.actor_role,
                    action=am.action,
                    intent=am.intent,
                    tool_name=am.tool_name,
                    arguments=args,
                    guardrail_decision=am.guardrail_decision,
                    approval_required=am.approval_required,
                    transaction_state=am.transaction_state,
                    result_status=am.result_status,
                    signature=am.signature,
                    latency_ms=am.latency_ms or 0.0,
                    explainability_notes=am.explainability_notes or ""
                ))
            return results
        finally:
            if not db:
                s.close()

    def get_audit_trail(self, limit: int = 100, db: Optional[Session] = None) -> List[AuditRecord]:
        s = db or SessionLocal()
        try:
            models = s.query(AuditRecordModel).order_by(AuditRecordModel.index.desc()).limit(limit).all()
            results = []
            for am in models:
                try:
                    args = json.loads(am.arguments_json or "{}")
                except Exception:
                    args = {}
                results.append(AuditRecord(
                    index=am.index,
                    timestamp=am.timestamp,
                    event_id=am.event_id,
                    prev_hash=am.prev_hash,
                    record_hash=am.record_hash,
                    actor_id=am.actor_id,
                    actor_role=am.actor_role,
                    action=am.action,
                    intent=am.intent,
                    tool_name=am.tool_name,
                    arguments=args,
                    guardrail_decision=am.guardrail_decision,
                    approval_required=am.approval_required,
                    transaction_state=am.transaction_state,
                    result_status=am.result_status,
                    signature=am.signature,
                    latency_ms=am.latency_ms or 0.0,
                    explainability_notes=am.explainability_notes or ""
                ))
            return results
        finally:
            if not db:
                s.close()


class IdempotencyRepository:
    def check_key(self, key: str, db: Optional[Session] = None) -> Optional[Dict[str, Any]]:
        s = db or SessionLocal()
        try:
            im = s.query(IdempotencyModel).filter(IdempotencyModel.key == key).first()
            if im:
                try:
                    return json.loads(im.response_json)
                except Exception:
                    return {}
            return None
        finally:
            if not db:
                s.close()

    def register_key(self, key: str, data: Dict[str, Any], db: Optional[Session] = None):
        s = db or SessionLocal()
        try:
            im = IdempotencyModel(key=key, response_json=json.dumps(data, default=str))
            s.merge(im)
            if not db:
                s.commit()
        except Exception:
            if not db:
                s.rollback()
            raise
        finally:
            if not db:
                s.close()


# Singleton repository instances
product_repo = ProductRepository()
cart_repo = CartRepository()
order_repo = OrderRepository()
payment_repo = PaymentRepository()
refund_repo = RefundRepository()
approval_repo = ApprovalRepository()
spend_repo = SpendRepository()
audit_repo = AuditRepository()
idempotency_repo = IdempotencyRepository()