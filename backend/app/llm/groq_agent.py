import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.config import settings
from backend.app.models.catalog import Product, ProductFilter
from backend.app.tools.read_tools import read_tools


class IntentClassificationResult(BaseModel):
    intent: str = "PRODUCT_SEARCH"
    confidence: float = 1.0
    entities: Dict[str, Any] = Field(default_factory=dict)
    category: Optional[str] = None
    max_price: Optional[float] = None
    include_bundle: bool = False
    sku: Optional[str] = None
    order_id: Optional[str] = None
    payment_id: Optional[str] = None
    provider: str = "deterministic"
    explanation: Optional[str] = None


@dataclass
class CatalogAgentResult:
    products: List[Product]
    summary: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    provider: str = "deterministic"


SUPPORTED_INTENTS = [
    "PRODUCT_SEARCH",
    "PRODUCT_DETAILS",
    "PRODUCT_RECOMMENDATION",
    "CART_ADD",
    "CART_REMOVE",
    "CART_UPDATE",
    "UPSELL",
    "CROSS_SELL",
    "DISCOUNT",
    "CHECKOUT",
    "PAYMENT",
    "ORDER_STATUS",
    "PAYMENT_STATUS",
    "REFUND",
    "CANCEL_ORDER",
    "GENERAL_COMMERCE_QUERY"
]

CATALOG_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_catalog",
            "description": "Search the merchant's authoritative product catalog by keyword, category, and budget. Never invent prices or inventory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "category": {"type": ["string", "null"]},
                    "max_price": {"type": ["number", "null"], "description": "Maximum INR price limit"},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_details",
            "description": "Get complete specifications and pricing for a specific product SKU.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string"}
                },
                "required": ["product_id"],
                "additionalProperties": False,
            }
        }
    }
]


def _infer_category(text: str) -> Optional[str]:
    categories = {
        "nutrition_and_fitness": ("peanut", "protein", "nutrition", "chia", "shaker", "gym", "diet", "whey", "snack", "supplement"),
        "running_shoes": ("running", "shoes", "shoe", "sneaker", "pegasus", "marathon", "socks"),
        "mechanical_keyboards": ("keyboard", "keychron", "typing", "switch", "rk84", "ducky"),
        "ergonomics": ("mouse", "mice", "vertical", "ergonomic", "wrist"),
        "audio_equipment": ("headphone", "headset", "audio", "anc", "sound"),
        "smartphones": ("phone", "smartphone", "mobile", "android", "iphone", "pixel", "galaxy"),
        "developer_gear": ("screenbar", "dock", "hub", "usbc"),
        "workspace_accessories": ("desk", "deskmat", "stand", "cable", "mat"),
    }
    return next((name for name, words in categories.items() if any(word in text for word in words)), None)


def _infer_budget(text: str) -> Optional[float]:
    found = re.search(r"(?:under|below|budget|max|for)\s*(?:rs\.?|inr|₹)?\s*(\d[\d,]*)", text)
    if not found:
        found = re.search(r"(\d[\d,]*)\s*(?:rs|inr|rupees|₹)", text)
    return float(found.group(1).replace(",", "")) if found else None


class GroqCatalogAgent:
    """
    Groq GPT-OSS-20B Agentic Commerce Adapter.
    Performs 16-intent classification and tool calling with deterministic offline fallbacks.
    """

    def _search(self, args: Dict[str, Any]) -> List[Product]:
        return read_tools.catalog_lookup(ProductFilter(
            query=str(args.get("query", "")),
            category=args.get("category"),
            max_price=args.get("max_price")
        ))

    def route_intent(self, query: str, user_id: str = "user_default_buyer") -> IntentClassificationResult:
        lower = query.lower().strip()
        category = _infer_category(lower)
        max_price = _infer_budget(lower)
        include_bundle = any(w in lower for w in ("bundle", "both", "wrist rest", "charger", "case", "cable", "accessories", "add companion"))

        # Deterministic heuristic classifier baseline
        if any(w in lower for w in ("refund", "money back", "return payment")):
            fallback_intent = "REFUND"
        elif any(w in lower for w in ("cancel order", "cancel payment", "abort order")):
            fallback_intent = "CANCEL_ORDER"
        elif any(w in lower for w in ("order status", "track order", "where is my order", "order_")):
            fallback_intent = "ORDER_STATUS"
        elif any(w in lower for w in ("payment status", "payment verified", "pay_")):
            fallback_intent = "PAYMENT_STATUS"
        elif any(w in lower for w in ("discount", "coupon", "promo", "promo code", "voucher")):
            fallback_intent = "DISCOUNT"
        elif any(w in lower for w in ("upsell", "bundle", "accessory", "complementary", "pair with")):
            fallback_intent = "UPSELL"
        elif any(w in lower for w in ("buy", "checkout", "purchase", "place order", "order now", "get me", "i'll take")):
            fallback_intent = "CHECKOUT"
        elif any(w in lower for w in ("add to cart", "put in cart", "add item")):
            fallback_intent = "CART_ADD"
        elif any(w in lower for w in ("remove from cart", "delete from cart")):
            fallback_intent = "CART_REMOVE"
        elif any(w in lower for w in ("specs", "details", "features", "tell me about", "what is")):
            fallback_intent = "PRODUCT_DETAILS"
        elif any(w in lower for w in ("recommend", "best", "top choice", "suggest")):
            fallback_intent = "PRODUCT_RECOMMENDATION"
        else:
            fallback_intent = "PRODUCT_SEARCH"

        fallback_result = IntentClassificationResult(
            intent=fallback_intent,
            confidence=0.92,
            category=category,
            max_price=max_price,
            include_bundle=include_bundle,
            entities={"query": query, "category": category, "max_price": max_price},
            provider="deterministic"
        )

        if settings.LLM_PROVIDER != "groq" or not settings.GROQ_API_KEY:
            return fallback_result

        try:
            from groq import Groq
            client = Groq(api_key=settings.GROQ_API_KEY)
            prompt = (
                "You are an Intent Router for an agentic commerce system. "
                "Classify the user's message into exactly one of these intents:\n"
                f"{', '.join(SUPPORTED_INTENTS)}\n"
                "Extract any entities: category (string or null), max_price (float or null), "
                "sku (string or null), include_bundle (bool), order_id (string or null), payment_id (string or null).\n"
                "Return JSON ONLY matching the schema: {intent, confidence, category, max_price, include_bundle, sku, order_id, payment_id, explanation}."
            )
            response = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.0
            )
            payload = json.loads(response.choices[0].message.content or "{}")
            intent = payload.get("intent", fallback_intent)
            if intent not in SUPPORTED_INTENTS:
                intent = fallback_intent

            return IntentClassificationResult(
                intent=intent,
                confidence=float(payload.get("confidence", 0.95)),
                category=payload.get("category") or category,
                max_price=float(payload["max_price"]) if payload.get("max_price") is not None else max_price,
                include_bundle=bool(payload.get("include_bundle", include_bundle)),
                sku=payload.get("sku"),
                order_id=payload.get("order_id"),
                payment_id=payload.get("payment_id"),
                provider=f"groq:{settings.GROQ_MODEL}",
                explanation=payload.get("explanation")
            )
        except Exception:
            return fallback_result

    def run(self, query: str, category: Optional[str], max_price: Optional[float]) -> CatalogAgentResult:
        fallback = lambda: CatalogAgentResult(products=self._search({"query": query, "category": category, "max_price": max_price}))
        if settings.LLM_PROVIDER != "groq" or not settings.GROQ_API_KEY:
            return fallback()

        try:
            from groq import Groq
            client = Groq(api_key=settings.GROQ_API_KEY)
            messages = [
                {"role": "system", "content": "You are a catalog assistant. Use search_catalog to find products from the merchant catalog. Never invent prices or inventory."},
                {"role": "user", "content": f"Find products for: {query}. Category hint: {category or 'none'}. Max price INR: {max_price or 'none'}."}
            ]
            products: List[Product] = []
            trace: List[Dict[str, Any]] = []

            for _ in range(settings.GROQ_MAX_TOOL_ROUNDS):
                response = client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=messages,
                    tools=CATALOG_TOOLS,
                    tool_choice="auto"
                )
                msg = response.choices[0].message
                if not msg.tool_calls:
                    return CatalogAgentResult(products=products or self._search({"query": query, "category": category, "max_price": max_price}),
                                              summary=msg.content, tool_calls=trace, provider=f"groq:{settings.GROQ_MODEL}")

                for call in msg.tool_calls:
                    fn_name = call.function.name
                    args = json.loads(call.function.arguments or "{}")
                    trace.append({"tool": fn_name, "arguments": args})
                    if fn_name == "search_catalog":
                        products = self._search(args)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": call.id,
                            "name": fn_name,
                            "content": json.dumps([p.model_dump() for p in products[:5]])
                        })
                    elif fn_name == "get_product_details":
                        p = read_tools.get_product(args.get("product_id", ""))
                        messages.append({
                            "role": "tool",
                            "tool_call_id": call.id,
                            "name": fn_name,
                            "content": p.model_dump_json() if p else "{}"
                        })

            return CatalogAgentResult(products=products, summary="Completed catalog search.", tool_calls=trace, provider=f"groq:{settings.GROQ_MODEL}")
        except Exception:
            return fallback()


groq_catalog_agent = GroqCatalogAgent()
