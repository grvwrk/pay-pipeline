import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.config import settings
from backend.app.models.catalog import Product, ProductFilter
from backend.app.tools.read_tools import read_tools
from backend.app.tools.search_tools import tavily_search_engine

logger = logging.getLogger(__name__)


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
    provider: str = "groq"
    explanation: Optional[str] = None


@dataclass
class CatalogAgentResult:
    products: List[Product]
    summary: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    web_research: Optional[Dict[str, Any]] = None
    provider: str = "groq"


SUPPORTED_INTENTS = [
    "PRODUCT_SEARCH", "PRODUCT_DETAILS", "PRODUCT_RECOMMENDATION",
    "PRODUCT_COMPARISON", "CART_ADD", "CART_REMOVE", "CART_UPDATE",
    "UPSELL", "CROSS_SELL", "DISCOUNT", "CHECKOUT", "PAYMENT",
    "ORDER_STATUS", "PAYMENT_STATUS", "REFUND", "CANCEL_ORDER",
    "GENERAL_COMMERCE_QUERY"
]

CATALOG_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_catalog",
            "description": "Search internal product catalog by search keywords, category, and price ceiling.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keywords or product query"},
                    "category": {"type": "string", "description": "Optional category filter"},
                    "max_price": {"type": "number", "description": "Maximum price ceiling in INR"},
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
            "description": "Get complete specifications, ratings, and pricing for a specific product SKU.",
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
            "description": "Search external web via Tavily AI for external specs, reviews, and market comparisons.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Web search query"},
                    "max_results": {"type": "integer", "description": "Number of results (default: 5)"}
                },
                "required": ["query"],
                "additionalProperties": False,
            }
        }
    }
]


class GroqCatalogAgent:
    """Streamlined LLM Agent & Router delegating entity extraction and routing directly to Groq."""

    def _clean_json_response(self, raw_content: str) -> str:
        """Strip markdown code fences from LLM responses."""
        cleaned = raw_content.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        return cleaned

    def route_intent(self, query: str, user_id: str = "user_default_buyer") -> IntentClassificationResult:
        return self.classify_intent(query)

    def classify_intent(self, query: str) -> IntentClassificationResult:
        """Classify user query and extract entities via Groq JSON mode."""
        if not settings.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not set. Groq LLM provider is required for intent classification.")

        try:
            from groq import Groq
        except ImportError as e:
            raise RuntimeError("groq python library is not installed. Groq LLM provider is required.") from e
        try:
            client = Groq(api_key=settings.GROQ_API_KEY)
            prompt = (
                "You are an Intent Router & Entity Extractor for an E-commerce platform.\n"
                f"Classify user input into exactly one intent from: {', '.join(SUPPORTED_INTENTS)}\n\n"
                "Extract entities into JSON:\n"
                "- intent: string\n"
                "- category: string or null\n"
                "- max_price: extracted budget constraint as float in INR or null\n"
                "- include_bundle: boolean\n"
                "- sku: string or null\n"
                "- order_id: string or null\n"
                "- payment_id: string or null\n"
                "- explanation: short 1-sentence reasoning"
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
            
            raw_content = response.choices[0].message.content or "{}"
            payload = json.loads(self._clean_json_response(raw_content))
            
            # Validate extracted intent against supported intents
            extracted_intent = payload.get("intent", "PRODUCT_SEARCH")
            if extracted_intent not in SUPPORTED_INTENTS:
                logger.warning("Extracted intent '%s' not in SUPPORTED_INTENTS. Defaulting to PRODUCT_SEARCH.", extracted_intent)
                extracted_intent = "PRODUCT_SEARCH"

            raw_max_price = payload.get("max_price")
            max_price = float(raw_max_price) if raw_max_price is not None else None

            return IntentClassificationResult(
                intent=extracted_intent,
                confidence=float(payload.get("confidence", 0.95)),
                category=payload.get("category"),
                max_price=max_price,
                include_bundle=bool(payload.get("include_bundle", False)),
                sku=payload.get("sku"),
                order_id=payload.get("order_id"),
                payment_id=payload.get("payment_id"),
                entities=payload,
                provider=f"groq:{settings.GROQ_MODEL}",
                explanation=payload.get("explanation")
            )
        except Exception as exc:
            logger.error("Intent classification failed for query '%s': %s", query, exc, exc_info=True)
            raise

    def run(self, query: str, category: Optional[str] = None, max_price: Optional[float] = None) -> CatalogAgentResult:
        """Execute multi-turn tool calling using Groq tool dispatches."""
        if not settings.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not set. Groq LLM provider is required for catalog agent search.")

        try:
            from groq import Groq
        except ImportError as e:
            raise RuntimeError("groq python library is not installed. Groq LLM provider is required.") from e
        try:
            client = Groq(api_key=settings.GROQ_API_KEY)
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an AI Commerce Agent. "
                        "Use `search_catalog` to find internal stock and prices, "
                        "`get_product_details` for exact SKU specs, and "
                        "`tavily_search` for web research/comparisons."
                    )
                },
                {"role": "user", "content": f"User Request: {query}\nCategory Hint: {category}\nMax Price: {max_price}"}
            ]
            
            products_map: Dict[str, Product] = {}
            trace: List[Dict[str, Any]] = []
            web_results: Optional[Dict[str, Any]] = None

            for round_num in range(settings.GROQ_MAX_TOOL_ROUNDS):
                response = client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=messages,
                    tools=CATALOG_TOOLS,
                    tool_choice="auto"
                )
                msg = response.choices[0].message
                if not msg.tool_calls:
                    return CatalogAgentResult(
                        products=list(products_map.values()),
                        summary=msg.content,
                        tool_calls=trace,
                        web_research=web_results,
                        provider=f"groq:{settings.GROQ_MODEL}"
                    )

                # Format assistant message for continuation payload
                messages.append({
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in msg.tool_calls
                    ]
                })

                for call in msg.tool_calls:
                    fn_name = call.function.name
                    try:
                        args = json.loads(call.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}

                    trace.append({"tool": fn_name, "arguments": args})

                    try:
                        if fn_name == "search_catalog":
                            search_max_price = args.get("max_price")
                            parsed_max_price = float(search_max_price) if search_max_price is not None else max_price

                            found_products = read_tools.catalog_lookup(ProductFilter(
                                query=str(args.get("query", query)),
                                category=args.get("category") or category,
                                max_price=parsed_max_price
                            ))
                            for p in found_products:
                                products_map[p.sku] = p

                            messages.append({
                                "role": "tool",
                                "tool_call_id": call.id,
                                "name": fn_name,
                                "content": json.dumps([p.model_dump() for p in found_products[:5]])
                            })

                        elif fn_name == "get_product_details":
                            sku = str(args.get("product_id", ""))
                            p = read_tools.get_product(sku)
                            if p:
                                products_map[p.sku] = p

                            messages.append({
                                "role": "tool",
                                "tool_call_id": call.id,
                                "name": fn_name,
                                "content": p.model_dump_json() if p else "{}"
                            })

                        elif fn_name == "tavily_search":
                            search_q = str(args.get("query", query))
                            web_results = tavily_search_engine.search(query=search_q)
                            messages.append({
                                "role": "tool",
                                "tool_call_id": call.id,
                                "name": fn_name,
                                "content": json.dumps(web_results or {})
                            })
                    except Exception as tool_err:
                        logger.error("Tool execution failed for '%s': %s", fn_name, tool_err, exc_info=True)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": call.id,
                            "name": fn_name,
                            "content": json.dumps({"error": f"Tool execution failed: {str(tool_err)}"})
                        })

            return CatalogAgentResult(
                products=list(products_map.values()),
                summary="Completed discovery.",
                tool_calls=trace,
                web_research=web_results,
                provider=f"groq:{settings.GROQ_MODEL}"
            )

        except Exception as exc:
            logger.error("Catalog agent run loop crashed for query '%s': %s", query, exc, exc_info=True)
            raise


groq_catalog_agent = GroqCatalogAgent()