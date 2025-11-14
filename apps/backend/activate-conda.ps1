# Activate the conda-synthetic-data Conda environment

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Synthetic Data Platform - Conda Env  " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Activating conda-synthetic-data environment..." -ForegroundColor Green

# Resolve conda path (handle spaces in user profile paths)
$condaPath = "C:\ProgramData\miniforge3\Scripts\conda.exe"
if (-not (Test-Path $condaPath)) {
    $detected = (Get-Command conda -ErrorAction SilentlyContinue)?.Source
    if ($detected) { $condaPath = $detected }
}

if (Test-Path $condaPath) {
    Write-Host "✓ Using conda at: $condaPath" -ForegroundColor Green

    # Prefer 'conda activate' only if shell functions are initialized; fall back to 'conda run'
    try {
        & "$condaPath" info > $null 2>&1
        # Attempt normal activation (works when conda hook already loaded for shell)
        conda activate conda-synthetic-data 2>$null
    } catch {
        Write-Host "⚠️  Direct activation failed; falling back to 'conda run' shim" -ForegroundColor Yellow
    }

    # Display Python version using conda run to avoid issues with spaces in path
    Write-Host ""; Write-Host "Environment activated (or shimmed)! 🚀" -ForegroundColor Green; Write-Host ""
    Write-Host "Python version:" -ForegroundColor Cyan
    & "$condaPath" run -n conda-synthetic-data python --version
    Write-Host ""; Write-Host "Environment location:" -ForegroundColor Cyan
    & "$condaPath" info --envs | Select-String "conda-synthetic-data"
    Write-Host ""; Write-Host "To deactivate (if fully activated), run:" -ForegroundColor Yellow
    Write-Host "  conda deactivate" -ForegroundColor White
} else {
    Write-Host "✗ Conda not found at: $condaPath" -ForegroundColor Red
    Write-Host ""; Write-Host "Please ensure miniforge3 is installed or activate manually:" -ForegroundColor Yellow
    Write-Host "  conda activate conda-synthetic-data" -ForegroundColor White
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
