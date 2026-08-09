#Requires -Version 5.1

<#
.SYNOPSIS
Runs dependency-free regression tests for the AI Flywheel Windows bootstrap.

.DESCRIPTION
Verifies CLI-source extraction and the boundary between framework installation and
Python CLI setup. Framework compatibility classification is exercised without
network access or repository mutation.
#>

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$bootstrapPath = Join-Path $repositoryRoot 'scripts\install-ai-flywheel.ps1'

function Assert-BootstrapTest {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][bool]$Condition,
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Message
    )
    if (-not $Condition) { throw $Message }
}

function New-BootstrapTestZip {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param(
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Path,
        [Parameter(Mandatory)][hashtable]$Entries
    )
    if (-not $PSCmdlet.ShouldProcess($Path, 'Create bootstrap regression-test ZIP archive')) { return }

    Add-Type -AssemblyName System.IO.Compression -ErrorAction Stop
    Add-Type -AssemblyName System.IO.Compression.FileSystem -ErrorAction Stop
    $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Create, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
    try {
        $zip = [System.IO.Compression.ZipArchive]::new($stream, [System.IO.Compression.ZipArchiveMode]::Create, $true)
        try {
            foreach ($name in @($Entries.Keys | Sort-Object)) {
                $entry = $zip.CreateEntry($name)
                $writer = [System.IO.StreamWriter]::new($entry.Open())
                try { $writer.Write([string]$Entries[$name]) } finally { $writer.Dispose() }
            }
        }
        finally { $zip.Dispose() }
    }
    finally { $stream.Dispose() }
}

function Set-TestFramework {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)][string]$InstallationVersion,
        [Parameter(Mandatory)][string]$ManifestVersion
    )
    $flywheel = Join-Path $Root '.flywheel'
    New-Item -ItemType Directory -Path $flywheel -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $flywheel 'installation.yaml') -Value "framework_version: $InstallationVersion" -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $flywheel 'manifest.yaml') -Value @(
        'schema_version: 1'
        'framework:'
        "  version: $ManifestVersion"
    ) -Encoding UTF8
}

. $bootstrapPath

$testRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('AIFW-tests-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Path $testRoot -Force | Out-Null

try {
    $sourceText = Get-Content -LiteralPath $bootstrapPath -Raw
    $parameterNames = @((Get-Command -Name $bootstrapPath).Parameters.Keys)
    foreach ($removedParameter in @('FrameworkVersion', 'FrameworkRef', 'FrameworkPath')) {
        Assert-BootstrapTest -Condition ($parameterNames -notcontains $removedParameter) -Message "Removed parameter remains exposed: $removedParameter"
    }

    Assert-BootstrapTest -Condition ($sourceText.Contains('fe11b801b5dfeef812377a978558fd563b67fa9e')) -Message 'Official framework installer commit is not pinned.'
    Assert-BootstrapTest -Condition ($sourceText.Contains('/scripts/install-framework.ps1')) -Message 'Bootstrap does not invoke the official framework installer.'
    $frameworkStageIndex = $sourceText.IndexOf('$script:CurrentStage = ''Framework''')
    $pythonStageIndex = $sourceText.IndexOf('$script:CurrentStage = ''Python''')
    Assert-BootstrapTest -Condition ($frameworkStageIndex -ge 0 -and $frameworkStageIndex -lt $pythonStageIndex) -Message 'Framework assurance must occur before Python detection.'
    foreach ($forbidden in @('Get-FlywheelFrameworkPackage', 'New-BootstrapDirectoryArchive', 'Get-BootstrapSha256', 'Test-FlywheelInstallationProvenance')) {
        Assert-BootstrapTest -Condition (-not $sourceText.Contains($forbidden)) -Message "Framework-owned installation logic remains: $forbidden"
    }
    Assert-BootstrapTest -Condition (-not $sourceText.Contains("'start-execution'")) -Message 'Bootstrap must not invoke lifecycle operations.'

    $absentRoot = Join-Path $testRoot 'absent'
    New-Item -ItemType Directory -Path $absentRoot | Out-Null
    Assert-BootstrapTest -Condition ((Get-FlywheelFrameworkCompatibility -Root $absentRoot).Status -eq 'not-installed') -Message 'Absent framework classification failed.'

    $compatibleRoot = Join-Path $testRoot 'compatible'
    Set-TestFramework -Root $compatibleRoot -InstallationVersion '2026.08.08' -ManifestVersion '2026.08.08'
    $before = (Get-FileHash -LiteralPath (Join-Path $compatibleRoot '.flywheel\manifest.yaml') -Algorithm SHA256).Hash
    Assert-BootstrapTest -Condition ((Get-FlywheelFrameworkCompatibility -Root $compatibleRoot).Status -eq 'compatible') -Message 'Compatible framework classification failed.'
    $after = (Get-FileHash -LiteralPath (Join-Path $compatibleRoot '.flywheel\manifest.yaml') -Algorithm SHA256).Hash
    Assert-BootstrapTest -Condition ($before -eq $after) -Message 'Compatibility detection modified the framework.'

    $olderRoot = Join-Path $testRoot 'older'
    Set-TestFramework -Root $olderRoot -InstallationVersion '2026.08.07' -ManifestVersion '2026.08.07'
    Assert-BootstrapTest -Condition ((Get-FlywheelFrameworkCompatibility -Root $olderRoot).Status -eq 'older-unsupported') -Message 'Older framework classification failed.'

    $newerRoot = Join-Path $testRoot 'newer'
    Set-TestFramework -Root $newerRoot -InstallationVersion '2026.08.09' -ManifestVersion '2026.08.09'
    Assert-BootstrapTest -Condition ((Get-FlywheelFrameworkCompatibility -Root $newerRoot).Status -eq 'newer-unsupported') -Message 'Newer framework classification failed.'

    $untrackedRoot = Join-Path $testRoot 'untracked'
    New-Item -ItemType Directory -Path (Join-Path $untrackedRoot '.flywheel') -Force | Out-Null
    Assert-BootstrapTest -Condition ((Get-FlywheelFrameworkCompatibility -Root $untrackedRoot).Status -eq 'untracked-or-legacy') -Message 'Untracked framework classification failed.'

    $disagreeRoot = Join-Path $testRoot 'disagree'
    Set-TestFramework -Root $disagreeRoot -InstallationVersion '2026.08.08' -ManifestVersion '2026.08.09'
    Assert-BootstrapTest -Condition ((Get-FlywheelFrameworkCompatibility -Root $disagreeRoot).Status -eq 'invalid') -Message 'Version disagreement classification failed.'

    $malformedRoot = Join-Path $testRoot 'malformed'
    Set-TestFramework -Root $malformedRoot -InstallationVersion 'not-calver' -ManifestVersion 'not-calver'
    Assert-BootstrapTest -Condition ((Get-FlywheelFrameworkCompatibility -Root $malformedRoot).Status -eq 'malformed') -Message 'Malformed framework classification failed.'

    $script:CapturedInstallerUri = $null
    function Invoke-BootstrapWebRequest {
        [CmdletBinding()]
        param([Parameter(Mandatory)][uri]$Uri, [Parameter(Mandatory)][string]$OutFile)
        $script:CapturedInstallerUri = $Uri.AbsoluteUri
        Set-Content -LiteralPath $OutFile -Encoding UTF8 -Value @'
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory)][string]$Repository,
    [Parameter()][switch]$NonInteractive,
    [Parameter()][switch]$Apply
)
$record = Join-Path $Repository 'framework-installer-invocation.txt'
Set-Content -LiteralPath $record -Encoding UTF8 -Value ("{0}|{1}|{2}" -f $Repository, [bool]$NonInteractive, [bool]$Apply)
'@
    }
    $installerRoot = Join-Path $testRoot 'official-installer'
    New-Item -ItemType Directory -Path $installerRoot | Out-Null
    $NonInteractive = $true
    Invoke-OfficialFrameworkInstaller -Root $installerRoot -TemporaryRoot $testRoot
    $NonInteractive = $false
    $expectedInstallerUri = 'https://raw.githubusercontent.com/Infoconex/ai-flywheel-framework/fe11b801b5dfeef812377a978558fd563b67fa9e/scripts/install-framework.ps1'
    Assert-BootstrapTest -Condition ($script:CapturedInstallerUri -eq $expectedInstallerUri) -Message 'Official framework installer URI is incorrect.'
    $invocation = Get-Content -LiteralPath (Join-Path $installerRoot 'framework-installer-invocation.txt') -Raw
    Assert-BootstrapTest -Condition ($invocation.Trim() -eq "$installerRoot|True|True") -Message 'Repository or non-interactive authority was not passed to the official installer.'

    Assert-BootstrapTest -Condition (Test-CliArchiveEntryExcluded -EntryName 'repo/.flywheel/state.yaml') -Message 'CLI .flywheel exclusion failed.'
    Assert-BootstrapTest -Condition (-not (Test-CliArchiveEntryExcluded -EntryName 'repo/src/ai_flywheel_cli/cli.py')) -Message 'CLI source was incorrectly excluded.'

    $cliArchive = Join-Path $testRoot 'cli.zip'
    $deepSegment = 'deep-' + ('x' * 120)
    $entries = @{
        'repo/.flywheel/operations/records/should-not-extract.yaml' = 'excluded'
        'repo/tests/should-not-extract.py' = 'excluded'
        'repo/src/ai_flywheel_cli/cli.py' = 'included'
    }
    $entries["repo/src/$deepSegment/$deepSegment/value.txt"] = 'deep-path'
    New-BootstrapTestZip -Path $cliArchive -Entries $entries -Confirm:$false
    $cliRoot = Expand-BootstrapArchive -Archive $cliArchive -Destination (Join-Path $testRoot 'cli') -Confirm:$false
    Assert-BootstrapTest -Condition (Test-Path -LiteralPath (Join-Path $cliRoot 'src\ai_flywheel_cli\cli.py')) -Message 'CLI source extraction failed.'
    Assert-BootstrapTest -Condition (-not (Test-Path -LiteralPath (Join-Path $cliRoot '.flywheel'))) -Message 'Excluded .flywheel content was extracted.'
    $deepPath = Join-Path $cliRoot "src\$deepSegment\$deepSegment\value.txt"
    Assert-BootstrapTest -Condition ([System.IO.File]::Exists((ConvertTo-BootstrapExtendedPath -Path $deepPath))) -Message 'Deep-path extraction failed.'

    Write-Output 'Windows bootstrap regression tests passed.'
}
finally {
    Remove-Item -LiteralPath $testRoot -Recurse -Force -ErrorAction SilentlyContinue
}
