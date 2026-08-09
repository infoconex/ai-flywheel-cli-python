#Requires -Version 5.1

<#
.SYNOPSIS
Starts the AI Flywheel Windows installer from a stable public one-liner.

.DESCRIPTION
This lightweight launcher is safe to execute through Invoke-Expression. It runs in
an isolated child scope, downloads the reviewed canonical installer to a temporary
.ps1 file, executes that file in its own script scope, and removes the temporary
launcher artifact afterward.

The canonical Python bootstrap detects framework compatibility and delegates an
absent framework to the official published framework installer. It then prepares
the Python CLI and performs compatibility and health checks.
#>

& {
    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'
    $ProgressPreference = 'SilentlyContinue'

    $installerCommit = 'a8cbeb6796ea0725cb179de4d289bb78d9707d5f'
    $installerUri = "https://raw.githubusercontent.com/Infoconex/ai-flywheel-cli-python/$installerCommit/scripts/install-ai-flywheel.ps1"
    $installerPath = Join-Path ([System.IO.Path]::GetTempPath()) ('ai-flywheel-installer-{0}.ps1' -f [guid]::NewGuid().ToString('N').Substring(0, 8))

    try {
        $requestParameters = @{
            Uri = $installerUri
            OutFile = $installerPath
            Headers = @{ 'User-Agent' = 'ai-flywheel-installer' }
            ErrorAction = 'Stop'
        }

        if ($PSVersionTable.PSEdition -eq 'Desktop') {
            [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
            $requestParameters['UseBasicParsing'] = $true
        }

        Invoke-WebRequest @requestParameters
        & $installerPath
    }
    finally {
        Remove-Item -LiteralPath $installerPath -Force -ErrorAction SilentlyContinue
    }
}
