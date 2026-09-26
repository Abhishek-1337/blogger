"""Free web search tool (DuckDuckGo via ddgs). No API key needed."""

from ddgs import DDGS


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web and return [{title, url, snippet}]."""
    results: list[dict] = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(
                    {
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    }
                )
    except Exception as e:
        results.append({"title": "search error", "url": "", "snippet": str(e)})
    return results
