Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Describe 'ProgressTools Module' {
    BeforeAll {
        Import-Module -Force (Join-Path $PSScriptRoot '..' '..' 'scripts' 'ProgressTools' 'ProgressTools.psm1')
    }

    It 'Start-TaskLogging creates a transcript log file and returns its path' {
        $logPath = Start-TaskLogging -Name 'unit-test'
        Test-Path $logPath | Should -BeTrue
        Stop-TaskLogging
    }

    It 'New-ProgressContext initializes fields and Set-Progress updates percent' {
        $ctx = New-ProgressContext -Activity 'Test Activity' -Status 'Init' -Id 42
        $ctx.Activity | Should -Be 'Test Activity'
        $ctx.PercentComplete | Should -Be 0
        Set-Progress -Context $ctx -PercentComplete 75 -Status 'Mostly Done'
        $ctx.PercentComplete | Should -Be 75
        Complete-Progress -Context $ctx
    }
}
