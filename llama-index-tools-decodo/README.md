# llama-index-tools-decodo

A [LlamaIndex](https://github.com/run-llama/llama_index) tool spec that wraps the [Decodo](https://decodo.com) web scraping API, exposing four tools for LlamaIndex agents: `scrape_url`, `search_web`, `search_amazon`, and `search_reddit`.

Decodo handles JavaScript rendering, anti-bot measures, CAPTCHA, and proxy rotation so your agent can reliably extract content from any page.

## Installation

```bash
pip install llama-index-tools-decodo
```

## Authentication

Obtain your API token from the [Decodo dashboard](https://app.decodo.com).

Set it as an environment variable:

```bash
export DECODO_API_TOKEN="your-token-here"
```

Or pass it directly to the constructor.

### Auth modes

| `auth_mode` | Encoding | Endpoint |
|---|---|---|
| `"basic"` (default) | `base64("token:")` | `POST /v2/scrape` |
| `"token"` | plain token | `POST /unified/v1/scrape` |

Both modes use the `Authorization: Basic <value>` header.

## Quick start

```python
from llama_index.tools.decodo import DecodoToolSpec

# Uses DECODO_API_TOKEN from environment
spec = DecodoToolSpec()
tools = spec.to_tool_list()
```

Use with a ReAct agent:

```python
from llama_index.core.agent import ReActAgent
from llama_index.llms.openai import OpenAI
from llama_index.tools.decodo import DecodoToolSpec

spec = DecodoToolSpec()
tools = spec.to_tool_list()
agent = ReActAgent.from_tools(tools, llm=OpenAI(model="gpt-4o"), verbose=True)
response = agent.chat("Summarise the homepage of https://news.ycombinator.com")
print(response)
```

## Tool reference

### `scrape_url(url)`

Scrape any web page and return its content as markdown.

```python
spec = DecodoToolSpec(api_token="your-token")
content = spec.scrape_url("https://news.ycombinator.com")
print(content)
```

### `search_web(query, num_results=10)`

Search Google and return a list of results, each with `url`, `content`, and `status_code`.

```python
results = spec.search_web("latest AI research papers", num_results=5)
for r in results:
    print(r["url"], r["content"][:200])
```

### `search_amazon(query, num_results=10)`

Search Amazon product listings.

```python
results = spec.search_amazon("noise cancelling headphones", num_results=5)
for r in results:
    print(r["url"], r["content"][:200])
```

### `search_reddit(query, num_results=10)`

Search Reddit via Google with a `site:reddit.com` filter.

```python
results = spec.search_reddit("best Python async libraries", num_results=5)
for r in results:
    print(r["url"], r["content"][:200])
```

## Auth mode examples

```python
# Basic mode (default) — recommended for most users
spec = DecodoToolSpec(api_token="your-token", auth_mode="basic")

# Token mode — for unified API access
spec = DecodoToolSpec(api_token="your-token", auth_mode="token")

# Custom timeout (seconds)
spec = DecodoToolSpec(api_token="your-token", timeout=300.0)
```

## License

MIT
