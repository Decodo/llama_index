"""
Decodo Readers for LlamaIndex
==============================

BaseReader implementations that pull data from the Decodo Web Scraping API
and return LlamaIndex Document objects ready for indexing or RAG pipelines.

Environment variable
--------------------
DECODO_API_TOKEN : str
    Your Decodo API token.  Can be passed explicitly to the constructors.

Usage
-----
>>> from llama_index.readers.decodo import DecodoReader, DecodoSearchReader
>>> reader = DecodoReader(api_token="your-token")
>>> docs = reader.load_data(["https://example.com", "https://news.ycombinator.com"])
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
_DEFAULT_TIMEOUT = 180.0
_INTEGRATION_HEADER = "llamaindex"

# Maps human-readable engine names to Decodo target identifiers.
_SEARCH_ENGINE_TARGETS: Dict[str, str] = {
    "google": "google_search",
    "amazon": "amazon_search",
    "reddit": "reddit_subreddit",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_auth_value(token: str, auth_mode: str) -> str:
    """Return the auth value for the given token and mode.

    For ``"basic"`` mode the token is already a base64-encoded
    ``username:password`` credential — pass it through directly.
    For ``"token"`` mode the token is used as-is.
    """
    return token


def _get_endpoint(auth_mode: str) -> str:
    return _V2_ENDPOINT if auth_mode == "basic" else _UNIFIED_ENDPOINT


def _call_api(
    endpoint: str,
    auth_value: str,
    payload: Dict[str, Any],
    timeout: float,
) -> Dict[str, Any]:
    """
    POST *payload* to the Decodo API endpoint and return parsed JSON.

    Raises
    ------
    RuntimeError
        If the server responds with a 4xx or 5xx status code.
    """
    headers = {
        "Authorization": f"Basic {auth_value}",
        "x-integration": _INTEGRATION_HEADER,
    }
    with httpx.Client(timeout=timeout) as client:
        response = client.post(endpoint, json=payload, headers=headers)
        if response.status_code >= 400:
            raise RuntimeError(
                f"Decodo API error {response.status_code}: {response.text}"
            )
        return response.json()


# ---------------------------------------------------------------------------
# DecodoReader
# ---------------------------------------------------------------------------


class DecodoWebReader(BaseReader):
    """
    Load one or more web pages via the Decodo Universal Scraper and return
    them as LlamaIndex :class:`~llama_index.core.schema.Document` objects.

    The scraper handles JavaScript rendering, anti-bot measures, and proxy
    rotation automatically.  The response content (markdown) is stored as
    ``Document.text``; the source URL, HTTP status code, and ``"source"``
    are stored in metadata.

    Parameters
    ----------
    api_token : str, optional
        Decodo API token.  Falls back to the ``DECODO_API_TOKEN`` environment
        variable if not provided.
    auth_mode : str
        ``"basic"`` (default) — base64-encode token and POST to ``/v2/scrape``.
        ``"token"`` — use the token as-is and POST to ``/unified/v1/scrape``.
    timeout : float
        HTTP request timeout in seconds.  Default is 180.

    Examples
    --------
    >>> from llama_index.readers.decodo import DecodoReader
    >>> reader = DecodoReader()
    >>> docs = reader.load_data(["https://example.com"])
    >>> print(docs[0].text[:200])
    """

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

        self._auth_value = _build_auth_value(token, auth_mode)
        self._endpoint = _get_endpoint(auth_mode)
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def load_data(
        self,
        urls: List[str],
        continue_on_error: bool = True,
    ) -> List[Document]:
        """
        Scrape each URL and return one Document per URL.

        Parameters
        ----------
        urls : list[str]
            Web page URLs to scrape.
        continue_on_error : bool
            If ``True`` (default), failed URLs produce a Document with error
            metadata rather than raising an exception.  If ``False``, the
            first failure raises immediately.

        Returns
        -------
        list[Document]
            One Document per URL.  The ``metadata`` dict contains ``"url"``,
            ``"status_code"``, and ``"source"`` keys.
        """
        documents: List[Document] = []

        for url in urls:
            payload: Dict[str, Any] = {
                "target": "universal",
                "url": url,
            }

            try:
                data = _call_api(
                    self._endpoint, self._auth_value, payload, self._timeout
                )
            except RuntimeError as exc:
                if not continue_on_error:
                    raise
                doc = Document(
                    text=f"[Decodo scrape error] {exc}",
                    metadata={
                        "url": url,
                        "status_code": None,
                        "source": url,
                        "error": str(exc),
                    },
                )
                documents.append(doc)
                continue

            for result in data.get("results", []):
                content: str = result.get("content", "")
                status_code: int = result.get("status_code", 0)
                result_url: str = result.get("url", url)

                metadata: Dict[str, Any] = {
                    "url": result_url,
                    "status_code": status_code,
                    "source": result_url,
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
        Reddit subreddit/search (uses ``reddit_subreddit`` target).

    Parameters
    ----------
    api_token : str, optional
        Decodo API token.  Falls back to the ``DECODO_API_TOKEN`` environment
        variable if not provided.
    auth_mode : str
        ``"basic"`` (default) or ``"token"``.
    timeout : float
        HTTP request timeout in seconds.  Default is 180.

    Examples
    --------
    >>> from llama_index.readers.decodo import DecodoSearchReader
    >>> reader = DecodoSearchReader()
    >>> docs = reader.load_data("open source LLMs", engine="google")
    >>> print(docs[0].text[:300])
    """

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

        self._auth_value = _build_auth_value(token, auth_mode)
        self._endpoint = _get_endpoint(auth_mode)
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def load_data(
        self,
        query: str,
        engine: str = "google",
        num_results: int = 10,
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
        num_results : int
            Maximum number of results to return.  Default is 10.

        Returns
        -------
        list[Document]
            One Document per result entry returned by Decodo.  The
            ``metadata`` dict contains ``"query"``, ``"engine"``,
            ``"target"``, ``"url"``, ``"status_code"``, and ``"source"``.
        """
        engine_lower = engine.lower()
        target = _SEARCH_ENGINE_TARGETS.get(engine_lower)
        if target is None:
            supported = ", ".join(f'"{k}"' for k in _SEARCH_ENGINE_TARGETS)
            raise ValueError(
                f"Unsupported engine {engine!r}.  "
                f"Supported engines: {supported}."
            )

        payload: Dict[str, Any] = {
            "target": target,
            "query": query,
            "limit": num_results,
        }

        data = _call_api(self._endpoint, self._auth_value, payload, self._timeout)

        documents: List[Document] = []
        for result in data.get("results", []):
            content: str = result.get("content", "")
            status_code: int = result.get("status_code", 0)
            result_url: str = result.get("url", "")

            metadata: Dict[str, Any] = {
                "query": query,
                "engine": engine_lower,
                "target": target,
                "url": result_url,
                "status_code": status_code,
                "source": result_url,
            }

            doc = Document(text=content, metadata=metadata)
            documents.append(doc)

        return documents
