.PHONY: help install dev build serve test lint fmt check qa clean ipfs deploy token

VENV := .venv
PYTHON := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip
PORT ?= 5000

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: $(VENV)/bin/activate ## Install all dependencies, IPFS, udev rules, and git hooks
	@echo "USB device access requires your password (sudo)."
	@echo "Enter it now so the rest of the install runs unattended."
	@echo ""
	@sudo -v
	@echo ""
	@echo "==> [1/5] Installing Python dependencies..."
	$(PIP) install -q -r requirements.txt
	$(PIP) install -q pytest ruff
	@echo "==> [2/5] Installing frontend dependencies..."
	@. scripts/ensure-node.sh && cd frontend && npm install
	@echo "==> [3/5] Setting up IPFS..."
	bash scripts/setup-ipfs.sh
	@echo "==> [4/5] Configuring USB device access..."
	bash scripts/setup-udev.sh
	@echo "==> [5/5] Installing git hooks..."
	bash scripts/setup-hooks.sh
	@echo ""
	@echo "OSmosis installed. Run 'make serve' to start."

$(VENV)/bin/activate:
	python3 -m venv $(VENV)

build: ## Build Vue frontend
	@. scripts/ensure-node.sh && cd frontend && npm run build

ipfs: ## Ensure IPFS daemon is running
	@export PATH="$$HOME/.local/bin:$$PATH"; \
	if command -v ipfs >/dev/null 2>&1 && ! ipfs id >/dev/null 2>&1; then \
		echo "Starting IPFS daemon..."; \
		ipfs daemon >/dev/null 2>&1 & \
		sleep 3; \
		echo "IPFS daemon running."; \
	fi

serve: build ipfs ## Build frontend, start IPFS, and start the server
	PATH="$$HOME/.local/bin:$$PATH" PYTHONPATH=$(CURDIR) $(PYTHON) web/app.py

dev: ipfs ## Start Flask backend only (use with: cd frontend && npm run dev)
	PATH="$$HOME/.local/bin:$$PATH" PYTHONPATH=$(CURDIR) $(PYTHON) web/app.py

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

qa: lint test ## Full QA: lint, tests, npm audit, pip audit
	@echo ""
	@echo "==> npm audit..."
	cd frontend && npm audit
	@echo ""
	@echo "==> pip audit..."
	$(PIP) install -q pip-audit 2>/dev/null; $(VENV)/bin/pip-audit -r requirements.txt || true
	@echo ""
	@echo "QA complete."

deploy: build ## Production deploy: build + nginx + firewall + fail2ban
	sudo bash scripts/setup-nginx.sh
	sudo bash scripts/setup-firewall.sh
	sudo bash scripts/setup-fail2ban.sh
	@echo ""
	@echo "Production deployment complete."
	@echo "Start the backend:  make serve"
	@echo "Generate auth token: make token"

token: ## Generate an auth token for remote access
	$(PYTHON) -m web.security --generate-token

clean: ## Remove build artifacts
	rm -rf web/static/dist/assets web/static/dist/index.html
	rm -rf frontend/node_modules/.vite
