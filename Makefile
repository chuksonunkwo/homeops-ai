.PHONY: install test run demo

install:
	python -m pip install -e ".[dev]"

test:
	pytest

run:
	python run.py

demo:
	python scripts/demo_flow.py
