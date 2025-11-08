Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Describe 'Invoke-TestAdapterConverter.ps1' {
    BeforeAll {
        $scriptPath = Join-Path $PSScriptRoot '..' '..' 'scripts' 'Invoke-TestAdapterConverter.ps1'
        $global:ConverterScript = $scriptPath
        $global:TempRoot = Join-Path $PSScriptRoot 'temp'
        if (Test-Path $global:TempRoot) { Remove-Item -Recurse -Force $global:TempRoot }
        New-Item -ItemType Directory -Path $global:TempRoot | Out-Null
    }

    BeforeEach {
        $inDir = Join-Path $global:TempRoot 'in'
        $outDir = Join-Path $global:TempRoot 'out'
        if (Test-Path $inDir) { Remove-Item -Recurse -Force $inDir }
        if (Test-Path $outDir) { Remove-Item -Recurse -Force $outDir }
        New-Item -ItemType Directory -Path $inDir | Out-Null
        New-Item -ItemType Directory -Path $outDir | Out-Null
        Set-Content -Path (Join-Path $inDir 'valid.json') -Value '{"name":"AdapterA"}' -Encoding UTF8
        Set-Content -Path (Join-Path $inDir 'invalid.json') -Value '{"foo":"bar"}' -Encoding UTF8
        $script:InDir = $inDir
        $script:OutDir = $outDir
    }

    It 'DryRun does not emit converted files' {
        pwsh -NoLogo -NoProfile -File $global:ConverterScript -InputDirectory $script:InDir -OutputDirectory $script:OutDir -DryRun
        $LASTEXITCODE | Should -Be 0
        (Get-ChildItem -LiteralPath $script:OutDir).Count | Should -Be 0
    }

    It 'Non-dry run converts valid file and skips invalid' {
        pwsh -NoLogo -NoProfile -File $global:ConverterScript -InputDirectory $script:InDir -OutputDirectory $script:OutDir
        $LASTEXITCODE | Should -Be 0
        $converted = Get-ChildItem -LiteralPath $script:OutDir -Filter '*.converted.json'
        $converted.Count | Should -Be 1
        $content = Get-Content -LiteralPath $converted[0].FullName -Raw | ConvertFrom-Json
        $content.adapterName | Should -Be 'AdapterA'
        $content.dryRun | Should -BeFalse
    }
}
