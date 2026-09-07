"""
Unit tests for DecodoWebReader and DecodoSearchReader.

All tests mock httpx — no network calls are made.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from llama_index.readers.decodo.base import (
    DecodoWebReader,
    DecodoSearchReader,
    _UNIFIED_ENDPOINT,
    _V2_ENDPOINT,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_api_response(results=None):
    """Return a minimal Decodo API response dict."""
    if results is None:
        results = [
            {
                "url": "https://example.com",
                "content": "hello world",
                "status_code": 200,
            }
        ]
    return {"results": results}


def _mock_post(response_data=None, status_code=200):
    """Return a mock httpx.Client that simulates a POST call."""
    if response_data is None:
        response_data = _make_api_response()

    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.text = "OK"
    mock_response.json.return_value = response_data

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_response

    return mock_client


# ---------------------------------------------------------------------------
# DecodoWebReader — init
# ---------------------------------------------------------------------------


class TestDecodoWebReaderInit:
    def test_explicit_token_basic_mode(self):
        reader = DecodoWebReader(api_token="mytoken", auth_mode="basic")
        assert reader._auth_value == "mytoken"
        assert reader._endpoint == _V2_ENDPOINT

    def test_explicit_token_token_mode(self):
        reader = DecodoWebReader(api_token="mytoken", auth_mode="token")
        assert reader._auth_value == "mytoken"
        assert reader._endpoint == _UNIFIED_ENDPOINT

    def test_env_var_token(self, monkeypatch):
        monkeypatch.setenv("DECODO_API_TOKEN", "env-token")
        reader = DecodoWebReader()
        assert reader._auth_value == "env-token"

    def test_missing_token_raises(self, monkeypatch):
        monkeypatch.delenv("DECODO_API_TOKEN", raising=False)
        with pytest.raises(ValueError, match="DECODO_API_TOKEN"):
            DecodoWebReader()

    def test_invalid_auth_mode_raises(self):
        with pytest.raises(ValueError, match="auth_mode"):
            DecodoWebReader(api_token="tok", auth_mode="wrong")


# ---------------------------------------------------------------------------
# DecodoWebReader — load_data
# ---------------------------------------------------------------------------


class TestDecodoWebReaderLoadData:
    def test_returns_documents(self):
        reader = DecodoWebReader(api_token="tok")
        mock_client = _mock_post(_make_api_response([
            {"url": "https://example.com", "content": "hello", "status_code": 200}
        ]))
        with patch("llama_index.readers.decodo.base.httpx.Client", return_value=mock_client):
            docs = reader.load_data(["https://example.com"])
        assert len(docs) == 1
        assert docs[0].text == "hello"

    def test_document_metadata_has_required_keys(self):
        reader = DecodoWebReader(api_token="tok")
        mock_client = _mock_post(_make_api_response([
            {"url": "https://example.com", "content": "text", "status_code": 200}
        ]))
        with patch("llama_index.readers.decodo.base.httpx.Client", return_value=mock_client):
            docs = reader.load_data(["https://example.com"])
        meta = docs[0].metadata
        assert "url" in meta
        assert "status_code" in meta
        assert "source" in meta

    def test_basic_mode_uses_v2_endpoint(self):
        reader = DecodoWebReader(api_token="tok", auth_mode="basic")
        mock_client = _mock_post()
        with patch("llama_index.readers.decodo.base.httpx.Client", return_value=mock_client):
            reader.load_data(["https://example.com"])
        call_args = mock_client.post.call_args
        assert call_args[0][0] == _V2_ENDPOINT

    def test_token_mode_uses_unified_endpoint(self):
        reader = DecodoWebReader(api_token="tok", auth_mode="token")
        mock_client = _mock_post()
        with patch("llama_index.readers.decodo.base.httpx.Client", return_value=mock_client):
            reader.load_data(["https://example.com"])
        call_args = mock_client.post.call_args
        assert call_args[0][0] == _UNIFIED_ENDPOINT

    def test_sends_integration_header(self):
        reader = DecodoWebReader(api_token="tok")
        mock_client = _mock_post()
        with patch("llama_index.readers.decodo.base.httpx.Client", return_value=mock_client):
            reader.load_data(["https://example.com"])
        headers = mock_client.post.call_args[1]["headers"]
        assert headers.get("x-integration") == "llamaindex"

    def test_continue_on_error_returns_error_document(self):
        reader = DecodoWebReader(api_token="tok")
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Server Error"

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response

        with patch("llama_index.readers.decodo.base.httpx.Client", return_value=mock_client):
            docs = reader.load_data(["https://bad-url.com"], continue_on_error=True)

        assert len(docs) == 1
        assert "error" in docs[0].metadata
        assert "Decodo scrape error" in docs[0].text

    def test_continue_on_error_false_raises(self):
        reader = DecodoWebReader(api_token="tok")
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Server Error"

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response

        with patch("llama_index.readers.decodo.base.httpx.Client", return_value=mock_client):
            with pytest.raises(RuntimeError, match="Decodo API error"):
                reader.load_data(["https://bad-url.com"], continue_on_error=False)

    def test_multiple_urls_returns_multiple_documents(self):
        reader = DecodoWebReader(api_token="tok")
        mock_client = _mock_post(_make_api_response([
            {"url": "https://example.com", "content": "page1", "status_code": 200}
        ]))
        with patch("llama_index.readers.decodo.base.httpx.Client", return_value=mock_client):
            docs = reader.load_data(["https://a.com", "https://b.com"])
        assert len(docs) == 2


# ---------------------------------------------------------------------------
# DecodoSearchReader — init
# ---------------------------------------------------------------------------


class TestDecodoSearchReaderInit:
    def test_basic_mode(self):
        reader = DecodoSearchReader(api_token="tok", auth_mode="basic")
        assert reader._endpoint == _V2_ENDPOINT

    def test_token_mode(self):
        reader = DecodoSearchReader(api_token="tok", auth_mode="token")
        assert reader._endpoint == _UNIFIED_ENDPOINT

    def test_missing_token_raises(self, monkeypatch):
        monkeypatch.delenv("DECODO_API_TOKEN", raising=False)
        with pytest.raises(ValueError, match="DECODO_API_TOKEN"):
            DecodoSearchReader()


# ---------------------------------------------------------------------------
# DecodoSearchReader — load_data / engine→target mapping
# ---------------------------------------------------------------------------


class TestDecodoSearchReaderLoadData:
    def test_google_engine_maps_to_google_search(self):
        reader = DecodoSearchReader(api_token="tok")
        mock_client = _mock_post()
        with patch("llama_index.readers.decodo.base.httpx.Client", return_value=mock_client):
            reader.load_data("python tips", engine="google")
        payload = mock_client.post.call_args[1]["json"]
        assert payload["target"] == "google_search"

    def test_amazon_engine_maps_to_amazon_search(self):
        reader = DecodoSearchReader(api_token="tok")
        mock_client = _mock_post()
        with patch("llama_index.readers.decodo.base.httpx.Client", return_value=mock_client):
            reader.load_data("laptop", engine="amazon")
        payload = mock_client.post.call_args[1]["json"]
        assert payload["target"] == "amazon_search"

    def test_reddit_engine_uses_google_search_with_site_filter(self):
        reader = DecodoSearchReader(api_token="tok")
        mock_client = _mock_post()
        with patch("llama_index.readers.decodo.base.httpx.Client", return_value=mock_client):
            reader.load_data("machine learning", engine="reddit")
        payload = mock_client.post.call_args[1]["json"]
        assert payload["target"] == "google_search"
        assert "site:reddit.com" in payload["query"]

    def test_invalid_engine_raises(self):
        reader = DecodoSearchReader(api_token="tok")
        with pytest.raises(ValueError, match="Unsupported engine"):
            reader.load_data("query", engine="bing")

    def test_returns_documents(self):
        reader = DecodoSearchReader(api_token="tok")
        mock_client = _mock_post(_make_api_response([
            {"url": "https://example.com", "content": "result text", "status_code": 200}
        ]))
        with patch("llama_index.readers.decodo.base.httpx.Client", return_value=mock_client):
            docs = reader.load_data("open source LLMs", engine="google")
        assert len(docs) == 1
        assert docs[0].text == "result text"
        assert docs[0].metadata["engine"] == "google"
        assert docs[0].metadata["target"] == "google_search"
        assert "source" in docs[0].metadata

    def test_basic_mode_uses_v2_endpoint(self):
        reader = DecodoSearchReader(api_token="tok", auth_mode="basic")
        mock_client = _mock_post()
        with patch("llama_index.readers.decodo.base.httpx.Client", return_value=mock_client):
            reader.load_data("query")
        assert mock_client.post.call_args[0][0] == _V2_ENDPOINT

    def test_token_mode_uses_unified_endpoint(self):
        reader = DecodoSearchReader(api_token="tok", auth_mode="token")
        mock_client = _mock_post()
        with patch("llama_index.readers.decodo.base.httpx.Client", return_value=mock_client):
            reader.load_data("query")
        assert mock_client.post.call_args[0][0] == _UNIFIED_ENDPOINT

    def test_sends_integration_header(self):
        reader = DecodoSearchReader(api_token="tok")
        mock_client = _mock_post()
        with patch("llama_index.readers.decodo.base.httpx.Client", return_value=mock_client):
            reader.load_data("test")
        headers = mock_client.post.call_args[1]["headers"]
        assert headers.get("x-integration") == "llamaindex"

    def test_passes_num_results(self):
        reader = DecodoSearchReader(api_token="tok")
        mock_client = _mock_post()
        with patch("llama_index.readers.decodo.base.httpx.Client", return_value=mock_client):
            reader.load_data("query", num_results=5)
        payload = mock_client.post.call_args[1]["json"]
        assert payload["limit"] == 5
