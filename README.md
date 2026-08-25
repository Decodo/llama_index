# decodo-llamaindex

[LlamaIndex](https://www.llamaindex.ai/) integration for the [Decodo Web Scraping API](https://decodo.com).
Load live web pages and search-engine results into your RAG pipelines, or give LlamaIndex agents real-time browsing capabilities — all through a single, type-safe Python package.

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
pip install decodo-llamaindex
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

All classes read `DECODO_API_TOKEN` from the environment by default.  You can also pass it explicitly:

```python
reader = DecodoWebReader(api_token="your_token_here")
```

---

## Usage

### DecodoWebReader — scrape URLs into Documents

```python
import os
from decodo_llamaindex import DecodoWebReader

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
from decodo_llamaindex import DecodoSearchReader

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
from decodo_llamaindex import DecodoWebReader

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
import os
from llama_index.core.agent import ReActAgent
from llama_index.llms.openai import OpenAI
from decodo_llamaindex import DecodoToolSpec

spec = DecodoToolSpec()
tools = spec.to_tool_list()

agent = ReActAgent.from_tools(
    tools,
    llm=OpenAI(model="gpt-4o"),
    verbose=True,
)

response = agent.chat(
    "Search Google for 'Python async best practices 2025' "
    "and summarise the top recommendations."
)
print(response)
```

See [`examples/agent_example.py`](examples/agent_example.py) for a runnable script.

---

## API Reference

### `DecodoWebReader`

```python
DecodoWebReader(
    api_token: str | None = None,       # default: DECODO_API_TOKEN env var
    extra_payload: dict | None = None,  # merged into every API request body
)
```

**Methods**

| Method | Returns | Description |
|---|---|---|
| `load_data(urls, *, extra_info=None)` | `list[Document]` | Scrape each URL, one Document per result |

**Document metadata fields:** `url`, `status_code`

---

### `DecodoSearchReader`

```python
DecodoSearchReader(
    api_token: str | None = None,
    extra_payload: dict | None = None,
)
```

**Methods**

| Method | Returns | Description |
|---|---|---|
| `load_data(query, engine="google", *, extra_info=None)` | `list[Document]` | Run a search, one Document per result block |

Supported `engine` values: `"google"`, `"amazon"`, `"reddit"`.

**Document metadata fields:** `query`, `engine`, `target`, `url`, `status_code`

---

### `DecodoToolSpec`

```python
DecodoToolSpec(
    api_token: str | None = None,
    extra_payload: dict | None = None,
)
```

**Registered tool functions**

| Function | Signature | Description |
|---|---|---|
| `scrape_url` | `(url: str) -> str` | Fetch and return a web page as markdown |
| `search` | `(query: str, engine: str = "google") -> str` | Run a web search and return results as text |

Convert to LlamaIndex tools with `spec.to_tool_list()`.

---

## Project Layout

```
integrations/llamaindex/
├── pyproject.toml
├── README.md
├── src/
│   └── decodo_llamaindex/
│       ├── __init__.py
│       ├── readers.py
│       └── tools.py
└── examples/
    ├── rag_pipeline.ipynb
    └── agent_example.py
```

---

> **Manual steps:** See [MANUAL_STEPS.md](../MANUAL_STEPS.md) (gitignored).

## License

MIT © Decodo
