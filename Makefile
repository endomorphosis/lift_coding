SHELL := /usr/bin/env bash

.PHONY: deps fmt fmt-check lint test openapi-validate compose-up compose-down dev migrate migrate-test

PYTHON ?= python3
DB_PATH ?= data/handsfree.duckdb

# Install dev dependencies into the active environment.
deps:
	$(PYTHON) -m pip install -U pip
	$(PYTHON) -m pip install -r requirements-dev.txt

fmt:
	$(PYTHON) -m ruff format .

fmt-check:
	$(PYTHON) -m ruff format --check .

lint:
	$(PYTHON) -m ruff check .

test:
	$(PYTHON) -m pytest -q

openapi-validate:
	$(PYTHON) scripts/validate_openapi.py spec/openapi.yaml

compose-up:
	docker compose up -d

compose-down:
	docker compose down

# Run database migrations
migrate:
	$(PYTHON) scripts/migrate.py --db-path $(DB_PATH)

# Run database migrations for test database (in-memory or separate file)
migrate-test:
	$(PYTHON) scripts/migrate.py --db-path :memory:

# Placeholder: implemented in PR-002.
dev:
	@echo "Backend server will be added in PR-002 (see implementation_plan/prs/PR-002-backend-api-skeleton.md)"
