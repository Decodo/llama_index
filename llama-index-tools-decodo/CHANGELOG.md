# Changelog

## [0.1.0] - Initial release

- `DecodoToolSpec` with `scrape_url`, `search_web`, `search_amazon`, and `search_reddit` tools
- Dual auth modes: `"basic"` (token → `/v2/scrape`) and `"token"` (plain token → `/unified/v1/scrape`)
- `x-integration: llamaindex` header on all requests
- Reads `DECODO_API_TOKEN` from environment if not passed explicitly
