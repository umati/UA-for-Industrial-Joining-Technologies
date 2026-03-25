# =============================================================================
#  IJT Web Client — Makefile
#  Common development tasks for Linux / macOS / Docker / WSL.
#  Windows users: use `python run_all_tests.py`.
# =============================================================================

PYTHON   ?= python3
NPX      ?= npx
PIP      ?= $(PYTHON) -m pip

.DEFAULT_GOAL := help

# ── Help ─────────────────────────────────────────────────────────────────────
.PHONY: help
help:
	@echo ""
	@echo "  IJT Web Client — available make targets"
	@echo "  ----------------------------------------"
	@echo "  make setup          One-command project setup (venv + npm install)"
	@echo "  make test           Unit tests + smoke tests (fast, no server)"
	@echo "  make test-all       All tests (unit + live OPC UA + Playwright E2E)"
	@echo "  make test-live      Unit tests + live OPC UA integration tests"
	@echo "  make test-e2e       Unit tests + Playwright E2E (needs backend)"
	@echo "  make lint           ESLint + Python static checks"
	@echo "  make lint-fix       ESLint auto-fix"
	@echo "  make serve          Serve the frontend at http://localhost:3000"
	@echo "  make backend        Start the Python WebSocket backend"
	@echo "  make docker-build   Build the Docker image"
	@echo "  make docker-up      Start services with docker compose"
	@echo "  make docker-test    Run tests inside Docker"
	@echo "  make docker-down    Stop and remove Docker containers"
	@echo "  make clean          Remove generated files and caches"
	@echo ""

# ── Setup ────────────────────────────────────────────────────────────────────
.PHONY: setup
setup:
	$(PYTHON) setup_project.py

# ── Tests ────────────────────────────────────────────────────────────────────
.PHONY: test
test:
	$(PYTHON) run_all_tests.py

.PHONY: test-all
test-all:
	$(PYTHON) run_all_tests.py --all

.PHONY: test-live
test-live:
	$(PYTHON) run_all_tests.py --integration

.PHONY: test-e2e
test-e2e:
	$(PYTHON) run_all_tests.py --e2e

.PHONY: test-unit-python
test-unit-python:
	$(PYTHON) -m pytest tests/ -m "not integration and not live and not live_ws" -v --tb=short

.PHONY: test-unit-js
test-unit-js:
	npm run test:unit:js

.PHONY: test-smoke
test-smoke:
	$(NPX) playwright test --project=smoke --reporter=line

# ── Lint ─────────────────────────────────────────────────────────────────────
.PHONY: lint
lint:
	npm run lint
	$(PYTHON) -m py_compile src/Python/*.py src/scripts/*.py

.PHONY: lint-fix
lint-fix:
	npm run lint:fix

# ── Dev servers ──────────────────────────────────────────────────────────────
.PHONY: serve
serve:
	$(NPX) serve --listen tcp://127.0.0.1:3000 --no-clipboard .

.PHONY: backend
backend:
	$(PYTHON) index.py

# ── Docker ───────────────────────────────────────────────────────────────────
.PHONY: docker-build
docker-build:
	docker compose build

.PHONY: docker-up
docker-up:
	docker compose up -d

.PHONY: docker-test
docker-test:
	docker compose run --rm ijt_tests

.PHONY: docker-down
docker-down:
	docker compose down

# ── Clean ────────────────────────────────────────────────────────────────────
.PHONY: clean
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf test-results playwright-report .state/
	@echo "Clean done."
