# Protocol Gate — developer task runner.
# Run `make help` for the list of targets.
.DEFAULT_GOAL := help
SHELL := /usr/bin/env bash

COMPOSE := docker compose -f infra/docker-compose.yml
PYTHONPATH := src:.
export PYTHONPATH

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## Install the package with dev + bench extras (editable)
	pip install -e ".[dev,bench]"

.PHONY: test
test: ## Run the full test suite
	pytest

.PHONY: test-unit
test-unit: ## Run only unit tests
	pytest tests/unit

.PHONY: test-property
test-property: ## Run only property-based tests
	pytest tests/property

.PHONY: test-integration
test-integration: ## Run only integration tests
	pytest tests/integration

.PHONY: lint
lint: ## Lint with ruff
	ruff check .

.PHONY: format
format: ## Auto-format with black + ruff --fix
	black .
	ruff check --fix .

.PHONY: typecheck
typecheck: ## Static type check with mypy
	mypy src

.PHONY: verify
verify: lint typecheck test ## Run lint + typecheck + tests

.PHONY: proofs
proofs: ## Model-check the TLA+ specification (requires tla2tools.jar)
	cd proofs && java -cp $${TLA_TOOLS:-tla2tools.jar} tla2sany.SANY ProtocolGate.tla
	cd proofs && java -cp $${TLA_TOOLS:-tla2tools.jar} tlc2.TLC -config ProtocolGate.cfg ProtocolGate.tla

.PHONY: experiments
experiments: ## Run the control-vs-experiment comparison
	python -m experiments.runner

.PHONY: bench
bench: ## Run the benchmark suite
	python -m benchmarks.runner --iterations 20 --output results/benchmark.json

.PHONY: run
run: ## Run the gate API locally with uvicorn
	uvicorn api.main:app --app-dir src --reload --port 8000

.PHONY: up
up: ## Start the full observability + inference stack
	$(COMPOSE) up -d

.PHONY: down
down: ## Stop the stack
	$(COMPOSE) down

.PHONY: logs
logs: ## Tail stack logs
	$(COMPOSE) logs -f

.PHONY: clean
clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist build results
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
