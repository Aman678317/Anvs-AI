# ==============================================================================
# Multilingual AI Meeting Platform - Development Automation Makefile
# ==============================================================================

.PHONY: help install up down restart dev test test-unit test-integration test-ai lint format typecheck db-migrate db-upgrade clean

SHELL := /bin/bash
PYTHON := python
PNPM := pnpm

help:
	@echo "Multilingual AI Meeting Platform - Available Commands:"
	@echo "  make install         Install all Node.js and Python dependencies"
	@echo "  make up              Start local Docker services (Postgres, Redis, LiveKit, Jaeger)"
	@echo "  make down            Stop local Docker services"
	@echo "  make restart         Restart local Docker services"
	@echo "  make dev             Start web frontend and API in development mode"
	@echo "  make db-migrate      Generate new Alembic database migration"
	@echo "  make db-upgrade      Apply pending Alembic database migrations"
	@echo "  make lint            Run linter checks across TypeScript and Python"
	@echo "  make format          Auto-format TypeScript and Python code"
	@echo "  make typecheck       Run TypeScript tsc and Python mypy typechecks"
	@echo "  make test            Run all unit and integration test suites"
	@echo "  make test-ai         Run speech, translation, and model benchmark evaluations"
	@echo "  make clean           Remove temporary cache files, build outputs, and logs"

install:
	@echo "--> Installing Node.js dependencies with pnpm..."
	$(PNPM) install
	@echo "--> Installing Python root & service dependencies..."
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"

up:
	@echo "--> Starting local Docker containers..."
	docker compose up -d

down:
	@echo "--> Stopping local Docker containers..."
	docker compose down

restart:
	@echo "--> Restarting local Docker containers..."
	docker compose restart

dev:
	@echo "--> Starting Turborepo / development servers..."
	$(PNPM) run dev

db-migrate:
	@echo "--> Generating Alembic migration..."
	$(PYTHON) -m alembic revision --autogenerate

db-upgrade:
	@echo "--> Applying database migrations..."
	$(PYTHON) -m alembic upgrade head

lint:
	@echo "--> Running Ruff linter on Python code..."
	$(PYTHON) -m ruff check .
	@echo "--> Running ESLint on TypeScript code..."
	$(PNPM) run lint

format:
	@echo "--> Auto-formatting Python code with Ruff..."
	$(PYTHON) -m ruff format .
	@echo "--> Auto-formatting TypeScript/JSON with Prettier..."
	$(PNPM) run format

typecheck:
	@echo "--> Running Mypy on Python code..."
	$(PYTHON) -m mypy services packages
	@echo "--> Running tsc on TypeScript apps & packages..."
	$(PNPM) run typecheck

test:
	@echo "--> Running pytest suite..."
	$(PYTHON) -m pytest tests/unit tests/integration tests/contract -v
	@echo "--> Running web vitest suite..."
	$(PNPM) run test

test-ai:
	@echo "--> Running AI model benchmark & evaluation suite..."
	$(PYTHON) -m pytest tests/ai -v -s

clean:
	@echo "--> Cleaning cache and transient artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean completed."
