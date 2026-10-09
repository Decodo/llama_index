# llama-index-tools-decodo

A [LlamaIndex](https://github.com/run-llama/llama_index) tool spec that wraps the [Decodo](https://decodo.com) web scraping API, exposing four tools for LlamaIndex agents: `scrape_url`, `search_web`, `search_amazon`, and `search_reddit`.

Decodo handles JavaScript rendering, anti-bot measures, CAPTCHA, and proxy rotation so your agent can reliably extract content from any page.

## Installation

```bash
pip install llama-index-tools-decodo
```

## Authentication

Copy your Web Data API key from your Web Data API subscription on the [Decodo dashboard](https://dashboard.decodo.com/web-data/playground).
Older plans only have a basic authentication token, which also works (see below).

Set it as an environment variable:

```bash
export DECODO_API_TOKEN="your-api-key"
```

Or pass it directly to the constructor.

### Auth modes

| `auth_mode` | Encoding | Endpoint |
|---|---|---|
| `"basic"` (default) | `base64("token:")` | `POST /v2/scrape` |
| `"token"` | plain token | `POST /unified/v1/scrape` |

`"basic"` sends `Authorization: Basic <token>`; `"token"` sends `Authorization: Bearer <token>`.
Use `"token"` with your API key and `"basic"` only with a basic authentication token from an older
plan. A credential used in the wrong mode is rejected with a 401.

All tools request markdown output.

## Quick start

```python
from llama_index.tools.decodo import DecodoToolSpec

# Uses DECODO_API_TOKEN from environment
spec = DecodoToolSpec(auth_mode="token")
tools = spec.to_tool_list()
```

Use with a ReAct agent:

```python
import asyncio

from llama_index.core.agent.workflow import ReActAgent
from llama_index.llms.openai import OpenAI
from llama_index.tools.decodo import DecodoToolSpec

spec = DecodoToolSpec(auth_mode="token")
tools = spec.to_tool_list()
agent = ReActAgent(tools=tools, llm=OpenAI(model="gpt-4o"))


async def main() -> None:
    response = await agent.run("Summarise the homepage of https://news.ycombinator.com")
    print(response)


asyncio.run(main())
```

## Tool reference

### `scrape_url(url)`

Scrape any web page and return its content as markdown.

```python
spec = DecodoToolSpec(api_token="your-api-key", auth_mode="token")
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

## Errors

All tools raise `RuntimeError` on an HTTP error from the API. `search_web`, `search_amazon` and
`search_reddit` also raise it when Decodo returns no results or only failed ones (for example
status `613`, "We were not able to scrape the target"), so an agent can retry instead of reading
an empty list as "no results".

## Auth mode examples

```python
# API key
spec = DecodoToolSpec(api_token="your-api-key", auth_mode="token")

# Basic auth token (older plans, default)
spec = DecodoToolSpec(api_token="your-basic-auth-token", auth_mode="basic")

# Custom timeout (seconds)
spec = DecodoToolSpec(api_token="your-api-key", auth_mode="token", timeout=300.0)
```

## License

MIT
