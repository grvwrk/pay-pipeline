import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from backend.app.models.campaign import Campaign
from backend.app.database.repositories import order_repo, cart_repo, audit_repo
from backend.app.config import settings

router = APIRouter(prefix="/merchant", tags=["Merchant Revenue Growth & Campaigns"])

CAMPAIGNS_FILE_PATH = Path(__file__).parent.parent / "data" / "campaigns_db.json"


def _load_campaigns_db():
    if CAMPAIGNS_FILE_PATH.exists():
        try:
            with open(CAMPAIGNS_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to parse campaign database file: {str(err)}"
            )
    return {"segments": [], "campaigns": [], "merchant_config": {}}


@router.get("/analytics")
def get_merchant_analytics():
    """Merchant Growth KPIs calculated strictly dynamically from DB repositories and configuration."""
    campaigns_db = _load_campaigns_db()

    # 1. Baseline AOV Check
    merchant_config = campaigns_db.get("merchant_config", {})
    baseline_aov = merchant_config.get("baseline_aov_inr") or getattr(settings, "MERCHANT_BASELINE_AOV_INR", None)

    if baseline_aov is None or float(baseline_aov) <= 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Merchant baseline AOV is not configured. Set 'baseline_aov_inr' in merchant config."
        )
    baseline_aov = float(baseline_aov)

    # 2. Orders & Revenue Calculation
    all_orders = order_repo.list_orders(limit=1000)
    captured_orders = [o for o in all_orders if o.state == "PAYMENT_CAPTURED"]
    total_orders = len(captured_orders)

    if total_orders == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No captured orders found in database to calculate merchant analytics."
        )

    total_revenue = round(sum(o.amount for o in captured_orders), 2)
    agent_aov = round(total_revenue / total_orders, 2)

    # 3. Cart Abandonment Rate
    all_carts = cart_repo.list_carts(limit=1000) if hasattr(cart_repo, "list_carts") else []
    total_carts = len(all_carts)
    
    if total_carts == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No cart records found in database to calculate cart abandonment rate."
        )

    cart_abandonment_rate = round(max(0.0, (total_carts - total_orders) / total_carts), 2)

    # 4. Upsell Conversion Rate
    upsell_orders_count = sum(
        1 for o in captured_orders
        if (isinstance(o.notes, dict) and o.notes.get("bundle_applied") == "true")
    )
    upsell_conversion_rate = round(upsell_orders_count / total_orders, 2)

    # 5. Guardrail Interceptions
    audit_chain = audit_repo.list_all() if hasattr(audit_repo, "list_all") else []
    interceptions = sum(1 for r in audit_chain if r.result_status == "DENIED")

    # 6. AOV Growth Lift
    aov_lift_percent = round(((agent_aov - baseline_aov) / baseline_aov) * 100.0, 1)

    return {
        "kpis": {
            "total_revenue_inr": total_revenue,
            "average_order_value_inr": agent_aov,
            "baseline_aov_without_agent_inr": baseline_aov,
            "aov_growth_percentage": aov_lift_percent,
            "upsell_conversion_rate": upsell_conversion_rate,
            "cart_abandonment_rate": cart_abandonment_rate,
            "guardrail_interceptions_count": interceptions,
            "total_orders_processed": total_orders
        },
        "segments": campaigns_db.get("segments", []),
        "campaigns": campaigns_db.get("campaigns", [])
    }


@router.post("/campaigns")
def create_campaign(campaign: Campaign):
    """Launch bounded revenue growth campaign."""
    campaigns_db = _load_campaigns_db()
    campaigns_db.setdefault("campaigns", []).append(campaign.model_dump(mode="json"))

    CAMPAIGNS_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CAMPAIGNS_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(campaigns_db, f, indent=2)

    return {
        "status": "SUCCESS",
        "message": f"Campaign '{campaign.title}' activated with bounded budget ₹{campaign.max_budget_inr:,.2f}."
    }