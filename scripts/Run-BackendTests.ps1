param(
    [string]$BackendDir = "C:\Code\python\synthetic-data-platform\apps\backend",
    [string[]]$PytestArgs = @("-q", "tests"),
    [string]$PythonExe = "C:\Users\Isaiyavan Karan\.conda\envs\conda-synthetic-data\python.exe"
)

Write-Host "Running backend tests via PowerShell script..." -ForegroundColor Cyan

# Ensure backend directory exists
if (-not (Test-Path $BackendDir)) {
    Write-Error "BackendDir not found: $BackendDir"
    exit 1
}

Push-Location $BackendDir
$start = Get-Date

# Prefer `pytest` if on PATH; otherwise use `python -m pytest`
$exit = 0
try {
    if (Test-Path $PythonExe) {
    & $PythonExe -m pytest @PytestArgs
        $exit = $LASTEXITCODE
        if ($exit -eq 9009 -or $exit -eq 127) {
            Write-Warning "Primary PythonExe failed to launch (exit $exit); attempting fallback search."        
        }
        else { return }
    }
    if ($exit -ne 0) {
        if (Get-Command pytest -ErrorAction SilentlyContinue) {
            & pytest @PytestArgs
            $exit = $LASTEXITCODE
            return
        }
        elseif (Get-Command python -ErrorAction SilentlyContinue) {
            & python -m pytest @PytestArgs
            $exit = $LASTEXITCODE
            return
        }
        else {
            Write-Error "No suitable Python/pytest executable found after fallbacks."
            $exit = 1
        }
    }
}
catch {
    Write-Error $_
    $exit = 1
}
finally {
    Pop-Location
}

$duration = (Get-Date) - $start
if ($exit -eq 0) {
    Write-Host "`n=== BACKEND TESTS PASSED ===" -ForegroundColor Green
    Write-Host "Duration: $($duration.ToString())" -ForegroundColor Green
} else {
    Write-Host "`n=== BACKEND TESTS FAILED (exit code $exit) ===" -ForegroundColor Red
    Write-Host "Duration: $($duration.ToString())" -ForegroundColor Red
}

exit $exit
