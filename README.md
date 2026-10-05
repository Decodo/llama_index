# decodo-llamaindex

[LlamaIndex](https://www.llamaindex.ai/) integration for the [Decodo Web Scraping API](https://decodo.com).
Load live web pages and search-engine results into your RAG pipelines, or give LlamaIndex agents real-time browsing capabilities — through two Python packages.

---

## Features

| Component | Description |
|---|---|
| `DecodoWebReader` | Scrape one or more URLs → `list[Document]` |
| `DecodoSearchReader` | Run Google / Amazon / Reddit search → `list[Document]` |
| `DecodoToolSpec` | LlamaIndex tool spec for agent use (scrape + search) |

Decodo handles JavaScript rendering, anti-bot bypassing, CAPTCHA solving, and proxy rotation automatically.

---

## Installation

```bash
pip install llama-index-readers-decodo llama-index-tools-decodo
```

To use the examples you will also need an LLM provider package, e.g.:

```bash
pip install llama-index-llms-openai llama-index-embeddings-openai
```

---

## Authentication

Get your API token from the [Decodo dashboard](https://app.decodo.com) and export it:

```bash
export DECODO_API_TOKEN="your_token_here"
```

All classes read `DECODO_API_TOKEN` from the environment by default.  You can also pass it explicitly. A Unified API key (a plain hex string) needs `auth_mode="token"`:

```python
reader = DecodoWebReader(api_token="your_token_here")
reader = DecodoWebReader(api_token="your_api_key", auth_mode="token")
```

---

## Usage

### DecodoWebReader — scrape URLs into Documents

```python
import os
from llama_index.readers.decodo import DecodoWebReader

reader = DecodoWebReader()  # reads DECODO_API_TOKEN from env

docs = reader.load_data([
    "https://news.ycombinator.com",
    "https://en.wikipedia.org/wiki/Large_language_model",
])

for doc in docs:
    print(doc.metadata["url"], "—", len(doc.text), "chars")
```

### DecodoSearchReader — fetch search results into Documents

```python
from llama_index.readers.decodo import DecodoSearchReader

reader = DecodoSearchReader()

# Google Search
google_docs = reader.load_data("open source LLMs 2025", engine="google")

# Amazon product search
amazon_docs = reader.load_data("mechanical keyboard", engine="amazon")

# Reddit
reddit_docs = reader.load_data("r/MachineLearning", engine="reddit")
```

### RAG Pipeline

```python
import os
from llama_index.core import VectorStoreIndex
from llama_index.core.settings import Settings
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.readers.decodo import DecodoWebReader

Settings.llm = OpenAI(model="gpt-4o")
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

# 1. Load documents
reader = DecodoWebReader()
docs = reader.load_data([
    "https://en.wikipedia.org/wiki/Retrieval-augmented_generation",
    "https://en.wikipedia.org/wiki/Transformer_(deep_learning_architecture)",
])

# 2. Build index
index = VectorStoreIndex.from_documents(docs)

# 3. Query
engine = index.as_query_engine()
response = engine.query("How does RAG work and why is it useful?")
print(response)
```

See [`examples/rag_pipeline.ipynb`](examples/rag_pipeline.ipynb) for a complete walkthrough.

### LlamaIndex Agent with DecodoToolSpec

```python
import asyncio
from llama_index.core.agent.workflow import ReActAgent
from llama_index.llms.openai import OpenAI
from llama_index.tools.decodo import DecodoToolSpec

spec = DecodoToolSpec()
tools = spec.to_tool_list()

agent = ReActAgent(tools=tools, llm=OpenAI(model="gpt-4o"))


async def main() -> None:
    response = await agent.run(
        "Search Google for 'Python async best practices 2025' "
        "and summarise the top recommendations."
    )
    print(response)


asyncio.run(main())
```

See [`examples/agent_example.py`](examples/agent_example.py) for a runnable script.

---

## API Reference

The integration ships as two packages. Each takes `api_token`, `auth_mode` and `timeout`.

| Argument | Default | Description |
|---|---|---|
| `api_token` | `DECODO_API_TOKEN` env var | Decodo credential |
| `auth_mode` | `"basic"` | `"basic"` sends `Authorization: Basic` to `/v2/scrape`; `"token"` sends `Authorization: Bearer` to `/unified/v1/scrape`. A Unified API key (plain hex string) needs `"token"`. |
| `timeout` | `180.0` | HTTP timeout in seconds |

### `DecodoWebReader` (`llama-index-readers-decodo`)

| Method | Returns | Description |
|---|---|---|
| `load_data(urls, continue_on_error=True)` | `list[Document]` | Scrape each URL; failed URLs become error Documents unless `continue_on_error=False` |

**Document metadata:** `url`, `status_code`, `source`

### `DecodoSearchReader` (`llama-index-readers-decodo`)

| Method | Returns | Description |
|---|---|---|
| `load_data(query, engine="google", num_results=10)` | `list[Document]` | Run a search; raises `RuntimeError` if Decodo returns no results or only failed ones |

Supported `engine` values: `"google"`, `"amazon"`, `"reddit"` (Google with a `site:reddit.com` filter).

**Document metadata:** `query`, `engine`, `target`, `url`, `status_code`, `source`

### `DecodoToolSpec` (`llama-index-tools-decodo`)

| Function | Signature | Description |
|---|---|---|
| `scrape_url` | `(url: str) -> str` | Fetch a web page as markdown |
| `search_web` | `(query: str, num_results: int = 10) -> list[dict]` | Google search |
| `search_amazon` | `(query: str, num_results: int = 10) -> list[dict]` | Amazon product search |
| `search_reddit` | `(query: str, num_results: int = 10) -> list[dict]` | Google search with a `site:reddit.com` filter |

Search functions return dicts with `url`, `content` and `status_code`, and raise `RuntimeError`
if Decodo returns no results or only failed ones. Convert to LlamaIndex tools with `spec.to_tool_list()`.

---

## Project Layout

```
├── llama-index-readers-decodo/   # DecodoWebReader, DecodoSearchReader
├── llama-index-tools-decodo/     # DecodoToolSpec
└── examples/
    ├── rag_pipeline.ipynb
    └── agent_example.py
```

---

## License

MIT © Decodo
