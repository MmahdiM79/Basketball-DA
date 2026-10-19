UV ?= uv
CONFIG ?= config/scraper.json
ARGS ?=

.PHONY: help setup scrape scrape-refresh scrape-help test

help:
	@printf '%s\n' \
		'Commands:' \
		'  make help            Show this guide (default)' \
		'  make setup           Create the environment and install locked dependencies' \
		'  make scrape          Collect data using the selected configuration' \
		'  make scrape-refresh  Fetch and parse again without reusing caches' \
		'  make scrape-help     Show all scraper CLI options' \
		'  make test            Run the existing test suite' \
		'' \
		'Variables:' \
		'  UV      uv executable path (default: uv)' \
		'  CONFIG  Configuration path (default: config/scraper.json)' \
		'  ARGS    Extra CLI options for scrape and scrape-refresh' \
		'' \
		'Examples:' \
		'  make scrape ARGS="--start-season 2024 --end-season 2024"' \
		'  make scrape ARGS="--datasets mvp_votes champions --delay 5"' \
		'  make scrape CONFIG="config/custom file.json"'

setup:
	"$(UV)" sync --locked

scrape:
	"$(UV)" run --locked python code/main.py --config "$(CONFIG)" $(ARGS)

scrape-refresh:
	"$(UV)" run --locked python code/main.py --config "$(CONFIG)" $(ARGS) --no-reuse-cache

scrape-help:
	"$(UV)" run --locked python code/main.py --help

test:
	"$(UV)" run --locked --directory code python -m unittest discover -s tests -v
