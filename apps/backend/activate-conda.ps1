# Activate the conda-synthetic-data Conda environment

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Synthetic Data Platform - Conda Env  " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Activating conda-synthetic-data environment..." -ForegroundColor Green

# Check if conda is available
$condaPath = "C:\ProgramData\miniforge3\Scripts\conda.exe"
if (Test-Path $condaPath) {
    Write-Host "✓ Found miniforge3 at: $condaPath" -ForegroundColor Green
    
    # Activate the environment
    & $condaPath activate conda-synthetic-data
    
    Write-Host ""
    Write-Host "Environment activated! 🚀" -ForegroundColor Green
    Write-Host ""
    Write-Host "Python version:" -ForegroundColor Cyan
    python --version
    Write-Host ""
    Write-Host "Environment location:" -ForegroundColor Cyan
    & $condaPath info --envs | Select-String "conda-synthetic-data"
    Write-Host ""
    Write-Host "To deactivate, run:" -ForegroundColor Yellow
    Write-Host "  conda deactivate" -ForegroundColor White
} else {
    Write-Host "✗ Conda not found at: $condaPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please ensure miniforge3 is installed or activate manually:" -ForegroundColor Yellow
    Write-Host "  conda activate conda-synthetic-data" -ForegroundColor White
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
