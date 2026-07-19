.PHONY: install format lint test run

install:
	python3 -m pip install -e '.[dev]'

format:
	ruff format src tests

lint:
	ruff check src tests

test:
	pytest

run:
	PYTHONPATH=src python3 -m aster_market.web
