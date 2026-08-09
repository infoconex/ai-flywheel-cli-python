#Requires -Version 5.1

<#
.SYNOPSIS
Prepares a Windows Git repository for AI Flywheel onboarding.

.DESCRIPTION
Ensures the official AI Flywheel framework is installed, then asks whether the
Python CLI should be installed as repository-owned editable source or as a managed
CLI outside the repository. The bootstrap validates the selected installation
without starting onboarding. It delegates all framework acquisition, verification,
provenance, archive safety, and framework publication to the published framework
installer.

The bootstrap never commits, pushes, merges, enables application missions, or
starts an onboarding execution.

.PARAMETER Repository
Path within the target Git repository. Defaults to the current directory. When a
subdirectory is supplied, the Git repository root is resolved automatically.

.PARAMETER CliRef
CLI Git branch, tag, or commit. Defaults to an approved immutable CLI commit.

.PARAMETER CliPath
Local CLI source directory, wheel, or sdist for development/testing.

.PARAMETER CliInstallMode
Selects Source or Managed CLI installation. Interactive runs prompt when omitted.
Non-interactive runs require an explicit selection.

.PARAMETER NonInteractive
Disables prompts. Repository mutation additionally requires -Apply.

.PARAMETER Apply
Explicitly authorizes framework or repository-owned source mutation in
non-interactive mode.

.PARAMETER ValidateOnly
Validates prerequisites and an existing installation without installing.

.EXAMPLE
.\install-ai-flywheel.ps1 -Repository D:\code\my-project

Ensures framework 2026.08.08 is present and configures the Python CLI.

.NOTES
Minimum PowerShell: Windows PowerShell 5.1. PowerShell 7+ is preferred.
Minimum Python: 3.11.
Managed data: %LOCALAPPDATA%\AI-Flywheel\{cache,environments,logs}.
Temporary extraction data uses the operating-system temporary directory and is
removed at the end of the run.
Exit codes: 0 success; 1 cancelled; 2 prerequisite; 3 acquisition; 4 integrity;
5 repository conflict; 6 installation; 7 validation/readiness; 8 recovery.

Unexpected exceptions produce a concise console error, a full text diagnostic log,
and a structured .error.json report containing exception and script stack details.
#>

[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
param(
    [Parameter()]
    [ValidateNotNullOrEmpty()]
    [string]$Repository = '.',

    [Parameter()]
    [ValidateNotNullOrEmpty()]
    [string]$CliRef = '2d84294cbe9922ec907fe718e9dd06e9944e0ebc',

    [Parameter()]
    [ValidateNotNullOrEmpty()]
    [string]$CliPath,

    [Parameter()]
    [ValidateSet('Source', 'Managed')]
    [string]$CliInstallMode,

    [Parameter()]
    [switch]$NonInteractive,

    [Parameter()]
    [switch]$Apply,

    [Parameter()]
    [switch]$ValidateOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$script:ExitCode = @{
    Success = 0
    Cancelled = 1
    Prerequisite = 2
    Acquisition = 3
    Integrity = 4
    RepositoryConflict = 5
    Installation = 6
    Validation = 7
    Recovery = 8
}
$script:CliRepository = 'Infoconex/ai-flywheel-cli-python'
$script:FrameworkVersion = '2026.08.08'
$script:FrameworkInstallerCommit = 'fe11b801b5dfeef812377a978558fd563b67fa9e'
$script:FrameworkInstallerUri = "https://raw.githubusercontent.com/Infoconex/ai-flywheel-framework/$($script:FrameworkInstallerCommit)/scripts/install-framework.ps1"
$script:MinimumPythonVersion = [version]'3.11.0'
$script:RunId = [guid]::NewGuid().ToString('N')
$script:Warnings = [System.Collections.Generic.List[string]]::new()
$script:LogPath = $null
$script:ErrorReportPath = $null
$script:CurrentStage = 'Initialization'
$script:TemporaryRoot = $null
$script:InvocationBoundParameters = @{} + $PSBoundParameters
$script:BootstrapContext = [ordered]@{
    RunId = $script:RunId
    RepositoryRoot = $null
    PowerShellVersion = $PSVersionTable.PSVersion.ToString()
    PowerShellEdition = $PSVersionTable.PSEdition
    PythonVersion = $null
    PythonExecutable = $null
    CliVersion = $null
    CliExecutable = $null
    CliResolvedCommit = $null
    CliInstallMode = $null
    CliSourcePath = $null
    FrameworkVersion = $null
    FrameworkCompatibility = $null
    FrameworkInstallerCommit = $script:FrameworkInstallerCommit
    OnboardingReady = $false
}

function Write-BootstrapSection {
    [CmdletBinding()]
    param([Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Title)
    Write-Host ''
    Write-Host $Title -ForegroundColor Cyan
    Write-Host ('-' * [Math]::Min([Math]::Max($Title.Length, 24), 64)) -ForegroundColor DarkGray
}

function Write-BootstrapSuccess {
    [CmdletBinding()]
    param([Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-BootstrapWarning {
    [CmdletBinding()]
    param([Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Message)
    $script:Warnings.Add($Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-BootstrapFailure {
    [CmdletBinding()]
    param([Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Message)
    Write-Host "[FAIL] $Message" -ForegroundColor Red
}

function Write-BootstrapLog {
    [CmdletBinding()]
    param([Parameter(Mandatory)][AllowEmptyString()][string]$Message)
    try {
        if ($script:LogPath) {
            $line = '{0} [{1}] {2}' -f ([DateTimeOffset]::Now.ToString('o')), $script:CurrentStage, $Message
            Add-Content -LiteralPath $script:LogPath -Value $line -Encoding UTF8 -ErrorAction Stop
        }
    }
    catch {
        Write-Verbose "Bootstrap log write failed: $($_.Exception.Message)"
    }
    Write-Verbose $Message
}

function Get-InnerExceptionDetail {
    [CmdletBinding()]
    param([Parameter(Mandatory)][System.Exception]$Exception)
    $items = [System.Collections.Generic.List[object]]::new()
    $current = $Exception
    $depth = 0
    while ($null -ne $current) {
        $items.Add([ordered]@{
            Depth = $depth
            Type = $current.GetType().FullName
            Message = $current.Message
            HResult = $current.HResult
            StackTrace = $current.StackTrace
        })
        $current = $current.InnerException
        $depth++
    }
    return $items
}

function Write-UnexpectedBootstrapError {
    [CmdletBinding()]
    param([Parameter(Mandatory)][System.Management.Automation.ErrorRecord]$ErrorRecord)

    $timestamp = [DateTimeOffset]::Now
    if (-not $script:LogPath) {
        try {
            $script:LogPath = Join-Path ([System.IO.Path]::GetTempPath()) ('ai-flywheel-bootstrap-{0}.log' -f $timestamp.ToString('yyyyMMdd-HHmmss'))
            New-Item -ItemType File -Path $script:LogPath -Force -ErrorAction Stop | Out-Null
        }
        catch { $script:LogPath = $null }
    }

    $baseDirectory = if ($script:LogPath) { Split-Path -Parent $script:LogPath } else { [System.IO.Path]::GetTempPath() }
    $script:ErrorReportPath = Join-Path $baseDirectory ('bootstrap-{0}-{1}.error.json' -f $timestamp.ToString('yyyyMMdd-HHmmss'), $script:RunId.Substring(0, 8))
    $invocation = $ErrorRecord.InvocationInfo
    $diagnostic = [ordered]@{
        SchemaVersion = 1
        Timestamp = $timestamp.ToString('o')
        RunId = $script:RunId
        Stage = $script:CurrentStage
        ExitCategory = 'unexpected-exception'
        PowerShell = [ordered]@{
            Version = $PSVersionTable.PSVersion.ToString()
            Edition = $PSVersionTable.PSEdition
            Host = $Host.Name
            ProcessId = $PID
        }
        BootstrapContext = $script:BootstrapContext
        ErrorRecord = [ordered]@{
            ExceptionType = $ErrorRecord.Exception.GetType().FullName
            Message = $ErrorRecord.Exception.Message
            FullyQualifiedErrorId = $ErrorRecord.FullyQualifiedErrorId
            CategoryInfo = $ErrorRecord.CategoryInfo.ToString()
            ErrorDetails = if ($ErrorRecord.ErrorDetails) { $ErrorRecord.ErrorDetails.Message } else { $null }
            ScriptStackTrace = $ErrorRecord.ScriptStackTrace
            PositionMessage = if ($invocation) { $invocation.PositionMessage } else { $null }
            InvocationName = if ($invocation) { $invocation.InvocationName } else { $null }
            ScriptName = if ($invocation) { $invocation.ScriptName } else { $null }
            ScriptLineNumber = if ($invocation) { $invocation.ScriptLineNumber } else { $null }
            OffsetInLine = if ($invocation) { $invocation.OffsetInLine } else { $null }
            Line = if ($invocation) { $invocation.Line } else { $null }
            ExceptionToString = $ErrorRecord.Exception.ToString()
            InnerExceptions = @(Get-InnerExceptionDetail -Exception $ErrorRecord.Exception)
        }
    }

    try { $diagnostic | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $script:ErrorReportPath -Encoding UTF8 -ErrorAction Stop }
    catch { Write-BootstrapLog -Message "Unable to write structured error report: $($_.Exception.Message)" }

    Write-BootstrapLog -Message ('UNEXPECTED ERROR RECORD:{0}{1}' -f [Environment]::NewLine, ($ErrorRecord | Format-List * -Force | Out-String))
    Write-BootstrapLog -Message ('EXCEPTION:{0}{1}' -f [Environment]::NewLine, $ErrorRecord.Exception.ToString())
    Write-BootstrapLog -Message ('SCRIPT STACK:{0}{1}' -f [Environment]::NewLine, $ErrorRecord.ScriptStackTrace)

    Write-BootstrapFailure -Message 'AI Flywheel setup encountered an unexpected error.'
    Write-Host "Stage: $script:CurrentStage"
    Write-Host "Error type: $($ErrorRecord.Exception.GetType().FullName)"
    Write-Host "Message: $($ErrorRecord.Exception.Message)"
    if ($invocation -and $invocation.ScriptLineNumber) { Write-Host "Location: $($invocation.ScriptName):$($invocation.ScriptLineNumber)" }
    if ($script:LogPath) { Write-Host "Diagnostic log: $script:LogPath" -ForegroundColor DarkGray }
    if ($script:ErrorReportPath) { Write-Host "Structured error report: $script:ErrorReportPath" -ForegroundColor DarkGray }
}

function Invoke-BootstrapFailure {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Message,
        [Parameter(Mandatory)][ValidateRange(1, 255)][int]$Code,
        [string]$Remediation
    )
    Write-BootstrapFailure -Message $Message
    if ($Remediation) { Write-Host "Remediation: $Remediation" -ForegroundColor Yellow }
    Write-BootstrapLog -Message "EXPECTED FAILURE exit=$Code message=$Message remediation=$Remediation"
    if ($script:LogPath) { Write-Host "Diagnostic log: $script:LogPath" -ForegroundColor DarkGray }
    $exception = [System.InvalidOperationException]::new($Message)
    $exception.Data['BootstrapExitCode'] = $Code
    $exception.Data['BootstrapExpected'] = $true
    throw $exception
}

function Confirm-BootstrapAction {
    [CmdletBinding()]
    param([Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Prompt, [bool]$DefaultYes = $true)
    if ($NonInteractive) { return $false }
    $suffix = if ($DefaultYes) { '[Y/n]' } else { '[y/N]' }
    $answer = Read-Host "$Prompt $suffix"
    if ([string]::IsNullOrWhiteSpace($answer)) { return $DefaultYes }
    return $answer.Trim().StartsWith('y', [System.StringComparison]::OrdinalIgnoreCase)
}

function Resolve-CliInstallMode {
    [CmdletBinding()]
    param()

    if (-not [string]::IsNullOrWhiteSpace($CliInstallMode)) { return $CliInstallMode }
    if ($NonInteractive) {
        Invoke-BootstrapFailure -Message 'Non-interactive setup requires an explicit CLI installation mode.' -Code $script:ExitCode.Cancelled -Remediation 'Specify -CliInstallMode Source or -CliInstallMode Managed.'
    }

    Write-Host 'How should the AI Flywheel CLI be installed?'
    Write-Host ''
    Write-Host '  1. Repository-owned source (recommended)'
    Write-Host '     Seed editable Python source in .flywheel/tools so this repository can evolve it.'
    Write-Host ''
    Write-Host '  2. Managed CLI'
    Write-Host '     Install a shared, versioned CLI outside the repository.'
    Write-Host ''
    while ($true) {
        $selection = Read-Host 'Selection [1]'
        if ([string]::IsNullOrWhiteSpace($selection) -or $selection.Trim() -eq '1') { return 'Source' }
        if ($selection.Trim() -eq '2') { return 'Managed' }
        Write-BootstrapWarning -Message 'Enter 1 for repository-owned source or 2 for managed CLI.'
    }
}

function New-BootstrapDirectory {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param([Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Path)
    if ((-not (Test-Path -LiteralPath $Path)) -and $PSCmdlet.ShouldProcess($Path, 'Create directory')) {
        New-Item -ItemType Directory -Path $Path -Force -ErrorAction Stop | Out-Null
    }
}

function Sync-BootstrapProcessPath {
    [CmdletBinding()]
    param()
    $machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = @($machinePath, $userPath) -join ';'
}

function Invoke-BootstrapNativeCommand {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$FilePath,
        [Parameter()][AllowEmptyCollection()][string[]]$ArgumentList = @(),
        [switch]$AllowFailure
    )
    Write-BootstrapLog -Message ('RUN {0} {1}' -f $FilePath, ($ArgumentList -join ' '))
    $previousNativePreference = $null
    $hasNativePreference = Test-Path variable:PSNativeCommandUseErrorActionPreference
    if ($hasNativePreference) {
        $previousNativePreference = $PSNativeCommandUseErrorActionPreference
        $PSNativeCommandUseErrorActionPreference = $false
    }
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $output = @(& $FilePath @ArgumentList 2>&1)
        $nativeExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
        if ($hasNativePreference) { $PSNativeCommandUseErrorActionPreference = $previousNativePreference }
    }
    if ($output.Count -gt 0) { Write-BootstrapLog -Message (($output | Out-String).TrimEnd()) }
    if (($nativeExitCode -ne 0) -and -not $AllowFailure) {
        $rendered = ($output | Out-String).TrimEnd()
        throw [System.InvalidOperationException]::new(('Native command failed with exit code {0}: {1} {2}{3}{4}' -f $nativeExitCode, $FilePath, ($ArgumentList -join ' '), [Environment]::NewLine, $rendered))
    }
    return [pscustomobject]@{ ExitCode = $nativeExitCode; Output = $output }
}

function Install-BootstrapWingetPackage {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param(
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$PackageId,
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$DisplayName
    )
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget -or $NonInteractive) { return $false }
    if (-not (Confirm-BootstrapAction -Prompt "$DisplayName is required. Install it using winget?" -DefaultYes $true)) { return $false }
    if ($PSCmdlet.ShouldProcess($DisplayName, "Install using winget package $PackageId")) {
        Invoke-BootstrapNativeCommand -FilePath $winget.Source -ArgumentList @('install', '--id', $PackageId, '--exact', '--source', 'winget', '--accept-source-agreements', '--accept-package-agreements') | Out-Null
        Sync-BootstrapProcessPath
        return $true
    }
    return $false
}

function Get-GitCommand {
    [CmdletBinding()]
    param()
    $git = Get-Command git -ErrorAction SilentlyContinue
    if ($git) { return $git.Source }
    Write-BootstrapWarning -Message 'Git was not found on PATH.'
    if (Install-BootstrapWingetPackage -PackageId 'Git.Git' -DisplayName 'Git') { $git = Get-Command git -ErrorAction SilentlyContinue }
    if (-not $git) { Invoke-BootstrapFailure -Message 'Git is required but is not available.' -Code $script:ExitCode.Prerequisite -Remediation 'Install Git for Windows, open a new terminal if needed, and retry.' }
    return $git.Source
}

function Get-GitRepositoryRoot {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param(
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$RequestedPath,
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$GitExecutable
    )
    $resolvedPath = (Resolve-Path -LiteralPath $RequestedPath -ErrorAction Stop).Path
    Push-Location $resolvedPath
    try {
        $rootResult = Invoke-BootstrapNativeCommand -FilePath $GitExecutable -ArgumentList @('rev-parse', '--show-toplevel') -AllowFailure
        if ($rootResult.ExitCode -ne 0) {
            if ($NonInteractive) { Invoke-BootstrapFailure -Message 'The target directory is not a Git repository.' -Code $script:ExitCode.Prerequisite -Remediation 'Initialize the repository with git init before non-interactive setup.' }
            Write-BootstrapWarning -Message "No Git repository was found at $resolvedPath."
            if (-not (Confirm-BootstrapAction -Prompt 'Initialize this directory as a Git repository?' -DefaultYes $true)) { Invoke-BootstrapFailure -Message 'Setup cancelled before Git initialization.' -Code $script:ExitCode.Cancelled }
            if ($PSCmdlet.ShouldProcess($resolvedPath, 'Initialize Git repository')) { Invoke-BootstrapNativeCommand -FilePath $GitExecutable -ArgumentList @('init') | Out-Null }
            $rootResult = Invoke-BootstrapNativeCommand -FilePath $GitExecutable -ArgumentList @('rev-parse', '--show-toplevel')
        }
        return (($rootResult.Output | Select-Object -Last 1).ToString().Trim())
    }
    finally { Pop-Location }
}

function Test-BootstrapRepositoryWritable {
    [CmdletBinding()]
    param([Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Root)
    $probe = Join-Path $Root ('.flywheel-bootstrap-write-{0}.tmp' -f $script:RunId)
    try {
        Set-Content -LiteralPath $probe -Value 'probe' -Encoding ASCII -ErrorAction Stop
        Remove-Item -LiteralPath $probe -Force -ErrorAction Stop
        return $true
    }
    catch {
        Remove-Item -LiteralPath $probe -Force -ErrorAction SilentlyContinue
        Write-BootstrapLog -Message "Repository writability probe failed: $($_.Exception.Message)"
        return $false
    }
}

function Get-GitOperationState {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Root, [Parameter(Mandatory)][string]$GitExecutable)
    $result = Invoke-BootstrapNativeCommand -FilePath $GitExecutable -ArgumentList @('-C', $Root, 'rev-parse', '--git-dir')
    $gitDirectory = $result.Output[-1].ToString().Trim()
    if (-not [System.IO.Path]::IsPathRooted($gitDirectory)) { $gitDirectory = Join-Path $Root $gitDirectory }
    $markers = [ordered]@{ Merge = 'MERGE_HEAD'; RebaseMerge = 'rebase-merge'; RebaseApply = 'rebase-apply'; CherryPick = 'CHERRY_PICK_HEAD'; Revert = 'REVERT_HEAD'; Bisect = 'BISECT_LOG' }
    foreach ($entry in $markers.GetEnumerator()) {
        if (Test-Path -LiteralPath (Join-Path $gitDirectory $entry.Value)) { return $entry.Key }
    }
    return 'Normal'
}

function Test-PythonCandidate {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Command,
        [Parameter()][AllowEmptyCollection()][string[]]$Prefix = @()
    )
    $code = "import sys; print('.'.join(map(str, sys.version_info[:3]))); print(sys.executable); print(sys.base_prefix); print('1' if sys.prefix != sys.base_prefix else '0')"
    $result = Invoke-BootstrapNativeCommand -FilePath $Command -ArgumentList (@($Prefix) + @('-c', $code)) -AllowFailure
    if (($result.ExitCode -ne 0) -or ($result.Output.Count -lt 4)) { return $null }
    try { $version = [version]$result.Output[0].ToString().Trim() } catch { return $null }
    return [pscustomobject]@{
        Command = $Command
        Prefix = @($Prefix)
        Version = $version
        Executable = $result.Output[1].ToString().Trim()
        BasePrefix = $result.Output[2].ToString().Trim()
        IsVirtualEnvironment = $result.Output[3].ToString().Trim() -eq '1'
    }
}

function Get-PythonRuntime {
    [CmdletBinding()]
    param()
    $tested = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    $candidates = [System.Collections.Generic.List[object]]::new()
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) {
        foreach ($selector in @('-3.13', '-3.12', '-3.11')) { $candidates.Add([pscustomobject]@{ Command = $launcher.Source; Prefix = @($selector) }) }
    }
    foreach ($name in @('python', 'python3')) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) { $candidates.Add([pscustomobject]@{ Command = $command.Source; Prefix = @() }) }
    }

    foreach ($candidate in $candidates) {
        $identity = $candidate.Command + '|' + ($candidate.Prefix -join ' ')
        if (-not $tested.Add($identity)) { continue }
        try {
            $runtime = Test-PythonCandidate -Command $candidate.Command -Prefix $candidate.Prefix
            if (-not $runtime) { continue }
            if ($runtime.Version -lt $script:MinimumPythonVersion) { continue }
            if (-not $runtime.IsVirtualEnvironment) { return $runtime }

            Write-BootstrapLog -Message "Ignoring active virtual environment as bootstrap base runtime: $($runtime.Executable)"
            $baseExecutable = Join-Path $runtime.BasePrefix 'python.exe'
            if (Test-Path -LiteralPath $baseExecutable -PathType Leaf) {
                $baseRuntime = Test-PythonCandidate -Command $baseExecutable
                if ($baseRuntime -and -not $baseRuntime.IsVirtualEnvironment -and $baseRuntime.Version -ge $script:MinimumPythonVersion) { return $baseRuntime }
            }
        }
        catch { Write-BootstrapLog -Message "Python candidate failed: $($_.Exception.Message)" }
    }
    return $null
}

function Get-OrInstallPythonRuntime {
    [CmdletBinding()]
    param()
    $python = Get-PythonRuntime
    if ($python) { return $python }
    Write-BootstrapWarning -Message 'A base Python 3.11 or later runtime was not found.'
    if (Install-BootstrapWingetPackage -PackageId 'Python.Python.3.13' -DisplayName 'Python 3.13') { $python = Get-PythonRuntime }
    if (-not $python) { Invoke-BootstrapFailure -Message 'Python 3.11 or later is required but is not available.' -Code $script:ExitCode.Prerequisite -Remediation 'Install a base Python 3.11 or later runtime with venv support, then retry.' }
    return $python
}

function Invoke-BootstrapPython {
    [CmdletBinding()]
    param([Parameter(Mandatory)]$Python, [Parameter(Mandatory)][AllowEmptyCollection()][string[]]$ArgumentList)
    return Invoke-BootstrapNativeCommand -FilePath $Python.Command -ArgumentList (@($Python.Prefix) + $ArgumentList)
}

function Invoke-BootstrapWebRequest {
    [CmdletBinding()]
    param([Parameter(Mandatory)][uri]$Uri, [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$OutFile)
    if ($PSVersionTable.PSEdition -eq 'Desktop') {
        [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    }
    $parameters = @{ Uri = $Uri; OutFile = $OutFile; Headers = @{ 'User-Agent' = 'ai-flywheel-bootstrap' }; ErrorAction = 'Stop' }
    if ($PSVersionTable.PSEdition -eq 'Desktop') { $parameters['UseBasicParsing'] = $true }
    Invoke-WebRequest @parameters
}

function Resolve-GitHubCommit {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][ValidatePattern('^[A-Za-z0-9_.\/-]+$')][string]$RepositoryName,
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Ref
    )
    $uri = "https://api.github.com/repos/$RepositoryName/commits/$([uri]::EscapeDataString($Ref))"
    Write-BootstrapLog -Message "Resolving Git ref $RepositoryName@$Ref"
    try { $response = Invoke-RestMethod -Uri $uri -Headers @{ 'User-Agent' = 'ai-flywheel-bootstrap' } -ErrorAction Stop }
    catch { Invoke-BootstrapFailure -Message "Unable to resolve Git ref '$Ref' in $RepositoryName." -Code $script:ExitCode.Acquisition -Remediation $_.Exception.Message }
    if (-not $response.sha) { Invoke-BootstrapFailure -Message "GitHub did not return an immutable commit for '$Ref'." -Code $script:ExitCode.Acquisition }
    return $response.sha.ToString()
}

function Save-GitHubArchive {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][ValidatePattern('^[A-Za-z0-9_.\/-]+$')][string]$RepositoryName,
        [Parameter(Mandatory)][ValidatePattern('^[0-9a-fA-F]{40}$')][string]$CommitSha,
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Destination
    )
    if (Test-Path -LiteralPath $Destination) { return }
    $uri = "https://github.com/$RepositoryName/archive/$CommitSha.zip"
    Write-BootstrapLog -Message "Downloading $uri"
    try { Invoke-BootstrapWebRequest -Uri $uri -OutFile $Destination }
    catch {
        Remove-Item -LiteralPath $Destination -Force -ErrorAction SilentlyContinue
        Invoke-BootstrapFailure -Message "Download failed for $RepositoryName@$CommitSha." -Code $script:ExitCode.Acquisition -Remediation $_.Exception.Message
    }
}

function ConvertTo-BootstrapExtendedPath {
    [CmdletBinding()]
    param([Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Path)

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    if ($env:OS -ne 'Windows_NT') { return $fullPath }
    if ($fullPath.StartsWith('\\?\', [System.StringComparison]::Ordinal)) { return $fullPath }
    if ($fullPath.StartsWith('\\', [System.StringComparison]::Ordinal)) {
        return '\\?\UNC\' + $fullPath.Substring(2)
    }
    return '\\?\' + $fullPath
}

function Test-CliArchiveEntryExcluded {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$EntryName,
        [switch]$IncludeDevelopmentFiles
    )

    $parts = @($EntryName.Replace('\', '/').Split('/') | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($parts.Count -lt 2) { return $false }
    $rootChild = $parts[1]
    if ($rootChild -in @('.flywheel', '.git', '.gitignore', '.release-proof')) { return $true }
    return (-not $IncludeDevelopmentFiles) -and $rootChild -in @('tests', 'tools')
}

function Expand-BootstrapArchive {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param(
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Archive,
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Destination,
        [switch]$IncludeDevelopmentFiles
    )

    Add-Type -AssemblyName System.IO.Compression -ErrorAction Stop
    Add-Type -AssemblyName System.IO.Compression.FileSystem -ErrorAction Stop

    if (Test-Path -LiteralPath $Destination) {
        Remove-Item -LiteralPath $Destination -Recurse -Force -ErrorAction Stop
    }
    [System.IO.Directory]::CreateDirectory((ConvertTo-BootstrapExtendedPath -Path $Destination)) | Out-Null

    $destinationRoot = [System.IO.Path]::GetFullPath($Destination).TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    )
    $destinationPrefix = $destinationRoot + [System.IO.Path]::DirectorySeparatorChar
    $isCliExtraction = ([System.IO.Path]::GetFileName($destinationRoot) -eq 'cli')

    $zip = [System.IO.Compression.ZipFile]::OpenRead($Archive)
    try {
        foreach ($entry in $zip.Entries) {
            if ([string]::IsNullOrWhiteSpace($entry.FullName)) { continue }
            if ($isCliExtraction -and (Test-CliArchiveEntryExcluded -EntryName $entry.FullName -IncludeDevelopmentFiles:$IncludeDevelopmentFiles)) { continue }

            $relativeName = $entry.FullName.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
            $targetPath = [System.IO.Path]::GetFullPath((Join-Path $destinationRoot $relativeName))
            if (-not $targetPath.StartsWith($destinationPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
                Invoke-BootstrapFailure -Message "Archive entry escapes the extraction root: $($entry.FullName)" -Code $script:ExitCode.Integrity
            }

            $extendedTargetPath = ConvertTo-BootstrapExtendedPath -Path $targetPath
            if ([string]::IsNullOrEmpty($entry.Name)) {
                [System.IO.Directory]::CreateDirectory($extendedTargetPath) | Out-Null
                continue
            }

            $parent = [System.IO.Path]::GetDirectoryName($targetPath)
            [System.IO.Directory]::CreateDirectory((ConvertTo-BootstrapExtendedPath -Path $parent)) | Out-Null
            if ($PSCmdlet.ShouldProcess($targetPath, 'Extract ZIP entry')) {
                $sourceStream = $entry.Open()
                try {
                    $targetStream = [System.IO.File]::Open(
                        $extendedTargetPath,
                        [System.IO.FileMode]::Create,
                        [System.IO.FileAccess]::Write,
                        [System.IO.FileShare]::None
                    )
                    try { $sourceStream.CopyTo($targetStream) }
                    finally { $targetStream.Dispose() }
                }
                finally { $sourceStream.Dispose() }
            }
        }
    }
    finally { $zip.Dispose() }

    $roots = @(Get-ChildItem -LiteralPath $Destination -Directory -ErrorAction Stop)
    if ($roots.Count -ne 1) {
        Invoke-BootstrapFailure -Message "Expected one source root in archive but found $($roots.Count)." -Code $script:ExitCode.Integrity
    }
    return $roots[0].FullName
}

function Get-FlywheelCliSource {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$FlywheelHome,
        [Parameter(Mandatory)][string]$TemporaryRoot,
        [switch]$IncludeDevelopmentFiles
    )

    if ($script:InvocationBoundParameters.ContainsKey('CliPath')) {
        $sourcePath = (Resolve-Path -LiteralPath $CliPath -ErrorAction Stop).Path
        return [pscustomobject]@{
            Path = $sourcePath
            Identity = "local:$sourcePath"
            ResolvedCommit = $null
        }
    }

    $resolvedCommit = Resolve-GitHubCommit -RepositoryName $script:CliRepository -Ref $CliRef
    $cacheDirectory = Join-Path $FlywheelHome 'cache\cli'
    New-BootstrapDirectory -Path $cacheDirectory -Confirm:$false
    $archive = Join-Path $cacheDirectory ("$resolvedCommit.zip")
    Save-GitHubArchive -RepositoryName $script:CliRepository -CommitSha $resolvedCommit -Destination $archive
    $sourcePath = Expand-BootstrapArchive -Archive $archive -Destination (Join-Path $TemporaryRoot 'cli') -IncludeDevelopmentFiles:$IncludeDevelopmentFiles -Confirm:$false
    return [pscustomobject]@{
        Path = $sourcePath
        Identity = "github-ref:$script:CliRepository@$resolvedCommit"
        ResolvedCommit = $resolvedCommit
    }
}

function Initialize-FlywheelCliEnvironment {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]$Python,
        [Parameter(Mandatory)][string]$FlywheelHome,
        [Parameter(Mandatory)][string]$TemporaryRoot
    )
    $source = Get-FlywheelCliSource -FlywheelHome $FlywheelHome -TemporaryRoot $TemporaryRoot
    if ($script:InvocationBoundParameters.ContainsKey('CliPath')) {
        $environmentName = 'cli-local'
    }
    else {
        $environmentName = "cli-$($source.ResolvedCommit.Substring(0, 12))"
    }

    $environment = Join-Path $FlywheelHome ("environments\$environmentName")
    $venvPython = Join-Path $environment 'Scripts\python.exe'
    $flywheel = Join-Path $environment 'Scripts\flywheel.exe'
    $healthy = $false
    if ((Test-Path -LiteralPath $venvPython) -and (Test-Path -LiteralPath $flywheel)) {
        $healthy = (Invoke-BootstrapNativeCommand -FilePath $flywheel -ArgumentList @('--version') -AllowFailure).ExitCode -eq 0
    }
    if (-not $healthy) {
        if ($ValidateOnly) {
            Invoke-BootstrapFailure -Message 'The managed CLI environment is not healthy.' -Code $script:ExitCode.Validation -Remediation 'Run setup without -ValidateOnly and select Managed to rebuild the environment.'
        }
        if (Test-Path -LiteralPath $environment) {
            Write-BootstrapWarning -Message 'Existing managed CLI environment is unhealthy.'
            if ($NonInteractive -or (Confirm-BootstrapAction -Prompt 'Rebuild the Flywheel-owned CLI environment?' -DefaultYes $true)) { Remove-Item -LiteralPath $environment -Recurse -Force -ErrorAction Stop }
            else { Invoke-BootstrapFailure -Message 'A healthy AI Flywheel CLI environment is required.' -Code $script:ExitCode.Cancelled }
        }
        New-BootstrapDirectory -Path (Split-Path -Parent $environment) -Confirm:$false
        Write-Host 'Preparing managed AI Flywheel CLI environment...' -ForegroundColor DarkGray
        Invoke-BootstrapPython -Python $Python -ArgumentList @('-m', 'venv', $environment) | Out-Null
        Invoke-BootstrapNativeCommand -FilePath $venvPython -ArgumentList @('-m', 'pip', 'install', '--disable-pip-version-check', $source.Path) | Out-Null
    }
    $versionResult = Invoke-BootstrapNativeCommand -FilePath $flywheel -ArgumentList @('--version')
    return [pscustomobject]@{
        Executable = $flywheel
        Python = $venvPython
        Version = (($versionResult.Output | Select-Object -Last 1).ToString().Trim())
        Environment = $environment
        SourceIdentity = $source.Identity
        ResolvedCommit = $source.ResolvedCommit
        InstallMode = 'Managed'
        SourcePath = $null
    }
}

function Initialize-RepositoryFlywheelCli {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param(
        [Parameter(Mandatory)]$Python,
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)][string]$FlywheelHome,
        [Parameter(Mandatory)][string]$TemporaryRoot
    )

    $target = Join-Path $Root '.flywheel\tools'
    $metadataPath = Join-Path $target 'cli-source.yaml'
    if (Test-Path -LiteralPath $target) {
        if (-not (Test-Path -LiteralPath $metadataPath -PathType Leaf)) {
            Invoke-BootstrapFailure -Message 'Repository-owned CLI source cannot be installed because .flywheel/tools already exists without CLI source metadata.' -Code $script:ExitCode.RepositoryConflict -Remediation 'Preserve or relocate the existing tools, then retry. The installer will not overwrite them.'
        }
        $recordedMode = Get-TopLevelYamlValue -Path $metadataPath -Key 'installation_mode'
        if ($recordedMode -ne 'source') {
            Invoke-BootstrapFailure -Message 'Repository-owned CLI source metadata is malformed or uses an unsupported installation mode.' -Code $script:ExitCode.RepositoryConflict -Remediation 'Repair cli-source.yaml before retrying. The installer will not overwrite repository tools.'
        }
        if (-not (Test-Path -LiteralPath (Join-Path $target 'pyproject.toml') -PathType Leaf)) {
            Invoke-BootstrapFailure -Message 'Repository-owned CLI source metadata exists, but pyproject.toml is missing.' -Code $script:ExitCode.RepositoryConflict -Remediation 'Repair the governed repository-owned tools before retrying.'
        }
        $sourceIdentity = Get-TopLevelYamlValue -Path $metadataPath -Key 'source_identity'
        $resolvedCommit = Get-TopLevelYamlValue -Path $metadataPath -Key 'source_commit'
        Write-BootstrapSuccess -Message 'Existing repository-owned CLI source preserved'
    }
    else {
        if ($ValidateOnly) {
            Invoke-BootstrapFailure -Message 'Repository-owned CLI source is not installed.' -Code $script:ExitCode.Validation -Remediation 'Run setup without -ValidateOnly and select Source.'
        }
        $source = Get-FlywheelCliSource -FlywheelHome $FlywheelHome -TemporaryRoot $TemporaryRoot -IncludeDevelopmentFiles
        if (-not (Test-Path -LiteralPath $source.Path -PathType Container)) {
            Invoke-BootstrapFailure -Message 'Repository-owned installation requires a CLI source directory.' -Code $script:ExitCode.Acquisition -Remediation 'Use a source directory with -CliPath or use -CliInstallMode Managed for a wheel or sdist.'
        }

        $stagingParent = Join-Path $Root '.flywheel\.runtime'
        New-BootstrapDirectory -Path $stagingParent -Confirm:$false
        $staging = Join-Path $stagingParent ("cli-source-$($script:RunId.Substring(0, 8))")
        New-BootstrapDirectory -Path $staging -Confirm:$false
        try {
            foreach ($item in @('pyproject.toml', 'README.md', 'src', 'tests', 'tools')) {
                $sourceItem = Join-Path $source.Path $item
                if (-not (Test-Path -LiteralPath $sourceItem)) {
                    Invoke-BootstrapFailure -Message "CLI source is missing required project content: $item" -Code $script:ExitCode.Integrity
                }
                Copy-Item -LiteralPath $sourceItem -Destination $staging -Recurse -Force -ErrorAction Stop
            }
            $sourceCommit = if ($source.ResolvedCommit) { $source.ResolvedCommit } else { 'local' }
            @(
                'schema_version: 1'
                'installation_mode: source'
                "source_repository: $($script:CliRepository)"
                "source_commit: $sourceCommit"
                "source_identity: '$($source.Identity.Replace("'", "''"))'"
                'update_policy: repository-governed'
            ) | Set-Content -LiteralPath (Join-Path $staging 'cli-source.yaml') -Encoding UTF8 -ErrorAction Stop
            if ($PSCmdlet.ShouldProcess($target, 'Publish repository-owned CLI source')) {
                Move-Item -LiteralPath $staging -Destination $target -ErrorAction Stop
            }
        }
        finally {
            if (Test-Path -LiteralPath $staging) {
                Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue
            }
        }
        $sourceIdentity = $source.Identity
        $resolvedCommit = $source.ResolvedCommit
        Write-BootstrapSuccess -Message 'Editable CLI source installed in .flywheel/tools'
    }

    $environment = Join-Path $Root '.flywheel\.runtime\python-cli'
    $venvPython = Join-Path $environment 'Scripts\python.exe'
    $flywheel = Join-Path $environment 'Scripts\flywheel.exe'
    $healthy = $false
    if ((Test-Path -LiteralPath $venvPython) -and (Test-Path -LiteralPath $flywheel)) {
        $healthy = (Invoke-BootstrapNativeCommand -FilePath $flywheel -ArgumentList @('--version') -AllowFailure).ExitCode -eq 0
    }
    if (-not $healthy) {
        if ($ValidateOnly) {
            Invoke-BootstrapFailure -Message 'The repository-owned CLI runtime is not healthy.' -Code $script:ExitCode.Validation -Remediation 'Run setup without -ValidateOnly and select Source to rebuild the runtime.'
        }
        if (Test-Path -LiteralPath $environment) {
            Write-BootstrapWarning -Message 'Existing repository-owned CLI runtime is unhealthy.'
            if ($NonInteractive -or (Confirm-BootstrapAction -Prompt 'Rebuild the Flywheel-owned repository runtime?' -DefaultYes $true)) { Remove-Item -LiteralPath $environment -Recurse -Force -ErrorAction Stop }
            else { Invoke-BootstrapFailure -Message 'A healthy repository-owned CLI runtime is required.' -Code $script:ExitCode.Cancelled }
        }
        New-BootstrapDirectory -Path (Split-Path -Parent $environment) -Confirm:$false
        Write-Host 'Preparing repository-owned AI Flywheel CLI runtime...' -ForegroundColor DarkGray
        Invoke-BootstrapPython -Python $Python -ArgumentList @('-m', 'venv', $environment) | Out-Null
        Invoke-BootstrapNativeCommand -FilePath $venvPython -ArgumentList @('-m', 'pip', 'install', '--disable-pip-version-check', '--editable', "$target[dev]") | Out-Null
    }
    $versionResult = Invoke-BootstrapNativeCommand -FilePath $flywheel -ArgumentList @('--version')
    return [pscustomobject]@{
        Executable = $flywheel
        Python = $venvPython
        Version = (($versionResult.Output | Select-Object -Last 1).ToString().Trim())
        Environment = $environment
        SourceIdentity = $sourceIdentity
        ResolvedCommit = $resolvedCommit
        InstallMode = 'Source'
        SourcePath = $target
    }
}

function Get-TopLevelYamlValue {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Key
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    foreach ($line in Get-Content -LiteralPath $Path -ErrorAction Stop) {
        $match = [regex]::Match($line, ('^' + [regex]::Escape($Key) + ':\s*["'']?([^"'']+?)["'']?\s*$'))
        if ($match.Success) { return $match.Groups[1].Value.Trim() }
    }
    return $null
}

function Get-ManifestFrameworkVersion {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    $insideFramework = $false
    foreach ($line in Get-Content -LiteralPath $Path -ErrorAction Stop) {
        if (-not $insideFramework) {
            if ($line -match '^framework:\s*$') { $insideFramework = $true }
            continue
        }
        if ($line -match '^\S') { break }
        $match = [regex]::Match($line, '^\s+version:\s*["'']?([^"'']+?)["'']?\s*$')
        if ($match.Success) { return $match.Groups[1].Value.Trim() }
    }
    return $null
}

function Get-FlywheelFrameworkCompatibility {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Root)

    $flywheel = Join-Path $Root '.flywheel'
    if (-not (Test-Path -LiteralPath $flywheel)) {
        return [pscustomobject]@{ Status = 'not-installed'; Version = $null; Reason = 'No .flywheel directory is installed.' }
    }
    if (-not (Test-Path -LiteralPath $flywheel -PathType Container)) {
        return [pscustomobject]@{ Status = 'malformed'; Version = $null; Reason = '.flywheel exists but is not a directory.' }
    }

    $installation = Join-Path $flywheel 'installation.yaml'
    if (-not (Test-Path -LiteralPath $installation -PathType Leaf)) {
        return [pscustomobject]@{ Status = 'untracked-or-legacy'; Version = $null; Reason = 'Installation provenance is missing.' }
    }
    $installedVersion = Get-TopLevelYamlValue -Path $installation -Key 'framework_version'
    $manifestVersion = Get-ManifestFrameworkVersion -Path (Join-Path $flywheel 'manifest.yaml')
    $calverPattern = '^\d{4}\.\d{2}\.\d{2}$'
    if (-not $installedVersion -or $installedVersion -notmatch $calverPattern) {
        return [pscustomobject]@{ Status = 'malformed'; Version = $installedVersion; Reason = 'installation.yaml does not contain a valid CalVer framework_version.' }
    }
    if (-not $manifestVersion -or $manifestVersion -notmatch $calverPattern) {
        return [pscustomobject]@{ Status = 'malformed'; Version = $installedVersion; Reason = 'manifest.yaml does not contain a valid framework.version CalVer.' }
    }
    if ($manifestVersion -ne $installedVersion) {
        return [pscustomobject]@{ Status = 'invalid'; Version = $installedVersion; Reason = 'Installation and manifest framework versions disagree.' }
    }

    $installed = [version]$installedVersion
    $supported = [version]$script:FrameworkVersion
    if ($installed -eq $supported) {
        return [pscustomobject]@{ Status = 'compatible'; Version = $installedVersion; Reason = 'The installed framework is compatible.' }
    }
    if ($installed -lt $supported) {
        return [pscustomobject]@{ Status = 'older-unsupported'; Version = $installedVersion; Reason = 'The installed framework is older than the supported framework.' }
    }
    return [pscustomobject]@{ Status = 'newer-unsupported'; Version = $installedVersion; Reason = 'The installed framework is newer than the supported framework.' }
}

function Invoke-OfficialFrameworkInstaller {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)][string]$TemporaryRoot
    )

    $installerPath = Join-Path $TemporaryRoot 'install-framework.ps1'
    Invoke-BootstrapWebRequest -Uri $script:FrameworkInstallerUri -OutFile $installerPath
    $arguments = @{ Repository = $Root }
    if ($NonInteractive) {
        $arguments['NonInteractive'] = $true
        $arguments['Apply'] = $true
        $arguments['Confirm'] = $false
    }
    if ($WhatIfPreference) { $arguments['WhatIf'] = $true }

    Write-BootstrapLog -Message "Invoking official framework installer $($script:FrameworkInstallerCommit)"
    & $installerPath @arguments
}

function Remove-BootstrapTemporaryWork {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param([string]$Path)
    if ($Path -and (Test-Path -LiteralPath $Path) -and $PSCmdlet.ShouldProcess($Path, 'Remove temporary bootstrap working directory')) {
        Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction Stop
    }
}

function Invoke-AIFlywheelBootstrap {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param()
    try {
        if ($env:OS -ne 'Windows_NT') { Invoke-BootstrapFailure -Message 'This bootstrap is intended for Windows.' -Code $script:ExitCode.Prerequisite }

        $flywheelHome = Join-Path $env:LOCALAPPDATA 'AI-Flywheel'
        $logDirectory = Join-Path $flywheelHome 'logs'
        New-BootstrapDirectory -Path $logDirectory -Confirm:$false
        $script:LogPath = Join-Path $logDirectory ('bootstrap-{0}-{1}.log' -f ([DateTimeOffset]::Now.ToString('yyyyMMdd-HHmmss')), $script:RunId.Substring(0, 8))
        New-Item -ItemType File -Path $script:LogPath -Force -ErrorAction Stop | Out-Null
        $temporaryBase = Join-Path ([System.IO.Path]::GetTempPath()) 'AIFW'
        New-BootstrapDirectory -Path $temporaryBase -Confirm:$false
        $script:TemporaryRoot = Join-Path $temporaryBase $script:RunId.Substring(0, 8)
        New-BootstrapDirectory -Path $script:TemporaryRoot -Confirm:$false

        Write-Host 'AI Flywheel Setup' -ForegroundColor Cyan
        Write-Host 'Preparing this repository for AI Flywheel onboarding.' -ForegroundColor DarkGray

        $script:CurrentStage = 'Repository'
        Write-BootstrapSection -Title 'Repository'
        $gitExecutable = Get-GitCommand
        $root = Get-GitRepositoryRoot -RequestedPath $Repository -GitExecutable $gitExecutable -Confirm:$false
        $script:BootstrapContext.RepositoryRoot = $root
        Write-BootstrapSuccess -Message 'Git repository detected'
        Write-Host "Repository root: $root"
        if (-not (Test-BootstrapRepositoryWritable -Root $root)) { Invoke-BootstrapFailure -Message "Repository root is not writable: $root" -Code $script:ExitCode.Prerequisite -Remediation 'Correct repository permissions and retry.' }
        Write-BootstrapSuccess -Message 'Repository is writable'
        $gitVersion = ((Invoke-BootstrapNativeCommand -FilePath $gitExecutable -ArgumentList @('--version')).Output | Select-Object -Last 1).ToString().Trim()
        Write-BootstrapSuccess -Message $gitVersion
        $operationState = Get-GitOperationState -Root $root -GitExecutable $gitExecutable
        if ($operationState -ne 'Normal') {
            Write-BootstrapWarning -Message "Git operation in progress: $operationState"
            if ($NonInteractive) { Invoke-BootstrapFailure -Message "Git operation in progress: $operationState" -Code $script:ExitCode.RepositoryConflict -Remediation 'Complete or abort the Git operation before non-interactive setup.' }
            if (-not (Confirm-BootstrapAction -Prompt 'Continue setup without changing the existing Git operation?' -DefaultYes $false)) { Invoke-BootstrapFailure -Message 'Setup cancelled while a Git operation is in progress.' -Code $script:ExitCode.Cancelled }
        }
        $workingStatus = Invoke-BootstrapNativeCommand -FilePath $gitExecutable -ArgumentList @('-C', $root, 'status', '--porcelain')
        if ($workingStatus.Output.Count -gt 0) { Write-BootstrapWarning -Message 'Existing Git working changes detected; they will be preserved.' }

        $script:CurrentStage = 'Environment'
        Write-BootstrapSection -Title 'Environment'
        Write-BootstrapSuccess -Message 'Windows detected'
        Write-Host "PowerShell: $($PSVersionTable.PSVersion) ($($PSVersionTable.PSEdition))"
        if ($PSVersionTable.PSVersion.Major -lt 7) { Write-BootstrapWarning -Message 'PowerShell 7+ is preferred; Windows PowerShell 5.1 compatibility mode is active.' }
        if (Get-Command winget -ErrorAction SilentlyContinue) { Write-BootstrapSuccess -Message 'winget available for prerequisite remediation' }
        else { Write-BootstrapWarning -Message 'winget unavailable; automatic prerequisite remediation is limited.' }

        $script:CurrentStage = 'Framework'
        Write-BootstrapSection -Title 'AI Flywheel Framework'
        $frameworkInstalled = $false
        $compatibility = Get-FlywheelFrameworkCompatibility -Root $root
        if ($compatibility.Status -eq 'not-installed') {
            if ($ValidateOnly) {
                Invoke-BootstrapFailure -Message 'AI Flywheel Framework is not installed.' -Code $script:ExitCode.Validation -Remediation 'Run bootstrap without -ValidateOnly to invoke the official framework installer.'
            }
            if ($NonInteractive -and -not $Apply) {
                Invoke-BootstrapFailure -Message 'Non-interactive framework installation requires explicit -Apply authorization.' -Code $script:ExitCode.Cancelled
            }
            Write-Host "Framework $($script:FrameworkVersion) is not installed."
            Write-Host "Using official installer commit: $($script:FrameworkInstallerCommit)"
            Invoke-OfficialFrameworkInstaller -Root $root -TemporaryRoot $script:TemporaryRoot
            $compatibility = Get-FlywheelFrameworkCompatibility -Root $root
            if ($WhatIfPreference -and $compatibility.Status -eq 'not-installed') {
                Write-BootstrapWarning -Message 'WhatIf mode: the official framework installer was evaluated without installation.'
                return $script:ExitCode.Success
            }
            if ($compatibility.Status -eq 'not-installed') {
                Invoke-BootstrapFailure -Message 'The official framework installer completed without installing a framework.' -Code $script:ExitCode.Cancelled -Remediation 'Installation may have been cancelled. Run bootstrap again when ready.'
            }
            $frameworkInstalled = $true
        }
        if ($compatibility.Status -ne 'compatible') {
            $versionText = if ($compatibility.Version) { $compatibility.Version } else { 'unknown' }
            Invoke-BootstrapFailure -Message "Existing framework is not compatible: $($compatibility.Status) (version $versionText)." -Code $script:ExitCode.RepositoryConflict -Remediation "$($compatibility.Reason) Bootstrap will not overwrite .flywheel. No automatic framework upgrade contract is currently published."
        }
        $script:BootstrapContext.FrameworkVersion = $compatibility.Version
        $script:BootstrapContext.FrameworkCompatibility = $compatibility.Status
        if ($frameworkInstalled) { Write-BootstrapSuccess -Message "Official framework $($compatibility.Version) installed" }
        else { Write-BootstrapSuccess -Message "Compatible framework $($compatibility.Version) already installed and left intact" }

        $script:CurrentStage = 'CLI Installation Mode'
        Write-BootstrapSection -Title 'CLI Installation Mode'
        $installMode = Resolve-CliInstallMode
        $script:BootstrapContext.CliInstallMode = $installMode
        if ($installMode -eq 'Source') {
            if ($NonInteractive -and -not $Apply -and -not (Test-Path -LiteralPath (Join-Path $root '.flywheel\tools\cli-source.yaml') -PathType Leaf)) {
                Invoke-BootstrapFailure -Message 'Non-interactive repository-owned source installation requires explicit -Apply authorization.' -Code $script:ExitCode.Cancelled
            }
            Write-BootstrapSuccess -Message 'Repository-owned editable source selected'
        }
        else {
            if (Test-Path -LiteralPath (Join-Path $root '.flywheel\tools\cli-source.yaml') -PathType Leaf) {
                Invoke-BootstrapFailure -Message 'This repository already uses repository-owned CLI source.' -Code $script:ExitCode.RepositoryConflict -Remediation 'Select Source. Hybrid operation is not implemented in this milestone.'
            }
            Write-BootstrapSuccess -Message 'Managed CLI selected'
        }

        $script:CurrentStage = 'Python'
        Write-BootstrapSection -Title 'Python'
        $python = Get-OrInstallPythonRuntime
        $script:BootstrapContext.PythonVersion = $python.Version.ToString()
        $script:BootstrapContext.PythonExecutable = $python.Executable
        Write-BootstrapSuccess -Message "Python $($python.Version) detected"
        Write-Host "Python: $($python.Executable)"

        $script:CurrentStage = 'CLI'
        Write-BootstrapSection -Title 'AI Flywheel CLI'
        if ($installMode -eq 'Source') {
            $cli = Initialize-RepositoryFlywheelCli -Python $python -Root $root -FlywheelHome $flywheelHome -TemporaryRoot $script:TemporaryRoot -Confirm:$false
        }
        else {
            $cli = Initialize-FlywheelCliEnvironment -Python $python -FlywheelHome $flywheelHome -TemporaryRoot $script:TemporaryRoot
        }
        $script:BootstrapContext.CliVersion = $cli.Version
        $script:BootstrapContext.CliExecutable = $cli.Executable
        $script:BootstrapContext.CliResolvedCommit = $cli.ResolvedCommit
        $script:BootstrapContext.CliSourcePath = $cli.SourcePath
        Write-BootstrapSuccess -Message "AI Flywheel CLI $($cli.Version) ready"

        $script:CurrentStage = 'Validation'
        Write-BootstrapSection -Title 'Compatibility and Health'
        $doctorResult = Invoke-BootstrapNativeCommand -FilePath $cli.Executable -ArgumentList @('doctor', $root, '--json') -AllowFailure
        if ($doctorResult.ExitCode -ne 0) {
            $doctorDetail = ($doctorResult.Output -join [Environment]::NewLine).Trim()
            Invoke-BootstrapFailure -Message 'CLI health and framework compatibility checks failed.' -Code $script:ExitCode.Validation -Remediation $doctorDetail
        }
        Write-BootstrapSuccess -Message 'CLI health and framework compatibility checks passed'
        $script:BootstrapContext.OnboardingReady = $true

        $script:CurrentStage = 'Complete'
        Write-BootstrapSection -Title 'AI Flywheel Setup Complete'
        Write-Host "Repository: $root"
        Write-Host "Framework: $($compatibility.Version)"
        Write-Host "Framework installer commit: $($script:FrameworkInstallerCommit)"
        Write-Host "CLI installation mode: $($cli.InstallMode)"
        if ($cli.SourcePath) { Write-Host "CLI source: $($cli.SourcePath)" }
        Write-Host "CLI command: $($cli.Executable)"
        Write-Host "CLI: $($cli.Version)"
        Write-Host 'Compatibility: Passed'
        Write-Host 'Repository validation: Passed'
        Write-Host 'No onboarding or lifecycle operation was started.'
        if ($script:Warnings.Count -gt 0) { Write-Host "Warnings: $($script:Warnings.Count)" -ForegroundColor Yellow }
        Write-Host "Diagnostic log: $script:LogPath" -ForegroundColor DarkGray
        Write-Host ''
        Write-Host 'Next: Begin or continue AI Flywheel operation in this repository.' -ForegroundColor Cyan
        return $script:ExitCode.Success
    }
    catch {
        if ($_.Exception.Data['BootstrapExpected']) { return [int]$_.Exception.Data['BootstrapExitCode'] }
        Write-UnexpectedBootstrapError -ErrorRecord $_
        return $script:ExitCode.Installation
    }
    finally {
        $script:CurrentStage = 'Cleanup'
        if ($script:TemporaryRoot -and (Test-Path -LiteralPath $script:TemporaryRoot)) {
            try { Remove-BootstrapTemporaryWork -Path $script:TemporaryRoot -Confirm:$false }
            catch { Write-BootstrapWarning -Message "Temporary bootstrap work could not be fully removed: $script:TemporaryRoot"; Write-BootstrapLog -Message "Cleanup failure: $($_.Exception.ToString())" }
        }
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    $resultCode = Invoke-AIFlywheelBootstrap
    exit $resultCode
}
