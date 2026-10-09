# Changelog

## [0.1.3]

- README, docstrings and the missing-credential error now describe the API key first, with the basic auth token as the older-plan option

## [0.1.2]

- Request markdown output (`"markdown": true`) so `DecodoWebReader` and `DecodoSearchReader` return markdown instead of raw HTML
- `DecodoSearchReader.load_data` raises `RuntimeError` when Decodo returns no results or only failed ones, instead of returning an empty list

## [0.1.0] - Initial release

- `DecodoWebReader` for scraping URLs and returning LlamaIndex Documents
- `DecodoSearchReader` for Google, Amazon, and Reddit search results
- Dual auth modes: `"basic"` (token → `/v2/scrape`) and `"token"` (plain token → `/unified/v1/scrape`)
- `x-integration: llamaindex` header on all requests
- `continue_on_error` support in `DecodoWebReader.load_data`
- Reads `DECODO_API_TOKEN` from environment if not passed explicitly
