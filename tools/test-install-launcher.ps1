#Requires -Version 5.1

<#
.SYNOPSIS
Validates the public AI Flywheel PowerShell install launcher.

.DESCRIPTION
Verifies that install.ps1 is safe for the `irm ... | iex` delivery pattern. The
test confirms the launcher has no top-level parameter block, runs in an isolated
child scope, pins an immutable canonical installer commit, delegates to the
canonical installer script, and does not embed Flywheel installation logic.
#>

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$launcherPath = Join-Path $repositoryRoot 'install.ps1'
$launcherText = Get-Content -LiteralPath $launcherPath -Raw -ErrorAction Stop

$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $launcherPath,
    [ref]$tokens,
    [ref]$parseErrors
)

if ($parseErrors.Count -gt 0) {
    throw "Public install launcher contains $($parseErrors.Count) parse error(s)."
}

if ($null -ne $ast.ParamBlock) {
    throw 'Public install launcher must not have a top-level parameter block when delivered through Invoke-Expression.'
}

if (-not $launcherText.Contains('& {')) {
    throw 'Public install launcher must isolate execution in a child script scope.'
}

if ($launcherText -notmatch "installerCommit\s*=\s*'[0-9a-f]{40}'") {
    throw 'Public install launcher must pin an immutable canonical installer commit.'
}

if (-not $launcherText.Contains('/scripts/install-ai-flywheel.ps1')) {
    throw 'Public install launcher must delegate to the canonical installer script.'
}

foreach ($forbidden in @('Invoke-AIFlywheelBootstrap', 'start-execution', 'FrameworkRef', 'application_missions_allowed')) {
    if ($launcherText.Contains($forbidden)) {
        throw "Public install launcher contains canonical installer logic: $forbidden"
    }
}

Write-Output 'Public install launcher tests passed.'
