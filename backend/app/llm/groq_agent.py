import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.config import settings
from backend.app.models.catalog import Product, ProductFilter
from backend.app.tools.read_tools import read_tools
from backend.app.tools.search_tools import tavily_search_engine


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
    web_research: Optional[Dict[str, Any]] = None
    provider: str = "deterministic"


SUPPORTED_INTENTS = [
    "PRODUCT_SEARCH",
    "PRODUCT_DETAILS",
    "PRODUCT_RECOMMENDATION",
    "PRODUCT_COMPARISON",
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
            "description": "Search the merchant's authoritative SQLite product catalog by search keywords, dynamic category, and price ceiling. Returns authentic stock, prices, and specs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keywords or semantic product query"},
                    "category": {"type": ["string", "null"], "description": "Optional category filter"},
                    "max_price": {"type": ["number", "null"], "description": "Maximum price ceiling in INR"},
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
            "description": "Get complete specifications, ratings, and pricing for a specific product SKU from the merchant catalog.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product SKU ID"}
                },
                "required": ["product_id"],
                "additionalProperties": False,
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tavily_search",
            "description": "Search the live web using Tavily AI Search to discover real-time external product specifications, reviews, market prices, and nutritional comparisons.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Web search query for market intelligence or product specs"},
                    "max_results": {"type": "integer", "description": "Number of results to retrieve (default: 5)"}
                },
                "required": ["query"],
                "additionalProperties": False,
            }
        }
    }
]


def _extract_budget_dynamically(text: str) -> Optional[float]:
    """Extract numeric budget constraint dynamically from query text."""
    found = re.search(r"(?:under|below|budget|max|for|upto|within)\s*(?:rs\.?|inr|₹)?\s*(\d[\d,]*)", text, re.IGNORECASE)
    if not found:
        found = re.search(r"(\d[\d,]*)\s*(?:rs|inr|rupees|₹)", text, re.IGNORECASE)
    return float(found.group(1).replace(",", "")) if found else None


class GroqCatalogAgent:
    """
    LLM Multi-Agent Commerce Intelligence & Catalog Adapter.
    Executes dynamic LLM intent classification, Tavily web search, and catalog tool calling.
    """

    def _search(self, args: Dict[str, Any]) -> List[Product]:
        return read_tools.catalog_lookup(ProductFilter(
            query=str(args.get("query", "")),
            category=args.get("category"),
            max_price=args.get("max_price")
        ))

    def route_intent(self, query: str, user_id: str = "user_default_buyer") -> IntentClassificationResult:
        return self.classify_intent(query)

    def classify_intent(self, query: str) -> IntentClassificationResult:
        """
        Dynamically classify commerce intent and extract entities using LLM when available,
        or semantic catalog extraction in offline mode.
        """
        budget = _extract_budget_dynamically(query)
        lower = query.lower()

        # Offline fallback intent determination based on semantic action phrases
        if any(w in lower for w in ("refund", "money back", "return payment")):
            offline_intent = "REFUND"
        elif any(w in lower for w in ("cancel order", "cancel payment", "abort order")):
            offline_intent = "CANCEL_ORDER"
        elif any(w in lower for w in ("order status", "track order", "where is my order", "order_")):
            offline_intent = "ORDER_STATUS"
        elif any(w in lower for w in ("payment status", "payment verified", "pay_")):
            offline_intent = "PAYMENT_STATUS"
        elif any(w in lower for w in ("discount", "coupon", "promo", "promo code", "voucher")):
            offline_intent = "DISCOUNT"
        elif any(w in lower for w in ("upsell", "bundle", "accessory", "complementary", "pair with")):
            offline_intent = "UPSELL"
        elif any(w in lower for w in ("buy", "checkout", "purchase", "place order", "order now")):
            offline_intent = "CHECKOUT"
        elif any(w in lower for w in ("add to cart", "put in cart")):
            offline_intent = "CART_ADD"
        elif any(w in lower for w in ("remove from cart", "delete from cart")):
            offline_intent = "CART_REMOVE"
        elif any(w in lower for w in ("compare", "versus", " vs ")):
            offline_intent = "PRODUCT_COMPARISON"
        elif any(w in lower for w in ("specs", "details", "features", "tell me about")):
            offline_intent = "PRODUCT_DETAILS"
        elif any(w in lower for w in ("recommend", "top choice", "suggest", "best available")):
            offline_intent = "PRODUCT_RECOMMENDATION"
        else:
            offline_intent = "PRODUCT_SEARCH"

        fallback_result = IntentClassificationResult(
            intent=offline_intent,
            confidence=0.90,
            category=None,
            max_price=budget,
            include_bundle=any(w in lower for w in ("bundle", "with rest", "combo", "with mat")),
            entities={"query": query, "max_price": budget},
            provider="deterministic"
        )

        if settings.LLM_PROVIDER != "groq" or not settings.GROQ_API_KEY:
            return fallback_result

        try:
            from groq import Groq
            client = Groq(api_key=settings.GROQ_API_KEY)
            prompt = (
                "You are an expert Intent Router & Entity Extractor for an Agentic Commerce Platform. "
                "Analyze the user's message and classify into exactly one intent from:\n"
                f"{', '.join(SUPPORTED_INTENTS)}\n\n"
                "Extract structured entities:\n"
                "- search_query: cleaned keywords for product catalog lookup or Tavily web search\n"
                "- category: broad product category (string or null)\n"
                "- max_price: maximum INR budget constraint (float or null)\n"
                "- include_bundle: boolean indicating if buyer wants upsell/accessory bundle\n"
                "- sku: explicit SKU ID if specified (string or null)\n"
                "- order_id: order ID if referencing prior order (string or null)\n"
                "- payment_id: payment ID if referencing payment or refund (string or null)\n"
                "- explanation: 1-sentence reasoning for classification\n\n"
                "Output JSON only conforming to the schema."
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
            intent = payload.get("intent", offline_intent)
            if intent not in SUPPORTED_INTENTS:
                intent = offline_intent

            extracted_price = payload.get("max_price")
            price_val = float(extracted_price) if extracted_price is not None else budget

            return IntentClassificationResult(
                intent=intent,
                confidence=float(payload.get("confidence", 0.95)),
                category=payload.get("category"),
                max_price=price_val,
                include_bundle=bool(payload.get("include_bundle", fallback_result.include_bundle)),
                sku=payload.get("sku"),
                order_id=payload.get("order_id"),
                payment_id=payload.get("payment_id"),
                entities=payload,
                provider=f"groq:{settings.GROQ_MODEL}",
                explanation=payload.get("explanation")
            )
        except Exception:
            return fallback_result

    def run(self, query: str, category: Optional[str] = None, max_price: Optional[float] = None) -> CatalogAgentResult:
        """
        Execute multi-agent catalog discovery and market intelligence reasoning.
        Calls Tavily Search when external market intelligence or comparison is needed.
        """
        fallback_products = self._search({"query": query, "category": category, "max_price": max_price})
        fallback = lambda: CatalogAgentResult(products=fallback_products, provider="deterministic")

        if settings.LLM_PROVIDER != "groq" or not settings.GROQ_API_KEY:
            return fallback()

        try:
            from groq import Groq
            client = Groq(api_key=settings.GROQ_API_KEY)
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an AI Commerce & Market Research Agent. "
                        "You have access to:\n"
                        "1. `search_catalog`: Search internal merchant catalog for authentic products, stock, and prices.\n"
                        "2. `get_product_details`: Retrieve exact SKU details.\n"
                        "3. `tavily_search`: Search the live web via Tavily to research external product specs, reviews, nutritional data, or market comparisons.\n"
                        "Never invent merchant prices or inventory; always rely on `search_catalog` for purchases."
                    )
                },
                {"role": "user", "content": f"User Request: {query}\nCategory Hint: {category or 'None'}\nMax Budget INR: {max_price or 'None'}"}
            ]
            products: List[Product] = []
            trace: List[Dict[str, Any]] = []
            web_results: Optional[Dict[str, Any]] = None

            for _ in range(settings.GROQ_MAX_TOOL_ROUNDS):
                response = client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=messages,
                    tools=CATALOG_TOOLS,
                    tool_choice="auto"
                )
                msg = response.choices[0].message
                if not msg.tool_calls:
                    return CatalogAgentResult(
                        products=products or fallback_products,
                        summary=msg.content,
                        tool_calls=trace,
                        web_research=web_results,
                        provider=f"groq:{settings.GROQ_MODEL}"
                    )

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
                    elif fn_name == "tavily_search":
                        web_results = tavily_search_engine.search(query=args.get("query", query))
                        messages.append({
                            "role": "tool",
                            "tool_call_id": call.id,
                            "name": fn_name,
                            "content": json.dumps(web_results)
                        })

            return CatalogAgentResult(
                products=products or fallback_products,
                summary="Completed catalog discovery and market intelligence analysis.",
                tool_calls=trace,
                web_research=web_results,
                provider=f"groq:{settings.GROQ_MODEL}"
            )
        except Exception:
            return fallback()


groq_catalog_agent = GroqCatalogAgent()
