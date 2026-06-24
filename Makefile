SHELL := /usr/bin/env bash

.PHONY: deps fmt fmt-check lint test openapi-validate compose-up compose-down dev inotify-check inotify-apply

PYTHON ?= python3

# Install dev dependencies into the active environment.
deps:
	$(PYTHON) -m pip install -U pip
	$(PYTHON) -m pip install -r requirements-dev.txt
	$(PYTHON) -m pip install -e .

fmt:
	$(PYTHON) -m ruff format .

fmt-check:
	$(PYTHON) -m ruff format --check .

lint:
	$(PYTHON) -m ruff check .

test:
	PYTHONPATH=$(PWD)/src $(PYTHON) -m pytest -q

openapi-validate:
	$(PYTHON) scripts/validate_openapi.py spec/openapi.yaml

compose-up:
	docker compose up -d

compose-logs:
	docker compose logs -f --tail=200

compose-down:
	docker compose down

# Run the backend server
dev:
	$(PYTHON) -m handsfree.server

# Diagnose inotify usage/limits (no root required)
inotify-check:
	bash scripts/inotify_doctor.sh check

# Apply persistent inotify limits (requires sudo/root)
inotify-apply:
	bash scripts/inotify_doctor.sh apply
