# PowerShell Progress & Logging utilities for consistent CI/local UX
# Requires: PowerShell 7+

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Start-TaskLogging {
    [CmdletBinding()]
    param(
        [Parameter()][string]$Name = 'Task',
        [Parameter()][string]$LogDir = (Join-Path -Path (Resolve-Path (Join-Path $PSScriptRoot '..' '..')).Path -ChildPath 'artifacts/logs')
    )
    if (-not (Test-Path -LiteralPath $LogDir)) {
        New-Item -ItemType Directory -Path $LogDir | Out-Null
    }
    $timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $safeName = ($Name -replace '[^a-zA-Z0-9_-]', '-')
    $logPath = Join-Path -Path $LogDir -ChildPath "$timestamp-$safeName.log"
    try {
        Start-Transcript -Path $logPath -Force | Out-Null
    } catch {
        Write-Warning "Start-Transcript failed: $($_.Exception.Message)"
    }
    return $logPath
}

function Stop-TaskLogging {
    [CmdletBinding()]
    param()
    try {
        Stop-Transcript | Out-Null
    } catch {
        # Non-fatal if transcript wasn't started
        Write-Verbose "Stop-Transcript skipped: $($_.Exception.Message)"
    }
}

function New-ProgressContext {
    [CmdletBinding()] 
    param(
        [Parameter(Mandatory)][string]$Activity,
        [Parameter()][string]$Status = 'Starting...',
        [Parameter()][int]$Id = 1,
        [Parameter()][int]$ParentId = -1
    )
    $ctx = [ordered]@{
        Id = $Id
        ParentId = $ParentId
        Activity = $Activity
        PercentComplete = 0
        Status = $Status
    }
    Write-Progress -Id $ctx.Id -ParentId $ctx.ParentId -Activity $ctx.Activity -Status $ctx.Status -PercentComplete $ctx.PercentComplete
    return $ctx
}

function Set-Progress {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][hashtable]$Context,
        [Parameter(Mandatory)][ValidateRange(0,100)][int]$PercentComplete,
        [Parameter()][string]$Status
    )
    $Context.PercentComplete = $PercentComplete
    if ($PSBoundParameters.ContainsKey('Status')) { $Context.Status = $Status }
    Write-Progress -Id $Context.Id -ParentId $Context.ParentId -Activity $Context.Activity -Status $Context.Status -PercentComplete $Context.PercentComplete
}

function Complete-Progress {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][hashtable]$Context
    )
    try {
        Write-Progress -Id $Context.Id -Activity $Context.Activity -Completed -Status 'Done'
    } catch {
        Write-Verbose "Write-Progress complete failed: $($_.Exception.Message)"
    }
}

Export-ModuleMember -Function Start-TaskLogging, Stop-TaskLogging, New-ProgressContext, Set-Progress, Complete-Progress
