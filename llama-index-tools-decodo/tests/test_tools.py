"""
Unit tests for DecodoToolSpec.

All tests mock httpx — no network calls are made.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from llama_index.tools.decodo.base import (
    DecodoToolSpec,
    _UNIFIED_ENDPOINT,
    _V2_ENDPOINT,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_api_response(results=None):
    """Return a minimal Decodo API response dict."""
    if results is None:
        results = [{"url": "https://example.com", "content": "hello world", "status_code": 200}]
    return {"results": results}


def _mock_post(response_data=None):
    """Return a mock that simulates httpx.Client.post()."""
    if response_data is None:
        response_data = _make_api_response()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = response_data

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_response

    return mock_client


# ---------------------------------------------------------------------------
# Initialisation tests
# ---------------------------------------------------------------------------


class TestInit:
    def test_explicit_token_basic_mode(self):
        spec = DecodoToolSpec(api_token="mytoken", auth_mode="basic")
        assert spec._auth_value == "mytoken"
        assert spec._endpoint == _V2_ENDPOINT

    def test_explicit_token_token_mode(self):
        spec = DecodoToolSpec(api_token="mytoken", auth_mode="token")
        assert spec._auth_value == "mytoken"
        assert spec._endpoint == _UNIFIED_ENDPOINT

    def test_env_var_token(self, monkeypatch):
        monkeypatch.setenv("DECODO_API_TOKEN", "env-token")
        spec = DecodoToolSpec()
        assert spec._auth_value == "env-token"

    def test_missing_token_raises(self, monkeypatch):
        monkeypatch.delenv("DECODO_API_TOKEN", raising=False)
        with pytest.raises(ValueError, match="DECODO_API_TOKEN"):
            DecodoToolSpec()

    def test_invalid_auth_mode_raises(self):
        with pytest.raises(ValueError, match="auth_mode"):
            DecodoToolSpec(api_token="tok", auth_mode="invalid")

    def test_default_timeout(self):
        spec = DecodoToolSpec(api_token="tok")
        assert spec._timeout == 180.0


# ---------------------------------------------------------------------------
# spec_functions membership
# ---------------------------------------------------------------------------


class TestSpecFunctions:
    def test_scrape_url_in_spec_functions(self):
        assert "scrape_url" in DecodoToolSpec.spec_functions

    def test_search_web_in_spec_functions(self):
        assert "search_web" in DecodoToolSpec.spec_functions

    def test_search_amazon_in_spec_functions(self):
        assert "search_amazon" in DecodoToolSpec.spec_functions

    def test_search_reddit_in_spec_functions(self):
        assert "search_reddit" in DecodoToolSpec.spec_functions


# ---------------------------------------------------------------------------
# Endpoint selection by auth_mode
# ---------------------------------------------------------------------------


class TestEndpointSelection:
    def test_basic_mode_uses_v2_endpoint(self):
        spec = DecodoToolSpec(api_token="tok", auth_mode="basic")
        mock_client = _mock_post()
        with patch("llama_index.tools.decodo.base.httpx.Client", return_value=mock_client):
            spec.scrape_url("https://example.com")
        call_args = mock_client.post.call_args
        assert call_args[0][0] == _V2_ENDPOINT

    def test_token_mode_uses_unified_endpoint(self):
        spec = DecodoToolSpec(api_token="tok", auth_mode="token")
        mock_client = _mock_post()
        with patch("llama_index.tools.decodo.base.httpx.Client", return_value=mock_client):
            spec.scrape_url("https://example.com")
        call_args = mock_client.post.call_args
        assert call_args[0][0] == _UNIFIED_ENDPOINT


# ---------------------------------------------------------------------------
# scrape_url
# ---------------------------------------------------------------------------


class TestScrapeUrl:
    def test_returns_content_string(self):
        spec = DecodoToolSpec(api_token="tok")
        mock_client = _mock_post(_make_api_response([
            {"url": "https://example.com", "content": "page text", "status_code": 200}
        ]))
        with patch("llama_index.tools.decodo.base.httpx.Client", return_value=mock_client):
            result = spec.scrape_url("https://example.com")
        assert "page text" in result

    def test_sends_universal_target(self):
        spec = DecodoToolSpec(api_token="tok")
        mock_client = _mock_post()
        with patch("llama_index.tools.decodo.base.httpx.Client", return_value=mock_client):
            spec.scrape_url("https://example.com")
        payload = mock_client.post.call_args[1]["json"]
        assert payload["target"] == "universal"

    def test_sends_integration_header(self):
        spec = DecodoToolSpec(api_token="tok")
        mock_client = _mock_post()
        with patch("llama_index.tools.decodo.base.httpx.Client", return_value=mock_client):
            spec.scrape_url("https://example.com")
        headers = mock_client.post.call_args[1]["headers"]
        assert headers.get("x-integration") == "llamaindex-python"

    def test_sends_authorization_header(self):
        spec = DecodoToolSpec(api_token="tok")
        mock_client = _mock_post()
        with patch("llama_index.tools.decodo.base.httpx.Client", return_value=mock_client):
            spec.scrape_url("https://example.com")
        headers = mock_client.post.call_args[1]["headers"]
        assert headers.get("Authorization", "").startswith("Basic ")


# ---------------------------------------------------------------------------
# search_web
# ---------------------------------------------------------------------------


class TestSearchWeb:
    def test_uses_google_search_target(self):
        spec = DecodoToolSpec(api_token="tok")
        mock_client = _mock_post()
        with patch("llama_index.tools.decodo.base.httpx.Client", return_value=mock_client):
            spec.search_web("python async")
        payload = mock_client.post.call_args[1]["json"]
        assert payload["target"] == "google_search"

    def test_returns_list(self):
        spec = DecodoToolSpec(api_token="tok")
        mock_client = _mock_post(_make_api_response([
            {"url": "https://example.com", "content": "result", "status_code": 200}
        ]))
        with patch("llama_index.tools.decodo.base.httpx.Client", return_value=mock_client):
            result = spec.search_web("python async")
        assert isinstance(result, list)
        assert result[0]["url"] == "https://example.com"

    def test_passes_num_results(self):
        spec = DecodoToolSpec(api_token="tok")
        mock_client = _mock_post()
        with patch("llama_index.tools.decodo.base.httpx.Client", return_value=mock_client):
            spec.search_web("query", num_results=5)
        payload = mock_client.post.call_args[1]["json"]
        assert payload["limit"] == 5


# ---------------------------------------------------------------------------
# search_amazon
# ---------------------------------------------------------------------------


class TestSearchAmazon:
    def test_uses_amazon_search_target(self):
        spec = DecodoToolSpec(api_token="tok")
        mock_client = _mock_post()
        with patch("llama_index.tools.decodo.base.httpx.Client", return_value=mock_client):
            spec.search_amazon("laptop")
        payload = mock_client.post.call_args[1]["json"]
        assert payload["target"] == "amazon_search"

    def test_returns_list(self):
        spec = DecodoToolSpec(api_token="tok")
        mock_client = _mock_post()
        with patch("llama_index.tools.decodo.base.httpx.Client", return_value=mock_client):
            result = spec.search_amazon("laptop")
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# search_reddit
# ---------------------------------------------------------------------------


class TestSearchReddit:
    def test_uses_google_search_target(self):
        spec = DecodoToolSpec(api_token="tok")
        mock_client = _mock_post()
        with patch("llama_index.tools.decodo.base.httpx.Client", return_value=mock_client):
            spec.search_reddit("best python frameworks")
        payload = mock_client.post.call_args[1]["json"]
        assert payload["target"] == "google_search"

    def test_includes_site_reddit_filter(self):
        spec = DecodoToolSpec(api_token="tok")
        mock_client = _mock_post()
        with patch("llama_index.tools.decodo.base.httpx.Client", return_value=mock_client):
            spec.search_reddit("best python frameworks")
        payload = mock_client.post.call_args[1]["json"]
        assert "site:reddit.com" in payload["query"]

    def test_returns_list(self):
        spec = DecodoToolSpec(api_token="tok")
        mock_client = _mock_post()
        with patch("llama_index.tools.decodo.base.httpx.Client", return_value=mock_client):
            result = spec.search_reddit("python")
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_api_error_raises_runtime_error(self):
        spec = DecodoToolSpec(api_token="tok")
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response

        with patch("llama_index.tools.decodo.base.httpx.Client", return_value=mock_client):
            with pytest.raises(RuntimeError, match="Decodo API error"):
                spec.scrape_url("https://example.com")

    def test_401_raises_runtime_error(self):
        spec = DecodoToolSpec(api_token="bad-token")
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response

        with patch("llama_index.tools.decodo.base.httpx.Client", return_value=mock_client):
            with pytest.raises(RuntimeError, match="Decodo API error"):
                spec.scrape_url("https://example.com")


# ---------------------------------------------------------------------------
# markdown output and failed scrapes
# ---------------------------------------------------------------------------


class TestMarkdownAndFailedScrapes:
    @pytest.mark.parametrize(
        "call",
        [
            lambda s: s.scrape_url("https://example.com"),
            lambda s: s.search_web("q"),
            lambda s: s.search_amazon("q"),
            lambda s: s.search_reddit("q"),
        ],
    )
    def test_requests_markdown(self, call):
        spec = DecodoToolSpec(api_token="tok")
        mock_client = _mock_post()
        with patch("llama_index.tools.decodo.base.httpx.Client", return_value=mock_client):
            call(spec)
        assert mock_client.post.call_args[1]["json"]["markdown"] is True

    @pytest.mark.parametrize(
        "results",
        [[], [{"url": "", "content": "", "status_code": 613}]],
    )
    @pytest.mark.parametrize("method", ["search_web", "search_amazon", "search_reddit"])
    def test_search_raises_when_scrape_failed(self, method, results):
        spec = DecodoToolSpec(api_token="tok")
        mock_client = _mock_post(_make_api_response(results))
        with patch("llama_index.tools.decodo.base.httpx.Client", return_value=mock_client):
            with pytest.raises(RuntimeError, match="could not scrape"):
                getattr(spec, method)("q")
