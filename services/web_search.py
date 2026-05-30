from __future__ import annotations

import logging

from ddgs import DDGS

logger = logging.getLogger(__name__)


def search_web(query: str, max_results: int = 3) -> list[dict[str, str]]:
    """Search DuckDuckGo and return list of {title, link, snippet}."""
    try:
        ddgs = DDGS()
        results = list(ddgs.text(query, max_results=max_results))
        return [
            {
                "title": r.get("title", ""),
                "link": r.get("link", ""),
                "snippet": r.get("body", ""),
            }
            for r in results
        ]
    except Exception:
        logger.exception("web search failed for: %s", query)
        return []


def weather_search(city: str) -> list[dict[str, str]]:
    """Search web for weather info about a city."""
    return search_web(f"погода {city} сегодня", max_results=3)
