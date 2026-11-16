import logging
from typing import Optional

import requests
import trafilatura
from ddgs import DDGS
from ddgs.exceptions import DDGSException

# Page text is fed straight to the LLM, so keep it short enough for a small local model's context
MAX_FETCH_CHARS = 8000
MAX_SEARCH_RESULTS = 10
FETCH_TIMEOUT_S = 15
USER_AGENT = "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"


def web_search(query: str, max_results: Optional[int] = None) -> str:
    """
    Performs a web search.

    :param query: The query to search for
    :param max_results: The maximum number of results to return (default: 3)
    """
    # DuckDuckGo's free metasearch, which needs no API key
    max_results = max(1, min(int(max_results or 3), MAX_SEARCH_RESULTS))
    try:
        results = DDGS().text(query, max_results=max_results)
    except DDGSException as e:
        # ddgs raises rather than returning an empty list, so tell the LLM plainly instead of handing it a traceback
        logging.info("Web search for %r found nothing: %s", query, e)
        results = []
    if not results:
        return "No results found. Try a shorter or simpler query."
    return "\n\n".join(
        f"{r.get('title', '')}\n{r.get('href', '')}\n{r.get('body', '')}" for r in results
    )


def web_fetch(url: str) -> str:
    """
    Fetches the content of a web page for the provided URL.

    :param url: The URL to fetch
    """
    # Only the page's main text is kept, without the menus, ads and markup
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=FETCH_TIMEOUT_S)
    if response.status_code >= 400:
        # Many big sites refuse anything that isn't a real browser, which isn't worth a traceback
        logging.info("web_fetch got HTTP %d from %s", response.status_code, url)
        return f"That site refused the request (HTTP {response.status_code}). Try a different result."
    text = trafilatura.extract(response.text, url=url, include_comments=False, include_tables=True)
    if not text:
        logging.info("trafilatura found no main text at %s", url)
        return "Could not find any readable text on that page."
    if len(text) > MAX_FETCH_CHARS:
        text = text[:MAX_FETCH_CHARS] + "\n[truncated]"
    return text
