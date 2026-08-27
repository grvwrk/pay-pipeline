import os
import logging
from typing import Dict, Any, Optional
import httpx
from bs4 import BeautifulSoup
from backend.app.config import settings
from backend.app.tools.dispatcher import tool_dispatcher, ToolRiskLevel

logger = logging.getLogger(__name__)


class TavilySearchEngine:
    """
    Tavily AI Search Engine for Agentic Commerce.
    Provides real-time product intelligence without silent fake data injection.
    """

    TAVILY_API_URL = "https://api.tavily.com/search"

    def __init__(self, api_key: Optional[str] = None, timeout: float = 8.0):
        self.api_key = api_key or getattr(settings, "TAVILY_API_KEY", None) or os.getenv("TAVILY_API_KEY")
        self.timeout = timeout
        self.headers = {
            "User-Agent": "pay-pipeline-agent/1.0 (Autonomous Commerce Intelligence Engine)"
        }

    async def asearch(
        self,
        query: str,
        max_results: int = 5,
        search_depth: str = "basic",
        include_answer: bool = True
    ) -> Dict[str, Any]:
        """Async execution of Tavily API with transparent DuckDuckGo fallback."""
        active_key = self.api_key or getattr(settings, "TAVILY_API_KEY", None) or os.getenv("TAVILY_API_KEY")

        if active_key:
            return await self._execute_tavily_api_async(query, active_key, max_results, search_depth, include_answer)

        return await self._execute_fallback_search_async(query, max_results)

    async def _execute_tavily_api_async(
        self,
        query: str,
        api_key: str,
        max_results: int,
        search_depth: str,
        include_answer: bool
    ) -> Dict[str, Any]:
        try:
            payload = {
                "api_key": api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": search_depth,
                "include_answer": include_answer,
                "include_raw_content": False
            }
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.TAVILY_API_URL, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    results = [
                        {
                            "title": r.get("title", ""),
                            "snippet": r.get("content", ""),
                            "url": r.get("url", ""),
                            "score": r.get("score", 1.0)
                        }
                        for r in data.get("results", [])
                    ]
                    return {
                        "provider": "tavily",
                        "query": query,
                        "answer": data.get("answer"),
                        "results": results,
                        "total_results": len(results)
                    }
                else:
                    logger.warning(f"Tavily API returned status {response.status_code}: {response.text}")
        except Exception as e:
            logger.warning(f"Async Tavily API search failed for '{query}': {e}")

        return await self._execute_fallback_search_async(query, max_results)

    async def _execute_fallback_search_async(self, query: str, max_results: int) -> Dict[str, Any]:
        results = []
        try:
            url = "https://html.duckduckgo.com/html/"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            async with httpx.AsyncClient(headers=headers, timeout=self.timeout, follow_redirects=True) as client:
                response = await client.post(url, data={"q": query})
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    links = soup.find_all("div", class_="result")
                    for link in links:
                        if len(results) >= max_results:
                            break
                        snippet_tag = link.find("a", class_="result__snippet")
                        url_tag = link.find("a", class_="result__url")
                        title = link.find("h2", class_="result__title")

                        title_text = title.get_text(strip=True) if title else ""
                        snippet_text = snippet_tag.get_text(strip=True) if snippet_tag else ""
                        href = url_tag.get("href", "") if url_tag else ""

                        if snippet_text or title_text:
                            results.append({
                                "title": title_text or query,
                                "snippet": snippet_text,
                                "url": href,
                                "score": 0.85
                            })
        except Exception as e:
            logger.warning(f"Async Fallback search failed for '{query}': {e}")

        return {
            "provider": "tavily_fallback",
            "query": query,
            "answer": f"Web search completed with {len(results)} result(s)." if results else "No web results found.",
            "results": results,
            "total_results": len(results)
        }

    def search(
        self,
        query: str,
        max_results: int = 5,
        search_depth: str = "basic",
        include_answer: bool = True
    ) -> Dict[str, Any]:
        active_key = self.api_key or getattr(settings, "TAVILY_API_KEY", None) or os.getenv("TAVILY_API_KEY")

        if active_key:
            return self._execute_tavily_api(query, active_key, max_results, search_depth, include_answer)

        return self._execute_fallback_search(query, max_results)

    def _execute_tavily_api(self, query: str, api_key: str, max_results: int, search_depth: str, include_answer: bool) -> Dict[str, Any]:
        try:
            payload = {
                "api_key": api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": search_depth,
                "include_answer": include_answer,
                "include_raw_content": False
            }
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(self.TAVILY_API_URL, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    results = [
                        {"title": r.get("title", ""), "snippet": r.get("content", ""), "url": r.get("url", ""), "score": r.get("score", 1.0)}
                        for r in data.get("results", [])
                    ]
                    return {"provider": "tavily", "query": query, "answer": data.get("answer"), "results": results, "total_results": len(results)}
        except Exception as e:
            logger.warning(f"Tavily API search failed for '{query}': {e}")

        return self._execute_fallback_search(query, max_results)

    def _execute_fallback_search(self, query: str, max_results: int) -> Dict[str, Any]:
        results = []
        try:
            url = "https://html.duckduckgo.com/html/"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            with httpx.Client(headers=headers, timeout=self.timeout, follow_redirects=True) as client:
                response = client.post(url, data={"q": query})
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    for link in soup.find_all("div", class_="result"):
                        if len(results) >= max_results:
                            break
                        snippet_tag = link.find("a", class_="result__snippet")
                        url_tag = link.find("a", class_="result__url")
                        title = link.find("h2", class_="result__title")

                        title_text = title.get_text(strip=True) if title else ""
                        snippet_text = snippet_tag.get_text(strip=True) if snippet_tag else ""
                        href = url_tag.get("href", "") if url_tag else ""

                        if snippet_text or title_text:
                            results.append({"title": title_text or query, "snippet": snippet_text, "url": href, "score": 0.85})
        except Exception as e:
            logger.warning(f"Fallback search failed for '{query}': {e}")

        return {
            "provider": "tavily_fallback",
            "query": query,
            "answer": f"Web search completed with {len(results)} result(s)." if results else "No web results found.",
            "results": results,
            "total_results": len(results)
        }


tavily_search_engine = TavilySearchEngine()


# Tool Registration
async def tavily_search_tool_fn_async(query: str, max_results: int = 5) -> Dict[str, Any]:
    return await tavily_search_engine.asearch(query=query, max_results=max_results)

def tavily_search_tool_fn_sync(query: str, max_results: int = 5) -> Dict[str, Any]:
    return tavily_search_engine.search(query=query, max_results=max_results)


tool_dispatcher.register_tool(
    name="tavily_search",
    description="Search the live web using Tavily AI Search for external product specs, reviews, market prices, and nutritional comparisons.",
    risk_level=ToolRiskLevel.LOW,
    handler=tavily_search_tool_fn_async
)

tool_dispatcher.register_tool(
    name="web_search",
    description="Alias for Tavily AI Search to look up live external product specs and market intelligence.",
    risk_level=ToolRiskLevel.LOW,
    handler=tavily_search_tool_fn_async
)