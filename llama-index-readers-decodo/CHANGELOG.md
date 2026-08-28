# Changelog

## [0.1.0] - Initial release

- `DecodoWebReader` for scraping URLs and returning LlamaIndex Documents
- `DecodoSearchReader` for Google, Amazon, and Reddit search results
- Dual auth modes: `"basic"` (token → `/v2/scrape`) and `"token"` (plain token → `/unified/v1/scrape`)
- `x-integration: llamaindex` header on all requests
- `continue_on_error` support in `DecodoWebReader.load_data`
- Reads `DECODO_API_TOKEN` from environment if not passed explicitly
