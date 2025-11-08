param(
    [string]$CondaPath = "C:\ProgramData\miniforge3",
    [string]$EnvName = "conda-synthetic-data",
    [string]$BackendDir = "C:\Code\python\synthetic-data-platform\apps\backend",
    [string]$PytestArgs = "-q"
)

# Try to source conda hook for pwsh-based activation
$condaHook = Join-Path $CondaPath "shell\condabin\conda-hook.ps1"
if (Test-Path $condaHook) {
    . $condaHook
} else {
    Write-Host "Conda hook not found at $condaHook" -ForegroundColor Yellow
}

# Activate the environment
try {
    conda activate $EnvName
} catch {
    Write-Host "Failed to activate conda env '$EnvName' - continuing; pytest may fail." -ForegroundColor Yellow
}

# Run tests in backend directory
Push-Location $BackendDir
$start = Get-Date
try {
    & pytest $PytestArgs
    $exit = $LASTEXITCODE
} catch {
    Write-Error $_
    $exit = 1
} finally {
    Pop-Location
}
$duration = (Get-Date) - $start

# Notification and summary
if ($exit -eq 0) {
    Write-Host "`n=== BACKEND TESTS PASSED ===" -ForegroundColor Green
    Write-Host "Duration: $($duration.ToString())" -ForegroundColor Green
    # Try BurntToast for a real toast notification if available
    if (Get-Module -ListAvailable -Name BurntToast) {
        Import-Module BurntToast -ErrorAction SilentlyContinue
        New-BurntToastNotification -Text "Backend tests passed", "All tests completed successfully"
    } else {
        # Audible beep as fallback
        try { [console]::beep(800,300) } catch { Write-Host "(beep)" }
    }
} else {
    Write-Host "`n=== BACKEND TESTS FAILED (exit code $exit) ===" -ForegroundColor Red
    Write-Host "Duration: $($duration.ToString())" -ForegroundColor Red
    if (Get-Module -ListAvailable -Name BurntToast) {
        Import-Module BurntToast -ErrorAction SilentlyContinue
        New-BurntToastNotification -Text "Backend tests failed", "Exit code: $exit"
    } else {
        for ($i=0; $i -lt 3; $i++) { try { [console]::beep(400,300) } catch { Write-Host "(beep)" }; Start-Sleep -Milliseconds 200 }
    }
}

# Exit with pytest's exit code so callers can detect failure
exit $exit
