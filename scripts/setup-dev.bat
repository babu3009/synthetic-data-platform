@echo off
REM Development setup script for Synthetic Data Platform (Windows)

echo 🚀 Setting up Synthetic Data Platform development environment...

REM Establish root (handles spaces in path)
set "ROOT=%~dp0"
pushd "%ROOT%" >nul

REM Check if required tools are installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is required but not installed. Aborting.
    exit /b 1
)

docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Compose is required but not installed. Aborting.
    exit /b 1
)

REM Backend setup
echo 📦 Setting up backend...
pushd "%ROOT%apps\backend" >nul
if not exist ".env" (
    copy .env.example .env
    echo ✅ Created backend .env file from template
)

REM Check for Poetry
poetry --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 📥 Poetry not found. Please install Poetry manually.
    echo Visit: https://python-poetry.org/docs/#installation
    pause
)

echo 📦 Installing backend dependencies...
poetry install

REM Frontend setup
echo 📦 Setting up frontend...
popd & pushd "%ROOT%apps\frontend" >nul

if not exist ".env" (
    copy .env.example .env
    echo ✅ Created frontend .env file from template
)

REM Check for pnpm
pnpm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 📥 Installing pnpm...
    npm install -g pnpm
)

echo 📦 Installing frontend dependencies...
pnpm install

REM Infrastructure setup
echo 🏗️ Setting up infrastructure...
popd & pushd "%ROOT%infra" >nul
if not exist ".env" (
    copy .env.example .env
    echo ✅ Created infrastructure .env file from template
)

REM Pre-commit setup
echo 🔧 Setting up pre-commit hooks...
popd & pushd "%ROOT%" >nul
pip install pre-commit
pre-commit install

echo 🎉 Development environment setup complete!
popd >nul
echo.
echo Next steps:
echo 1. Start infrastructure: make infra-up
echo 2. Start backend: make backend-dev
echo 3. Start frontend: make frontend-dev
echo.
echo Or start everything at once: make dev
pause