# Changelog

## [0.1.2]

- README, docstrings and the missing-credential error now describe the API key first, with the basic auth token as the older-plan option

## [0.1.1]

- Request markdown output (`"markdown": true`) so `scrape_url` and the search tools return markdown instead of raw HTML
- `search_web`, `search_amazon` and `search_reddit` raise `RuntimeError` when Decodo returns no results or only failed ones, instead of returning an empty list
- README ReAct agent example updated to the `llama_index.core.agent.workflow.ReActAgent` API

## [0.1.0] - Initial release

- `DecodoToolSpec` with `scrape_url`, `search_web`, `search_amazon`, and `search_reddit` tools
- Dual auth modes: `"basic"` (token → `/v2/scrape`) and `"token"` (plain token → `/unified/v1/scrape`)
- `x-integration: llamaindex` header on all requests
- Reads `DECODO_API_TOKEN` from environment if not passed explicitly
