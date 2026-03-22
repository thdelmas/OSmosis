.PHONY: help install dev build serve test lint fmt check clean

VENV := .venv
PYTHON := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip
PORT ?= 5000

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: $(VENV)/bin/activate ## Install all dependencies and git hooks
	$(PIP) install -q -r requirements.txt
	$(PIP) install -q pytest ruff
	cd frontend && npm install
	bash scripts/setup-hooks.sh

$(VENV)/bin/activate:
	python3 -m venv $(VENV)

build: ## Build Vue frontend
	cd frontend && npm run build

serve: build ## Build frontend and start the server
	PYTHONPATH=$(CURDIR) $(PYTHON) web/app.py

dev: ## Start Flask backend only (use with: cd frontend && npm run dev)
	PYTHONPATH=$(CURDIR) $(PYTHON) web/app.py

test: ## Run test suite
	PYTHONPATH=$(CURDIR) $(PYTHON) -m pytest tests/ -q --tb=short

lint: ## Check code quality (ruff)
	$(VENV)/bin/ruff check .
	$(VENV)/bin/ruff format --check .

fmt: ## Auto-fix lint and formatting
	$(VENV)/bin/ruff check --fix .
	$(VENV)/bin/ruff format .

check: ## Run all pre-commit checks (lint + tests + file length)
	bash scripts/code-quality-check.sh

clean: ## Remove build artifacts
	rm -rf web/static/dist/assets web/static/dist/index.html
	rm -rf frontend/node_modules/.vite
