#Requires -Version 5.1

<#
.SYNOPSIS
Validates the AI Flywheel Windows bootstrap for parse errors and PowerShell best-practice violations.

.DESCRIPTION
Runs the built-in PowerShell parser against the Windows bootstrap, then runs
PSScriptAnalyzer with the repository-owned settings, and finally verifies that
comment-based help is discoverable. The command fails when parsing fails,
PSScriptAnalyzer is unavailable, analyzer Error/Warning diagnostics are returned,
or comment-based help is missing.

When no paths are provided, the validator resolves the bootstrap script and analyzer
settings relative to the repository checkout. Explicit paths are supported for
validating downloaded artifacts outside a repository checkout.

.PARAMETER ScriptPath
Path to the PowerShell bootstrap script to validate. Defaults to
scripts\install-ai-flywheel.ps1 relative to the repository root.

.PARAMETER SettingsPath
Path to the PSScriptAnalyzer settings file. Defaults to
PSScriptAnalyzerSettings.psd1 relative to the repository root.

.EXAMPLE
.\tools\validate-powershell.ps1

Validates the bootstrap script from a repository checkout.

.EXAMPLE
.\validate-powershell.ps1 -ScriptPath .\install-ai-flywheel.ps1 -SettingsPath .\PSScriptAnalyzerSettings.psd1

Validates downloaded bootstrap artifacts from an arbitrary directory.
#>

[CmdletBinding()]
param(
    [Parameter()]
    [ValidateNotNullOrEmpty()]
    [string]$ScriptPath,

    [Parameter()]
    [ValidateNotNullOrEmpty()]
    [string]$SettingsPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = (Resolve-Path -LiteralPath (Join-Path -Path $PSScriptRoot -ChildPath '..')).Path
if ([string]::IsNullOrWhiteSpace($ScriptPath)) {
    $ScriptPath = Join-Path -Path $repositoryRoot -ChildPath 'scripts\install-ai-flywheel.ps1'
}
if ([string]::IsNullOrWhiteSpace($SettingsPath)) {
    $SettingsPath = Join-Path -Path $repositoryRoot -ChildPath 'PSScriptAnalyzerSettings.psd1'
}

$resolvedScriptPath = (Resolve-Path -LiteralPath $ScriptPath).Path
$resolvedSettingsPath = (Resolve-Path -LiteralPath $SettingsPath).Path

$tokens = $null
$parseErrors = $null
[System.Management.Automation.Language.Parser]::ParseFile(
    $resolvedScriptPath,
    [ref]$tokens,
    [ref]$parseErrors
) | Out-Null

if ($parseErrors.Count -gt 0) {
    $parseErrors | Format-Table -AutoSize
    throw "PowerShell parser reported $($parseErrors.Count) error(s)."
}

$analyzer = Get-Module -ListAvailable -Name PSScriptAnalyzer |
    Sort-Object -Property Version -Descending |
    Select-Object -First 1
if (-not $analyzer) {
    throw 'PSScriptAnalyzer is required. Install with: Install-Module PSScriptAnalyzer -Scope CurrentUser'
}

Import-Module -Name $analyzer.Path -Force
$diagnostics = @(
    Invoke-ScriptAnalyzer -Path $resolvedScriptPath -Settings $resolvedSettingsPath
)
if ($diagnostics.Count -gt 0) {
    $diagnostics | Format-Table -Property RuleName, Severity, Line, Message -AutoSize -Wrap
    throw "PSScriptAnalyzer reported $($diagnostics.Count) error/warning diagnostic(s)."
}

$help = Get-Help -Name $resolvedScriptPath -Full
if ([string]::IsNullOrWhiteSpace($help.Synopsis) -or $help.Synopsis -eq $resolvedScriptPath) {
    throw 'Bootstrap comment-based help is missing or invalid.'
}

Write-Output 'PowerShell validation passed.'
