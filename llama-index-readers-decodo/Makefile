GIT_ROOT ?= $(shell git rev-parse --show-toplevel)

help:  ## Show all Makefile targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

format:  ## Run code autoformatters (black)
	black .

lint:  ## Run linters (ruff, mypy)
	ruff check .
	mypy .

test:  ## Run tests via pytest
	pytest tests/ -v
