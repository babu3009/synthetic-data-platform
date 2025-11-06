# Synthetic Data Platform

A modern monorepo for generating and managing synthetic data using FastAPI, React, and supporting infrastructure.

## Architecture

```
synthetic-data-platform/
├── apps/
│   ├── backend/          # FastAPI application
│   └── frontend/         # React + Vite application
├── infra/               # Infrastructure configuration
├── .devcontainer/       # Development container setup
└── .github/workflows/   # CI/CD pipelines
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- Poetry (for Python dependency management)
- pnpm (for Node.js dependency management)

### Development Setup

1. **Clone and setup the repository:**
   ```bash
   git clone <repository-url>
   cd synthetic-data-platform
   ```

2. **Start infrastructure services:**
   ```bash
   make infra-up
   ```

3. **Setup backend:**
   ```bash
   make backend-setup
   make backend-dev
   ```

4. **Setup frontend:**
   ```bash
   make frontend-setup
   make frontend-dev
   ```

### Available Commands

```bash
# Development
make dev              # Start all services in development mode
make backend-dev      # Start backend development server
make frontend-dev     # Start frontend development server

# Infrastructure
make infra-up         # Start infrastructure services (Postgres, Redis, MinIO)
make infra-down       # Stop infrastructure services

# Testing
make test             # Run all tests
make backend-test     # Run backend tests
make frontend-test    # Run frontend tests

# Code Quality
make lint             # Run all linters
make fmt              # Format all code
make type-check       # Run type checking

# Database
make migrate          # Run database migrations
make seed             # Seed database with sample data
```

## Services

- **Backend API**: http://localhost:8000
  - Health check: http://localhost:8000/health
  - API docs: http://localhost:8000/docs
- **Frontend**: http://localhost:3000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **MinIO**: http://localhost:9000 (admin: minioadmin/minioadmin)

## Technology Stack

### Backend
- FastAPI (Python 3.11)
- Pydantic v2
- SQLAlchemy 2.x
- Alembic (migrations)
- RQ (Redis Queue)
- uvicorn (ASGI server)
- pyarrow, pandas, openpyxl (data processing)
- faker, mimesis (synthetic data generation)

### Frontend
- React 18
- Vite (build tool)
- TypeScript
- Bootstrap 5
- React Router
- React Query (TanStack Query)
- React Hook Form
- Recharts (charts)
- ReactFlow (flow diagrams)

#### Wizard features
- Entities: create/import via DDL or JSON; manual field designer
- Diagram: visualize tables and relationships; auto-layout with ReactFlow
- Providers & PII: per-column provider selection (faker, pattern, sequence, categorical, expression, geo, checksum-valid, reference, empirical), JSON config with inline validation, PII toggle with subtype, bulk auto-suggest via backend with confirmation diff, and save
- Rules: split editor for YAML/JSON rules with inline linting (implication, uniqueness, distribution, temporal), one-click dry-run validation via POST /api/v1/validate with compact report for sample vs final data

### Infrastructure
- PostgreSQL 15
- Redis 7
- MinIO (S3-compatible storage)
- Docker & Docker Compose

### Code Quality
- **Backend**: ruff, black, mypy, pytest
- **Frontend**: ESLint, Prettier, TypeScript
- **Pre-commit hooks**: Automated code quality checks