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
>>> import asyncio
>>> from llama_index.core.agent.workflow import ReActAgent
>>> from llama_index.llms.openai import OpenAI
>>> from decodo_llamaindex import DecodoToolSpec
>>>
>>> spec = DecodoToolSpec()
>>> agent = ReActAgent(tools=spec.to_tool_list(), llm=OpenAI(model="gpt-4o"))
>>>
>>> async def main():
...     response = await agent.run("Summarise the homepage of https://news.ycombinator.com")
...     print(response)
>>>
>>> asyncio.run(main())
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx
from llama_index.core.tools.tool_spec.base import BaseToolSpec

# ---------------------------------------------------------------------------
# Constants (mirrored from readers to keep this module self-contained)
# ---------------------------------------------------------------------------

_V2_ENDPOINT = "https://scraper-api.decodo.com/v2/scrape"
_UNIFIED_ENDPOINT = "https://scraper-api.decodo.com/unified/v1/scrape"
_DEFAULT_TIMEOUT = 60.0
_INTEGRATION_HEADER = "llamaindex-python"
_REDDIT_SITE_FILTER = "site:reddit.com"


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
    spec_functions: List[str] = ["scrape_url", "search_web", "search_amazon", "search_reddit"]

    def __init__(
        self,
        api_token: Optional[str] = None,
        auth_mode: str = "basic",
        extra_payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.api_token: str = api_token or os.environ.get("DECODO_API_TOKEN", "")
        if not self.api_token:
            raise ValueError(
                "A Decodo API token is required.  Pass api_token= or set the "
                "DECODO_API_TOKEN environment variable."
            )
        if auth_mode not in ("basic", "token"):
            raise ValueError(
                f"auth_mode must be 'basic' or 'token', got {auth_mode!r}."
            )
        self.auth_mode: str = auth_mode
        self._endpoint: str = _UNIFIED_ENDPOINT if auth_mode == "token" else _V2_ENDPOINT
        self.extra_payload: Dict[str, Any] = extra_payload or {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST *payload* to the Decodo API and return parsed JSON."""
        scheme = "Bearer" if self.auth_mode == "token" else "Basic"
        with httpx.Client(
            headers={
                "Authorization": f"{scheme} {self.api_token}",
                "x-integration": _INTEGRATION_HEADER,
            },
            timeout=_DEFAULT_TIMEOUT,
        ) as client:
            response = client.post(self._endpoint, json={**payload, **self.extra_payload})
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

    @staticmethod
    def _results_to_list(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert raw API response into a list of result dicts."""
        out: List[Dict[str, Any]] = []
        for result in data.get("results", []):
            out.append(
                {
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "status_code": result.get("status_code", 0),
                }
            )
        return out

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
            data = self._post({"target": "universal", "url": url, "markdown": True})
            return self._extract_content(data)
        except httpx.HTTPStatusError as exc:
            return (
                f"[Decodo scrape error] HTTP {exc.response.status_code} "
                f"while fetching {url}: {exc}"
            )
        except Exception as exc:  # noqa: BLE001
            return f"[Decodo scrape error] {exc}"

    def search_web(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search Google and return a list of results.

        Use this tool to find up-to-date information without knowing a
        specific URL in advance.

        Parameters
        ----------
        query : str
            The search query or keywords.
        num_results : int
            Maximum number of results to return.  Default is 10.

        Returns
        -------
        list
            Each item is a dict with keys ``url``, ``content``, and
            ``status_code``.
        """
        data = self._post({"target": "google_search", "query": query, "limit": num_results, "markdown": True})
        return self._results_to_list(data)

    def search_amazon(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search Amazon product listings and return results.

        Use this tool to find product details, prices, and reviews on Amazon.

        Parameters
        ----------
        query : str
            The product search query.
        num_results : int
            Maximum number of results to return.  Default is 10.

        Returns
        -------
        list
            Each item is a dict with keys ``url``, ``content``, and
            ``status_code``.
        """
        data = self._post({"target": "amazon_search", "query": query, "limit": num_results, "markdown": True})
        return self._results_to_list(data)

    def search_reddit(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search Reddit for posts and discussions matching *query*.

        Uses Google Search with a ``site:reddit.com`` filter to find
        relevant Reddit content.

        Parameters
        ----------
        query : str
            The search query.
        num_results : int
            Maximum number of results to return.  Default is 10.

        Returns
        -------
        list
            Each item is a dict with keys ``url``, ``content``, and
            ``status_code``.
        """
        reddit_query = f"{_REDDIT_SITE_FILTER} {query}"
        data = self._post({"target": "google_search", "query": reddit_query, "limit": num_results, "markdown": True})
        return self._results_to_list(data)
