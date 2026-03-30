"""Web search via DuckDuckGo for market research."""


async def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web using DuckDuckGo. Returns list of {title, url, snippet}."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return [{"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")} for r in results]
    except ImportError:
        return [{"title": "duckduckgo-search not installed", "url": "", "snippet": "pip install duckduckgo-search"}]
    except Exception as e:
        return [{"title": f"Search error: {e}", "url": "", "snippet": ""}]


def format_search_results(results: list[dict]) -> str:
    """Format search results as text for LLM context."""
    parts = ["=== Результаты веб-поиска ==="]
    for i, r in enumerate(results, 1):
        parts.append(f"\n{i}. {r['title']}\n   URL: {r['url']}\n   {r['snippet']}")
    return "\n".join(parts)
