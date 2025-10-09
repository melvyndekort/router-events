.PHONY: clean install update-deps test build full-build pylint dev run
.DEFAULT_GOAL: build

clean:
	@rm -rf .pytest_cache dist __pycache__ */__pycache__

install: clean
	@poetry install

update-deps:
	@poetry update

test: install
	@poetry run pytest

build: test
	@poetry build

full-build: clean
	@docker build -t router-events .

pylint:
	@poetry run pylint router_events

dev: install
	@poetry run python3 -m router_events.main

run: install
	@poetry run uvicorn router_events.main:app --host 0.0.0.0 --port 13959 --reload
