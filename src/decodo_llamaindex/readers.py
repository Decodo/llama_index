"""
Decodo LlamaIndex Readers
=========================

BaseReader implementations that pull data from the Decodo Web Scraping API
and return LlamaIndex Document objects ready for indexing.

Environment variable
--------------------
DECODO_API_TOKEN : str
    Your Decodo API token.  Can be passed explicitly to the constructors
    instead.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx
from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import Document

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_V2_ENDPOINT = "https://scraper-api.decodo.com/v2/scrape"
_UNIFIED_ENDPOINT = "https://scraper-api.decodo.com/unified/v1/scrape"
_DEFAULT_TIMEOUT = 60.0  # seconds
_INTEGRATION_HEADER = "llamaindex-python"

# Maps human-readable engine names to Decodo target identifiers.
# Reddit uses google_search with a site:reddit.com filter — the reddit_subreddit
# target requires a subreddit url param, not a text query.
_SEARCH_ENGINE_TARGETS: Dict[str, str] = {
    "google": "google_search",
    "amazon": "amazon_search",
    "reddit": "google_search",
}
_REDDIT_SITE_FILTER = "site:reddit.com"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_client(api_token: str, auth_mode: str = "basic") -> httpx.Client:
    """Return a synchronous httpx client pre-configured for the Decodo API."""
    scheme = "Bearer" if auth_mode == "token" else "Basic"
    return httpx.Client(
        headers={
            "Authorization": f"{scheme} {api_token}",
            "x-integration": _INTEGRATION_HEADER,
        },
        timeout=_DEFAULT_TIMEOUT,
    )


def _scrape(client: httpx.Client, payload: Dict[str, Any], endpoint: str) -> Dict[str, Any]:
    """
    POST *payload* to the Decodo scrape endpoint and return the parsed JSON.

    Raises
    ------
    httpx.HTTPStatusError
        If the server responds with a 4xx or 5xx status code.
    ValueError
        If the response JSON is missing the expected ``results`` key.
    """
    response = client.post(endpoint, json=payload)
    response.raise_for_status()
    data: Dict[str, Any] = response.json()
    if "results" not in data:
        raise ValueError(
            f"Unexpected Decodo API response — missing 'results' key: {data}"
        )
    return data


# ---------------------------------------------------------------------------
# DecodoWebReader
# ---------------------------------------------------------------------------


class DecodoWebReader(BaseReader):
    """
    Load one or more web pages via the Decodo Universal Scraper and return
    them as LlamaIndex :class:`~llama_index.core.schema.Document` objects.

    The scraper handles JavaScript rendering, anti-bot measures, and proxy
    rotation automatically.  The response content (markdown) is stored as
    ``Document.text``; the source URL and HTTP status code are stored as
    metadata.

    Parameters
    ----------
    api_token : str, optional
        Decodo API token.  Falls back to the ``DECODO_API_TOKEN`` environment
        variable if not provided.
    extra_payload : dict, optional
        Additional key/value pairs merged into every scrape request body.
        Useful for passing Decodo-specific options such as ``"geo"`` or
        ``"render"`` settings.

    Examples
    --------
    >>> from decodo_llamaindex import DecodoWebReader
    >>> reader = DecodoWebReader()          # reads DECODO_API_TOKEN from env
    >>> docs = reader.load_data([
    ...     "https://news.ycombinator.com",
    ...     "https://example.com",
    ... ])
    >>> print(docs[0].text[:200])
    """

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
    # Public interface
    # ------------------------------------------------------------------

    def load_data(
        self,
        urls: List[str],
        *,
        extra_info: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """
        Scrape each URL and return one Document per URL.

        Parameters
        ----------
        urls : list[str]
            Web page URLs to scrape.
        extra_info : dict, optional
            Extra metadata merged into every Document's ``metadata`` dict.

        Returns
        -------
        list[Document]
            One Document per URL.  Documents where the scrape returned a
            non-2xx status are still returned but include the status code in
            their metadata so callers can filter them.
        """
        documents: List[Document] = []

        with _build_client(self.api_token, self.auth_mode) as client:
            for url in urls:
                payload: Dict[str, Any] = {
                    "target": "universal",
                    "url": url,
                    "markdown": True,
                    **self.extra_payload,
                }

                try:
                    data = _scrape(client, payload, self._endpoint)
                except httpx.HTTPStatusError as exc:
                    # Surface the error as a Document so callers receive one
                    # Document per requested URL regardless of failures.
                    doc = Document(
                        text=f"[Decodo scrape error] {exc}",
                        metadata={
                            "url": url,
                            "status_code": exc.response.status_code,
                            "error": str(exc),
                            **(extra_info or {}),
                        },
                    )
                    documents.append(doc)
                    continue

                for result in data["results"]:
                    content: str = result.get("content", "")
                    status_code: int = result.get("status_code", 0)
                    result_url: str = result.get("url", url)

                    metadata: Dict[str, Any] = {
                        "url": result_url,
                        "status_code": status_code,
                        **(extra_info or {}),
                    }

                    doc = Document(text=content, metadata=metadata)
                    documents.append(doc)

        return documents


# ---------------------------------------------------------------------------
# DecodoSearchReader
# ---------------------------------------------------------------------------


class DecodoSearchReader(BaseReader):
    """
    Retrieve search-engine results via the Decodo API and return them as
    LlamaIndex :class:`~llama_index.core.schema.Document` objects.

    Supported engines
    -----------------
    ``"google"``
        Google Search (default).
    ``"amazon"``
        Amazon product search.
    ``"reddit"``
        Reddit subreddit/search.

    Parameters
    ----------
    api_token : str, optional
        Decodo API token.  Falls back to the ``DECODO_API_TOKEN`` environment
        variable if not provided.
    extra_payload : dict, optional
        Additional key/value pairs merged into every scrape request body.

    Examples
    --------
    >>> from decodo_llamaindex import DecodoSearchReader
    >>> reader = DecodoSearchReader()
    >>> docs = reader.load_data("open source LLMs", engine="google")
    >>> print(docs[0].text[:300])
    """

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
    # Public interface
    # ------------------------------------------------------------------

    def load_data(
        self,
        query: str,
        engine: str = "google",
        num_results: int = 10,
        *,
        extra_info: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """
        Run *query* against the specified search *engine* and return results
        as Documents.

        Parameters
        ----------
        query : str
            Search query string.
        engine : str
            One of ``"google"``, ``"amazon"``, or ``"reddit"``.
        extra_info : dict, optional
            Extra metadata merged into every Document's ``metadata`` dict.

        Returns
        -------
        list[Document]
            One Document per result page / result block returned by Decodo.
        """
        engine_lower = engine.lower()
        target = _SEARCH_ENGINE_TARGETS.get(engine_lower)
        if target is None:
            supported = ", ".join(f'"{k}"' for k in _SEARCH_ENGINE_TARGETS)
            raise ValueError(
                f"Unsupported engine {engine!r}.  "
                f"Supported engines: {supported}."
            )

        effective_query = (
            f"{_REDDIT_SITE_FILTER} {query}" if engine_lower == "reddit" else query
        )

        payload: Dict[str, Any] = {
            "target": target,
            "query": effective_query,
            "limit": num_results,
            "markdown": True,
            **self.extra_payload,
        }

        with _build_client(self.api_token, self.auth_mode) as client:
            data = _scrape(client, payload, self._endpoint)

        documents: List[Document] = []
        for result in data["results"]:
            content: str = result.get("content", "")
            status_code: int = result.get("status_code", 0)
            result_url: str = result.get("url", "")

            metadata: Dict[str, Any] = {
                "query": query,
                "engine": engine_lower,
                "target": target,
                "url": result_url,
                "status_code": status_code,
                **(extra_info or {}),
            }

            doc = Document(text=content, metadata=metadata)
            documents.append(doc)

        return documents
