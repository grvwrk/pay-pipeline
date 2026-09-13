import logging
from typing import Any, Dict, List, Optional

from backend.app.config import settings
from backend.app.database.db import SessionLocal
from backend.app.database.repositories import order_repo
from backend.app.models.order import RazorpayOrder, TransactionState
from backend.app.payment.razorpay_client import razorpay_client
from backend.app.payment.webhook_handler import webhook_handler
from backend.app.audit.audit_service import audit_service

logger = logging.getLogger(__name__)

SETTLED_STATES = (
    TransactionState.PAYMENT_CAPTURED,
    TransactionState.COMPLETED,
    TransactionState.REFUNDED,
)

# A link stays payable until it is cancelled or expires, so a failed attempt on an
# open link is recorded but leaves the order recoverable on retry.
LINK_DEAD_STATUSES = ("cancelled", "expired")


class PaymentReconciler:
    """
    Pull-based counterpart to the webhook receiver.

    Razorpay cannot deliver a webhook to a host it cannot reach, which is the normal
    case during local development. Reconciliation asks Razorpay — over the authenticated
    REST API — what actually happened to an order, then applies exactly the same state
    transitions the webhook path would. The gateway stays the sole source of truth;
    this only changes how its verdict is obtained.
    """

    @staticmethod
    def _pick_attempt(payments: List[Dict[str, Any]], status: str) -> Optional[Dict[str, Any]]:
        for payment in payments:
            if isinstance(payment, dict) and payment.get("status") == status:
                return payment
        return None

    @classmethod
    def _gateway_verdict(cls, order: RazorpayOrder) -> Dict[str, Any]:
        """Ask Razorpay what happened. Returns an outcome of captured / failed / pending."""
        notes = order.notes or {}
        link_id = notes.get("payment_link_id")
        link = None

        if link_id:
            link = razorpay_client.fetch_remote_payment_link(link_id)
            if link is None:
                return {"outcome": "unreachable", "detail": f"Could not read payment link {link_id} from Razorpay."}
        else:
            # Orders created before the link id was persisted can still be recovered
            # by the reference_id the link was opened with. The list response omits
            # the payment attempts, so re-read the link in full once it is identified.
            found = razorpay_client.find_remote_payment_link_by_reference(order.order_id)
            if found:
                link_id = found.get("id")
                order_repo.merge_notes(order.order_id, {
                    "payment_link_id": link_id or "",
                    "payment_link_url": found.get("short_url") or "",
                })
                link = (razorpay_client.fetch_remote_payment_link(link_id) if link_id else None) or found

        if link:
            # The link mints its own Razorpay order; remember it so a retried webhook
            # naming that order can still be traced back here.
            if link.get("order_id"):
                order_repo.merge_notes(order.order_id, {"link_order_id": link["order_id"]})

            attempts = link.get("payments") or []
            captured = cls._pick_attempt(attempts, "captured")
            link_status = link.get("status")

            if link_status == "paid" or captured:
                paid_paise = link.get("amount_paid") or link.get("amount") or 0
                return {
                    "outcome": "captured",
                    "payment_id": (captured or {}).get("payment_id") or (captured or {}).get("id") or "unknown_pay",
                    "amount": float(paid_paise) / 100.0,
                    "detail": f"Payment link {link_id} is paid.",
                }

            if link_status in LINK_DEAD_STATUSES:
                return {
                    "outcome": "failed",
                    "payment_id": "unknown_pay",
                    "amount": order.amount,
                    "detail": f"Payment link {link_id} is {link_status}.",
                }

            failed = cls._pick_attempt(attempts, "failed")
            if failed:
                return {
                    "outcome": "failed",
                    "payment_id": failed.get("payment_id") or failed.get("id") or "unknown_pay",
                    "amount": float(failed.get("amount") or 0) / 100.0 or order.amount,
                    "detail": f"Last attempt on payment link {link_id} failed.",
                }

            return {"outcome": "pending", "detail": f"Payment link {link_id} has not been paid yet."}

        # No link on this order: it may have been paid through Razorpay Checkout,
        # whose payments hang off the order id this system already stores.
        attempts = razorpay_client.fetch_remote_order_payments(order.order_id)
        captured = cls._pick_attempt(attempts, "captured")
        if captured:
            return {
                "outcome": "captured",
                "payment_id": captured.get("id") or "unknown_pay",
                "amount": float(captured.get("amount") or 0) / 100.0,
                "detail": f"Razorpay reports a captured payment on order {order.order_id}.",
            }

        failed = cls._pick_attempt(attempts, "failed")
        if failed:
            return {
                "outcome": "failed",
                "payment_id": failed.get("id") or "unknown_pay",
                "amount": float(failed.get("amount") or 0) / 100.0 or order.amount,
                "detail": f"Razorpay reports a failed payment on order {order.order_id}.",
                "error_description": failed.get("error_description"),
            }

        return {"outcome": "pending", "detail": f"Razorpay reports no payment attempts on order {order.order_id}."}

    @classmethod
    def reconcile_order(cls, order_id: str) -> Dict[str, Any]:
        """Reconcile one order against Razorpay and return what changed."""
        order = order_repo.get_order(order_id)
        if not order:
            raise ValueError(f"Order '{order_id}' not found.")

        if order.state in SETTLED_STATES:
            return {
                "order_id": order_id,
                "changed": False,
                "outcome": "already_settled",
                "state": order.state.value,
                "detail": f"Order is already {order.state.value}; nothing to reconcile.",
            }

        if settings.PAYMENT_PROVIDER_MODE != "razorpay":
            return {
                "order_id": order_id,
                "changed": False,
                "outcome": "unsupported",
                "state": order.state.value,
                "detail": "Reconciliation queries the Razorpay API and is unavailable in simulator mode.",
            }

        verdict = cls._gateway_verdict(order)
        outcome = verdict["outcome"]

        if outcome in ("pending", "unreachable"):
            return {
                "order_id": order_id,
                "changed": False,
                "outcome": outcome,
                "state": order.state.value,
                "detail": verdict["detail"],
            }

        session = SessionLocal()
        try:
            if outcome == "captured":
                ok, code, data = webhook_handler.apply_capture(
                    order, verdict["payment_id"], verdict["amount"], session
                )
            else:
                ok, code, data = webhook_handler.apply_failure(
                    order, verdict["payment_id"], verdict["amount"], session,
                    verdict.get("error_description") or verdict["detail"]
                )

            if not ok:
                session.rollback()
                return {
                    "order_id": order_id,
                    "changed": False,
                    "outcome": "rejected",
                    "state": order.state.value,
                    "detail": f"{code}: {data}",
                }

            session.commit()
        except Exception as exc:
            session.rollback()
            logger.error("Reconciliation failed for order %s: %s", order_id, exc)
            raise
        finally:
            session.close()

        refreshed = order_repo.get_order(order_id)
        changed = bool(refreshed and refreshed.state != order.state)

        audit_service.record_event(
            actor_id="RECONCILER",
            actor_role="PAYMENT_GATEWAY",
            action="PAYMENT_RECONCILED_FROM_GATEWAY",
            arguments={"order_id": order_id, "outcome": outcome, "code": code, **data},
            transaction_state=refreshed.state.value if refreshed else None,
            result_status="SUCCESS" if outcome == "captured" else "FAILED",
            explainability_notes=(
                f"Order state pulled from the Razorpay API rather than a webhook. {verdict['detail']}"
            )
        )

        return {
            "order_id": order_id,
            "changed": changed,
            "outcome": outcome,
            "code": code,
            "state": refreshed.state.value if refreshed else order.state.value,
            "detail": verdict["detail"],
            "payment_id": verdict.get("payment_id"),
        }

    @classmethod
    def reconcile_pending(cls, limit: int = 50) -> Dict[str, Any]:
        """Reconcile every order that has not reached a settled state yet."""
        pending = [
            order for order in order_repo.list_orders(limit=limit)
            if order.state not in SETTLED_STATES
        ]

        results = []
        for order in pending:
            try:
                results.append(cls.reconcile_order(order.order_id))
            except Exception as exc:
                logger.error("Skipping order %s during bulk reconciliation: %s", order.order_id, exc)
                results.append({
                    "order_id": order.order_id,
                    "changed": False,
                    "outcome": "error",
                    "detail": str(exc),
                })

        return {
            "checked": len(results),
            "updated": sum(1 for r in results if r.get("changed")),
            "results": results,
        }


payment_reconciler = PaymentReconciler()
