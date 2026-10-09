# llama-index-readers-decodo

[LlamaIndex](https://github.com/run-llama/llama_index) data readers that pull web pages and search results from the [Decodo](https://decodo.com) web scraping API and return them as `Document` objects ready for indexing or RAG pipelines.

Decodo handles JavaScript rendering, anti-bot measures, CAPTCHA, and proxy rotation transparently.

## Installation

```bash
pip install llama-index-readers-decodo
```

## Authentication

Copy your Web Data API key from your Web Data API subscription on the [Decodo dashboard](https://dashboard.decodo.com/web-data/playground).
Older plans only have a basic authentication token, which also works (see below).

```bash
export DECODO_API_TOKEN="your-api-key"
```

### Auth modes

| `auth_mode` | Header scheme | Endpoint |
|---|---|---|
| `"basic"` (default) | `Authorization: Basic <base64(token:)>` | `POST /v2/scrape` |
| `"token"` | `Authorization: Bearer <token>` | `POST /unified/v1/scrape` |

Use `auth_mode="token"` with your API key; with the default `"basic"` mode it is rejected
with a 401. Use `"basic"` only with a basic authentication token from an older plan. Both readers request markdown output, so
`Document.text` is markdown rather than raw HTML.

## DecodoWebReader

Load one or more URLs as LlamaIndex `Document` objects.

```python
from llama_index.readers.decodo import DecodoWebReader

reader = DecodoWebReader(auth_mode="token")  # reads DECODO_API_TOKEN from env

docs = reader.load_data([
    "https://news.ycombinator.com",
    "https://example.com",
])

for doc in docs:
    print(doc.metadata["url"], doc.text[:200])
```

Each `Document` has metadata with keys `url`, `status_code`, and `source`.

### Error handling

By default (`continue_on_error=True`), failed URLs produce a `Document` with error metadata rather than raising an exception:

```python
docs = reader.load_data(
    ["https://good-url.com", "https://bad-url.com"],
    continue_on_error=True,   # default
)
# One Document per URL; failed ones have "error" in metadata

docs = reader.load_data(["https://bad-url.com"], continue_on_error=False)
# Raises RuntimeError on first failure
```

## DecodoSearchReader

Run a query against Google, Amazon, or Reddit and return results as `Document` objects.

```python
from llama_index.readers.decodo import DecodoSearchReader

reader = DecodoSearchReader(auth_mode="token")

# Google search
docs = reader.load_data("open source LLMs", engine="google", num_results=10)

# Amazon product search
docs = reader.load_data("mechanical keyboards", engine="amazon", num_results=5)

# Reddit search
docs = reader.load_data("best async Python", engine="reddit", num_results=5)

for doc in docs:
    print(doc.metadata["engine"], doc.metadata["url"])
    print(doc.text[:300])
```

Each `Document` has metadata: `query`, `engine`, `target`, `url`, `status_code`, and `source`.

`load_data` raises `RuntimeError` on an HTTP error, and also when Decodo returns no results or
only failed ones (for example status `613`), rather than returning an empty list. The Reddit
engine uses Google Search with a `site:reddit.com` filter, so it can occasionally fail this way;
retrying usually succeeds.

## Auth mode examples

```python
# Token mode
reader = DecodoWebReader(api_token="your-api-key", auth_mode="token")

# Basic auth token (older plans, default)
reader = DecodoWebReader(api_token="your-basic-auth-token", auth_mode="basic")

# Custom timeout
reader = DecodoWebReader(api_token="your-api-key", auth_mode="token", timeout=300.0)

# Same options for DecodoSearchReader
search_reader = DecodoSearchReader(api_token="your-api-key", auth_mode="token")
```

## Use in a RAG pipeline

```python
from llama_index.core import VectorStoreIndex
from llama_index.readers.decodo import DecodoWebReader

reader = DecodoWebReader(auth_mode="token")
docs = reader.load_data(["https://docs.example.com/guide"])
index = VectorStoreIndex.from_documents(docs)
query_engine = index.as_query_engine()
response = query_engine.query("How do I get started?")
print(response)
```

## License

MIT
