"""
Decodo Tool Spec for LlamaIndex
================================

A :class:`~llama_index.core.tools.BaseToolSpec` that exposes Decodo's web
scraping and search capabilities as callable tools for LlamaIndex agents.

Environment variable
--------------------
DECODO_API_TOKEN : str
    Your Decodo API token.  Can be passed explicitly to the constructor.

Usage
-----
>>> from llama_index.tools.decodo import DecodoToolSpec
>>> spec = DecodoToolSpec(api_token="your-token")
>>> tools = spec.to_tool_list()
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx
from llama_index.core.tools.tool_spec.base import BaseToolSpec

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_V2_ENDPOINT = "https://scraper-api.decodo.com/v2/scrape"
_UNIFIED_ENDPOINT = "https://scraper-api.decodo.com/unified/v1/scrape"
_DEFAULT_TIMEOUT = 180.0
_INTEGRATION_HEADER = "llamaindex"


# ---------------------------------------------------------------------------
# DecodoToolSpec
# ---------------------------------------------------------------------------


class DecodoToolSpec(BaseToolSpec):
    """
    LlamaIndex tool specification wrapping the Decodo Web Scraping API.

    Exposes four tools that can be handed to any LlamaIndex agent:

    ``scrape_url(url)``
        Fetch and return the full rendered content of a web page as markdown.

    ``search_web(query, num_results)``
        Run a Google search and return a list of results.

    ``search_amazon(query, num_results)``
        Search Amazon product listings and return results.

    ``search_reddit(query, num_results)``
        Search Reddit via Google with site:reddit.com filter.

    Parameters
    ----------
    api_token : str, optional
        Decodo API token.  Falls back to the ``DECODO_API_TOKEN`` environment
        variable.
    auth_mode : str
        ``"basic"`` (default) — base64-encode ``username:password`` and POST
        to ``/v2/scrape``.
        ``"token"`` — use the token as-is and POST to ``/unified/v1/scrape``.
    timeout : float
        HTTP request timeout in seconds.  Default is 180.
    """

    spec_functions: List[str] = [
        "scrape_url",
        "search_web",
        "search_amazon",
        "search_reddit",
    ]

    def __init__(
        self,
        api_token: Optional[str] = None,
        auth_mode: str = "basic",
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        token = api_token or os.environ.get("DECODO_API_TOKEN", "")
        if not token:
            raise ValueError(
                "A Decodo API token is required.  Pass api_token= or set the "
                "DECODO_API_TOKEN environment variable."
            )

        if auth_mode not in ("basic", "token"):
            raise ValueError(
                f"auth_mode must be 'basic' or 'token', got {auth_mode!r}."
            )

        self._auth_mode = auth_mode
        self._timeout = timeout

        if auth_mode == "basic":
            # Token is already a base64-encoded "username:password" credential.
            # Pass it through directly — same as the /v2/scrape Authorization header.
            self._auth_value = token
            self._endpoint = _V2_ENDPOINT
        else:
            self._auth_value = token
            self._endpoint = _UNIFIED_ENDPOINT

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_api(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST *payload* to the appropriate Decodo endpoint and return JSON."""
        scheme = "Bearer" if self._auth_mode == "token" else "Basic"
        headers = {
            "Authorization": f"{scheme} {self._auth_value}",
            "x-integration": _INTEGRATION_HEADER,
        }
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(self._endpoint, json=payload, headers=headers)
            if response.status_code >= 400:
                raise RuntimeError(
                    f"Decodo API error {response.status_code}: {response.text}"
                )
            return response.json()

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

    @staticmethod
    def _results_to_text(data: Dict[str, Any]) -> str:
        """Concatenate content from all result entries into a single string."""
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
            The fully-qualified URL to scrape.

        Returns
        -------
        str
            The rendered page content in markdown format.
        """
        payload = {"target": "universal", "url": url, "markdown": True}
        data = self._call_api(payload)
        return self._results_to_text(data)

    def search_web(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search Google and return a list of results.

        Use this tool to find up-to-date information without knowing a
        specific URL in advance.

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
        payload = {
            "target": "google_search",
            "query": query,
            "limit": num_results,
            "markdown": True,
        }
        data = self._call_api(payload)
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
        payload = {
            "target": "amazon_search",
            "query": query,
            "limit": num_results,
            "markdown": True,
        }
        data = self._call_api(payload)
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
        reddit_query = f"{query} site:reddit.com"
        payload = {
            "target": "google_search",
            "query": reddit_query,
            "limit": num_results,
            "markdown": True,
        }
        data = self._call_api(payload)
        return self._results_to_list(data)
