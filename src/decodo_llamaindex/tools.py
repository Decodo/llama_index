"""
Decodo LlamaIndex Tool Spec
============================

A :class:`~llama_index.core.tools.BaseToolSpec` that exposes Decodo's web
scraping and search capabilities as callable tools for LlamaIndex agents
(e.g. OpenAI-function-calling agents, ReAct agents).

Environment variable
--------------------
DECODO_API_TOKEN : str
    Your Decodo API token.  Can be passed explicitly to the constructor.

Usage
-----
>>> from llama_index.core.agent import ReActAgent
>>> from llama_index.llms.openai import OpenAI
>>> from decodo_llamaindex import DecodoToolSpec
>>>
>>> spec = DecodoToolSpec()
>>> tools = spec.to_tool_list()
>>> agent = ReActAgent.from_tools(tools, llm=OpenAI(model="gpt-4o"), verbose=True)
>>> response = agent.chat("Summarise the homepage of https://news.ycombinator.com")
>>> print(response)
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx
from llama_index.core.tools.tool_spec.base import BaseToolSpec

# ---------------------------------------------------------------------------
# Constants (mirrored from readers to keep this module self-contained)
# ---------------------------------------------------------------------------

_API_URL = "https://scraper-api.decodo.com/v2/scrape"
_DEFAULT_TIMEOUT = 60.0

_SEARCH_ENGINE_TARGETS: Dict[str, str] = {
    "google": "google_search",
    "amazon": "amazon_search",
    "reddit": "reddit_subreddit",
}


# ---------------------------------------------------------------------------
# DecodoToolSpec
# ---------------------------------------------------------------------------


class DecodoToolSpec(BaseToolSpec):
    """
    LlamaIndex tool specification wrapping the Decodo Web Scraping API.

    Registers two tools that can be handed to any LlamaIndex agent:

    ``scrape_url(url)``
        Fetch and return the full rendered content of any web page as
        markdown text.

    ``search(query, engine)``
        Run a query against Google Search, Amazon, or Reddit and return
        the raw result content.

    Parameters
    ----------
    api_token : str, optional
        Decodo API token.  Falls back to the ``DECODO_API_TOKEN`` environment
        variable.
    extra_payload : dict, optional
        Extra key/value pairs merged into every API request body, e.g.
        ``{"geo": "us"}`` to pin geolocation.
    """

    # Names exposed to the agent framework.
    spec_functions: List[str] = ["scrape_url", "search"]

    def __init__(
        self,
        api_token: Optional[str] = None,
        extra_payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.api_token: str = api_token or os.environ.get("DECODO_API_TOKEN", "")
        if not self.api_token:
            raise ValueError(
                "A Decodo API token is required.  Pass api_token= or set the "
                "DECODO_API_TOKEN environment variable."
            )
        self.extra_payload: Dict[str, Any] = extra_payload or {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST *payload* to the Decodo API and return parsed JSON."""
        with httpx.Client(
            headers={"Authorization": f"Basic {self.api_token}"},
            timeout=_DEFAULT_TIMEOUT,
        ) as client:
            response = client.post(_API_URL, json={**payload, **self.extra_payload})
            response.raise_for_status()
            data: Dict[str, Any] = response.json()
            if "results" not in data:
                raise ValueError(
                    f"Unexpected Decodo API response — missing 'results': {data}"
                )
            return data

    @staticmethod
    def _extract_content(data: Dict[str, Any]) -> str:
        """Concatenate content from all result entries."""
        parts: List[str] = []
        for result in data.get("results", []):
            content = result.get("content", "").strip()
            if content:
                parts.append(content)
        return "\n\n---\n\n".join(parts) if parts else "(no content returned)"

    # ------------------------------------------------------------------
    # Tool functions
    # ------------------------------------------------------------------

    def scrape_url(self, url: str) -> str:
        """
        Scrape a web page and return its content as markdown text.

        Use this tool whenever you need to read the current content of a
        specific web page, article, documentation page, or any URL.

        Parameters
        ----------
        url : str
            The fully-qualified URL to scrape, e.g.
            ``"https://news.ycombinator.com"``.

        Returns
        -------
        str
            The rendered page content in markdown format, or an error
            description if the page could not be fetched.
        """
        try:
            data = self._post({"target": "universal", "url": url})
            return self._extract_content(data)
        except httpx.HTTPStatusError as exc:
            return (
                f"[Decodo scrape error] HTTP {exc.response.status_code} "
                f"while fetching {url}: {exc}"
            )
        except Exception as exc:  # noqa: BLE001
            return f"[Decodo scrape error] {exc}"

    def search(self, query: str, engine: str = "google") -> str:
        """
        Search the web and return results as text.

        Use this tool to find up-to-date information, news, product listings,
        or community discussions without knowing a specific URL in advance.

        Parameters
        ----------
        query : str
            The search query or keywords, e.g. ``"Python async best practices"``.
        engine : str
            Search engine to use.  One of:

            * ``"google"``  — Google Search (default)
            * ``"amazon"``  — Amazon product listings
            * ``"reddit"``  — Reddit posts / subreddits

        Returns
        -------
        str
            Raw search result content in markdown format, or an error
            description if the request failed.
        """
        engine_lower = engine.lower()
        target = _SEARCH_ENGINE_TARGETS.get(engine_lower)
        if target is None:
            supported = ", ".join(f'"{k}"' for k in _SEARCH_ENGINE_TARGETS)
            return (
                f"[Decodo tool error] Unsupported engine {engine!r}. "
                f"Supported engines: {supported}."
            )

        try:
            data = self._post({"target": target, "url": query})
            return self._extract_content(data)
        except httpx.HTTPStatusError as exc:
            return (
                f"[Decodo search error] HTTP {exc.response.status_code} "
                f"for query={query!r} engine={engine!r}: {exc}"
            )
        except Exception as exc:  # noqa: BLE001
            return f"[Decodo search error] {exc}"
