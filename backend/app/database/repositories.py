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
        """Atomic SQL decrement preventing concurrency overselling."""
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
        """Atomic SQL increment."""
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
                notes_json=json.dumps(order.notes or {}),
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


class ApprovalRepository:
    def is_approved(self, token: str, max_age_seconds: int = 900, db: Optional[Session] = None) -> bool:
        """Validates approval and verifies token age against expiry limit."""
        s = db or SessionLocal()
        try:
            app = s.query(ApprovalModel).filter(ApprovalModel.token == token).first()
            if not app or app.status != "APPROVED":
                return False
            
            # Verify expiry (TTL)
            if app.approved_at:
                now = datetime.now(timezone.utc)
                app_time = app.approved_at if app.approved_at.tzinfo else app.approved_at.replace(tzinfo=timezone.utc)
                if (now - app_time).total_seconds() > max_age_seconds:
                    return False
            return True
        finally:
            if not db:
                s.close()


class SpendRepository:
    def record_spend(self, user_id: str, amount: float, db: Optional[Session] = None):
        """Atomic addition of user cumulative spend."""
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
        """Deducts refunded amounts from cumulative user spend total."""
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


# Singleton repository instances
product_repo = ProductRepository()
cart_repo = CartRepository()
order_repo = OrderRepository()
payment_repo = PaymentRepository()
refund_repo = RefundRepository()
approval_repo = ApprovalRepository()
spend_repo = SpendRepository()