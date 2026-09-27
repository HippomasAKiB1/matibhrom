.PHONY: setup test lint run-dev run-test check-budget build-index clean docs

setup:
	pip install -r requirements-cpu.txt

test:
	pytest --cov=src --cov-fail-under=80

lint:
	ruff check src/ tests/ scripts/
	black --check src/ tests/ scripts/

run-dev:
	python -m src.runner.run --config configs/experiments.yaml --split dev

run-test:
	python -m src.runner.run --config configs/experiments.yaml --split test --unlock-test

check-budget:
	python scripts/check_budget.py --config configs/experiments.yaml

build-index:
	python scripts/build_index.py --config configs/rag.yaml

clean:
	rm -rf outputs/
	rm -rf .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docs:
	python scripts/export_tables.py --run-id main_v1 --output docs/

pre-flight:
	python -m src.validate_data --items data/dummy/items.jsonl --evidence data/dummy/evidence.jsonl --corpus data/dummy/corpus.jsonl