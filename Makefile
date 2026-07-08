.PHONY: install install-data install-dashboard format lint test run doctor market stock sectors candidates portfolio daily send-daily web dashboard

install:
	python3 -m pip install -e '.[dev]'

install-data:
	python3 -m pip install -e '.[dev,data]'

install-dashboard:
	python3 -m pip install -e '.[dev,data,dashboard]'

format:
	ruff format src tests

lint:
	ruff check src tests

test:
	pytest

run: web

doctor:
	PYTHONPATH=src python3 -m stock_ts.cli doctor --provider sample

market:
	PYTHONPATH=src python3 -m stock_ts.cli market --provider sample

stock:
	PYTHONPATH=src python3 -m stock_ts.cli stock 600519 --provider sample

sectors:
	PYTHONPATH=src python3 -m stock_ts.cli sectors --provider sample

candidates:
	PYTHONPATH=src python3 -m stock_ts.cli candidates --provider sample --limit 20

portfolio:
	PYTHONPATH=src python3 -m stock_ts.cli portfolio --provider sample --holdings data/portfolio/holdings.csv

daily:
	PYTHONPATH=src python3 -m stock_ts.cli daily --provider sample --holdings data/portfolio/holdings.csv --candidate-limit 20 --output reports/daily/sample-full.md

send-daily:
	PYTHONPATH=src python3 -m stock_ts.cli send-daily --provider sample --holdings data/portfolio/holdings.csv --channels email,wechat --dry-run

web:
	PYTHONPATH=src python3 -m stock_ts.web

dashboard:
	PYTHONPATH=src streamlit run src/stock_ts/dashboard.py
