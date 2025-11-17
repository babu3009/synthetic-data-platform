# PowerShell script to start the backend with proper error logging
# Works around Windows multiprocessing issues with uvicorn

$ErrorActionPreference = "Stop"

Push-Location $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Starting Synthetic Data Platform API" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Logs will be written to:" -ForegroundColor Yellow
Write-Host "  - logs/app.log (all logs)" -ForegroundColor Yellow
Write-Host "  - logs/errors.log (errors with tracebacks)" -ForegroundColor Yellow
Write-Host ""

# Activate conda environment and start uvicorn
# Using --reload-dir limits what files are watched, reducing issues
& "C:\ProgramData\miniforge3\Scripts\conda.exe" run -n conda-synthetic-data `
    uvicorn app.main:app `
    --host 127.0.0.1 `
    --port 8000 `
    --reload `
    --reload-dir app `
    --log-level info

Pop-Location
