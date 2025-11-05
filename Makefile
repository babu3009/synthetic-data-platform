#!/usr/bin/env make

# Default target
.DEFAULT_GOAL := help

# Colors for output
CYAN := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
NC := \033[0m # No Color

# Project paths
BACKEND_DIR := apps/backend
FRONTEND_DIR := apps/frontend
INFRA_DIR := infra

# Help target
help: ## Show this help message
	@echo "$(CYAN)Synthetic Data Platform - Available Commands$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Development commands
dev: infra-up backend-dev-bg frontend-dev ## Start all services in development mode
	@echo "$(GREEN)All services started!$(NC)"
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"
	@echo "MinIO: http://localhost:9000"

backend-setup: ## Setup backend dependencies
	@echo "$(YELLOW)Setting up backend dependencies...$(NC)"
	cd $(BACKEND_DIR) && poetry install

frontend-setup: ## Setup frontend dependencies
	@echo "$(YELLOW)Setting up frontend dependencies...$(NC)"
	cd $(FRONTEND_DIR) && pnpm install

backend-dev: ## Start backend development server
	@echo "$(YELLOW)Starting backend development server...$(NC)"
	cd $(BACKEND_DIR) && poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

backend-dev-bg: ## Start backend development server in background
	@echo "$(YELLOW)Starting backend development server in background...$(NC)"
	cd $(BACKEND_DIR) && poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &

frontend-dev: ## Start frontend development server
	@echo "$(YELLOW)Starting frontend development server...$(NC)"
	cd $(FRONTEND_DIR) && pnpm dev

# Infrastructure commands
infra-up: ## Start infrastructure services (Postgres, Redis, MinIO)
	@echo "$(YELLOW)Starting infrastructure services...$(NC)"
	cd $(INFRA_DIR) && docker-compose up -d
	@echo "$(GREEN)Infrastructure services started!$(NC)"

infra-down: ## Stop infrastructure services
	@echo "$(YELLOW)Stopping infrastructure services...$(NC)"
	cd $(INFRA_DIR) && docker-compose down
	@echo "$(GREEN)Infrastructure services stopped!$(NC)"

infra-logs: ## Show infrastructure services logs
	cd $(INFRA_DIR) && docker-compose logs -f

# Testing commands
test: backend-test frontend-test ## Run all tests

backend-test: ## Run backend tests
	@echo "$(YELLOW)Running backend tests...$(NC)"
	cd $(BACKEND_DIR) && poetry run pytest

frontend-test: ## Run frontend tests
	@echo "$(YELLOW)Running frontend tests...$(NC)"
	cd $(FRONTEND_DIR) && pnpm test

# Code quality commands
lint: backend-lint frontend-lint ## Run all linters

backend-lint: ## Run backend linting
	@echo "$(YELLOW)Running backend linting...$(NC)"
	cd $(BACKEND_DIR) && poetry run ruff check .
	cd $(BACKEND_DIR) && poetry run mypy .

frontend-lint: ## Run frontend linting
	@echo "$(YELLOW)Running frontend linting...$(NC)"
	cd $(FRONTEND_DIR) && pnpm lint

fmt: backend-fmt frontend-fmt ## Format all code

backend-fmt: ## Format backend code
	@echo "$(YELLOW)Formatting backend code...$(NC)"
	cd $(BACKEND_DIR) && poetry run black .
	cd $(BACKEND_DIR) && poetry run ruff check --fix .

frontend-fmt: ## Format frontend code
	@echo "$(YELLOW)Formatting frontend code...$(NC)"
	cd $(FRONTEND_DIR) && pnpm format

type-check: ## Run type checking
	@echo "$(YELLOW)Running type checking...$(NC)"
	cd $(BACKEND_DIR) && poetry run mypy .
	cd $(FRONTEND_DIR) && pnpm type-check

# Database commands
migrate: ## Run database migrations
	@echo "$(YELLOW)Running database migrations...$(NC)"
	cd $(BACKEND_DIR) && poetry run alembic upgrade head

migrate-create: ## Create a new migration (use name=migration_name)
	@echo "$(YELLOW)Creating new migration...$(NC)"
	cd $(BACKEND_DIR) && poetry run alembic revision --autogenerate -m "$(name)"

seed: ## Seed database with sample data
	@echo "$(YELLOW)Seeding database...$(NC)"
	cd $(BACKEND_DIR) && poetry run python -m app.scripts.seed_db

db-setup: ## Setup database with initial migration
	@echo "$(YELLOW)Setting up database...$(NC)"
	cd $(BACKEND_DIR) && python setup_db.py

db-validate: ## Validate backend implementation
	@echo "$(YELLOW)Validating backend implementation...$(NC)"
	cd $(BACKEND_DIR) && python validate_implementation.py

# Database management
db-reset: ## Reset database (drop and recreate)
	@echo "$(RED)Resetting database...$(NC)"
	cd $(INFRA_DIR) && docker-compose exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS synthetic_data_platform;"
	cd $(INFRA_DIR) && docker-compose exec postgres psql -U postgres -c "CREATE DATABASE synthetic_data_platform;"
	$(MAKE) migrate
	$(MAKE) seed

# Build commands
build: build-backend build-frontend ## Build all applications

build-backend: ## Build backend Docker image
	@echo "$(YELLOW)Building backend Docker image...$(NC)"
	cd $(BACKEND_DIR) && docker build -t synthetic-data-platform/backend .

build-frontend: ## Build frontend for production
	@echo "$(YELLOW)Building frontend...$(NC)"
	cd $(FRONTEND_DIR) && pnpm build

# Cleanup commands
clean: ## Clean up build artifacts and caches
	@echo "$(YELLOW)Cleaning up...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true

# Development utilities
shell-backend: ## Open backend shell
	cd $(BACKEND_DIR) && poetry shell

shell-db: ## Open database shell
	cd $(INFRA_DIR) && docker-compose exec postgres psql -U postgres -d synthetic_data_platform

logs-backend: ## Show backend logs
	cd $(BACKEND_DIR) && tail -f app.log

# Pre-commit setup
setup-hooks: ## Setup pre-commit hooks
	@echo "$(YELLOW)Setting up pre-commit hooks...$(NC)"
	poetry run pre-commit install
	@echo "$(GREEN)Pre-commit hooks installed!$(NC)"

.PHONY: help dev backend-setup frontend-setup backend-dev backend-dev-bg frontend-dev infra-up infra-down infra-logs test backend-test frontend-test lint backend-lint frontend-lint fmt backend-fmt frontend-fmt type-check migrate migrate-create seed db-reset build build-backend build-frontend clean shell-backend shell-db logs-backend setup-hooks