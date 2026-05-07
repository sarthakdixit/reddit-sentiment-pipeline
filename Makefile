.PHONY: help up down lint format typecheck test test-unit test-integration check-architecture clean install ingest

help:
	@echo "Targets:"
	@echo "  install            Install dev dependencies into the active venv"
	@echo "  up                 Start local Docker services (azurite + postgres)"
	@echo "  down               Stop local Docker services"
	@echo "  lint               Run ruff and black checks"
	@echo "  format             Auto-format with ruff and black"
	@echo "  typecheck          Run mypy on src/"
	@echo "  test               Run all tests"
	@echo "  test-unit          Run unit tests only (no Docker)"
	@echo "  test-integration   Run integration tests (requires Docker)"
	@echo "  check-architecture Verify src/core/ has no infrastructure imports"
	@echo "  ingest             Run the ingestion pipeline"
	@echo "  clean              Remove caches and build artifacts"

install:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e ".[dev]"
	@echo ""
	@echo "Activate the venv with: source .venv/bin/activate"

up:
	docker compose up -d

down:
	docker compose down

lint:
	ruff check src tests scripts
	black --check src tests scripts
	bash scripts/check_no_comments.sh

format:
	ruff check --fix src tests scripts
	black src tests scripts

typecheck:
	mypy src

test:
	pytest

test-unit:
	pytest tests/unit -v

test-integration:
	pytest tests/integration -v -m integration

check-architecture:
	bash scripts/check_architecture.sh

ingest:
	APP_MODE=walking-skeleton python -m src.cli ingest --subreddit $${SUBREDDIT:-technology} --limit $${LIMIT:-3}

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov coverage.xml build dist
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
