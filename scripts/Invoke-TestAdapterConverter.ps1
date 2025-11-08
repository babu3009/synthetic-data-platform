#!/usr/bin/env pwsh
<#
.SYNOPSIS
Wrapper to run the test adapter converter with consistent progress + logging UX.

.DESCRIPTION
Demonstrates usage of ProgressTools module: transcript logging, hierarchical progress bars, and structured error reporting.

.PARAMETER InputDirectory
Path to input test adapter JSON files.

.PARAMETER OutputDirectory
Destination for converted artifacts.

.PARAMETER DryRun
If specified, parses and validates without writing output.

.EXAMPLE
pwsh ./scripts/Invoke-TestAdapterConverter.ps1 -InputDirectory ./testing/adapters -OutputDirectory ./testing/converted

.NOTES
Exit codes: 0 success, 2 validation error, 3 unexpected failure.
#>
param(
    [Parameter(Mandatory)][string]$InputDirectory,
    [Parameter(Mandatory)][string]$OutputDirectory,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Import progress module
Import-Module -Force (Join-Path $PSScriptRoot 'ProgressTools' 'ProgressTools.psm1')

$logPath = Start-TaskLogging -Name 'test-adapter-converter'
Write-Host "[INFO] Log: $logPath" -ForegroundColor Cyan

if (-not (Test-Path -LiteralPath $InputDirectory)) {
    Write-Error "InputDirectory '$InputDirectory' does not exist."; Stop-TaskLogging; exit 2
}
if (-not (Test-Path -LiteralPath $OutputDirectory)) {
    New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
}

$rootCtx = New-ProgressContext -Activity 'Adapter Conversion' -Status 'Scanning input' -Id 1

$files = Get-ChildItem -LiteralPath $InputDirectory -Filter '*.json' -File -ErrorAction SilentlyContinue
if ($files.Count -eq 0) {
    Set-Progress -Context $rootCtx -PercentComplete 0 -Status 'No input files found'; Complete-Progress -Context $rootCtx; Stop-TaskLogging; exit 0
}

$convertCtx = New-ProgressContext -Activity 'Converting files' -Status 'Initializing' -Id 2 -ParentId 1

$index = 0
foreach ($file in $files) {
    $index++
    $percent = [int](($index / $files.Count) * 100)
    Set-Progress -Context $convertCtx -PercentComplete $percent -Status "Processing $($file.Name) ($index/$($files.Count))"
    try {
        $json = Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json -ErrorAction Stop
    } catch {
        Write-Warning "Failed to parse JSON for $($file.Name): $($_.Exception.Message)"
        continue
    }

    # Simulated transformation: ensure required properties exist
    if (-not $json.name) {
        Write-Warning "Missing 'name' property in $($file.Name)"; continue
    }
    $outObj = [ordered]@{
        adapterName = $json.name
        originalFile = $file.Name
        timestamp = (Get-Date).ToString('o')
        dryRun = [bool]$DryRun
    }
    if (-not $DryRun) {
        $outPath = Join-Path $OutputDirectory ($file.BaseName + '.converted.json')
        $outObj | ConvertTo-Json -Depth 10 | Out-File -FilePath $outPath -Encoding UTF8
    }
}

Complete-Progress -Context $convertCtx
Set-Progress -Context $rootCtx -PercentComplete 100 -Status 'Done'
Complete-Progress -Context $rootCtx
Stop-TaskLogging
Write-Host "[INFO] Conversion complete" -ForegroundColor Green
exit 0
