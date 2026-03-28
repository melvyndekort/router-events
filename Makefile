.PHONY: clean install update-deps test build full-build pylint dev run
.DEFAULT_GOAL: build

clean:
	@rm -rf .pytest_cache dist __pycache__ */__pycache__

install: clean
	@uv sync --all-extras

update-deps:
	@uv sync --upgrade --all-extras

test: install
	@uv run pytest

build: test
	@uv build

full-build: clean
	@docker build -t router-events .

lint: install
	@uv run pylint router_events

pylint:
	@uv run pylint router_events

dev: install
	@uv run python3 -m router_events.main

run: install
	@uv run uvicorn router_events.main:app --host 0.0.0.0 --port 13959 --reload
