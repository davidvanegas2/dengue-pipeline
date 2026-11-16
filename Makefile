# Project shortcuts. On Windows without make, run the corresponding uv command.
.DEFAULT_GOAL := help
.PHONY: help install workshop facilitator pipeline pipeline-online format lint test test-fast workshop-check workshop-qr student-notebook ci clean

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies and pre-commit hooks
	uv sync
	uv run pre-commit install

workshop: ## Open the workshop notebook with exercises
	uv run marimo edit notebooks/workshop.py

facilitator: ## Open the solved facilitator notebook
	uv run marimo edit notebooks/workshop_facilitator.py

pipeline: ## Run the complete offline pipeline (bronze -> silver -> gold)
	uv run dengue-pipeline run

pipeline-online: ## Run the pipeline after refreshing IDEAM data online
	uv run dengue-pipeline -v run --refresh-ideam

format: ## Format and autofix Python and SQL
	uv run ruff format .
	uv run ruff check --fix .
	uv run sqlfluff fix sql

lint: ## Check style, types, SQL and notebooks
	uv run ruff check .
	uv run ruff format --check .
	uv run sqlfluff lint sql
	uv run mypy
	uv run marimo check notebooks
	uv run python scripts/generate_student_notebook.py --check

test: ## Run all tests with coverage
	uv run pytest --cov --cov-report=term-missing

test-fast: ## Run tests without network access or notebooks
	uv run pytest -m "not network and not slow"

workshop-check: ## Check workshop readiness offline, including notebook exercises
	uv sync --locked
	$(MAKE) lint
	uv run pytest -m "not network" --cov --cov-report=term-missing
	$(MAKE) pipeline

workshop-qr: ## Generate local QR images for the repository and molab links
	uv run scripts/generate_workshop_qr.py

student-notebook: ## Regenerate workshop.py from the facilitator notebook
	uv run python scripts/generate_student_notebook.py

ci: lint test ## Run the local quality checks and tests

clean: ## Remove the regenerable warehouse and tool caches
	rm -rf data/dengue.duckdb data/dengue.duckdb.wal .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov
