#!/bin/bash

# Development setup script for Synthetic Data Platform

set -e

echo "🚀 Setting up Synthetic Data Platform development environment..."

# Check if required tools are installed
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed. Aborting." >&2; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose is required but not installed. Aborting." >&2; exit 1; }

# Backend setup
echo "📦 Setting up backend..."
cd apps/backend
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ Created backend .env file from template"
fi

# Install Poetry if not present
if ! command -v poetry &> /dev/null; then
    echo "📥 Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
fi

echo "📦 Installing backend dependencies..."
poetry install

# Frontend setup
echo "📦 Setting up frontend..."
cd ../frontend

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ Created frontend .env file from template"
fi

# Install pnpm if not present
if ! command -v pnpm &> /dev/null; then
    echo "📥 Installing pnpm..."
    npm install -g pnpm
fi

echo "📦 Installing frontend dependencies..."
pnpm install

# Infrastructure setup
echo "🏗️ Setting up infrastructure..."
cd ../../infra
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ Created infrastructure .env file from template"
fi

# Pre-commit setup
echo "🔧 Setting up pre-commit hooks..."
cd ..
pip install pre-commit
pre-commit install

echo "🎉 Development environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Start infrastructure: make infra-up"
echo "2. Start backend: make backend-dev"
echo "3. Start frontend: make frontend-dev"
echo ""
echo "Or start everything at once: make dev"