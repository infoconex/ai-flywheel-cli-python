@{
    Severity = @('Error', 'Warning')

    # The bootstrap intentionally owns a terminal wizard experience. Write-Host
    # is used only for presentation; operational data and diagnostics are logged
    # separately and CLI commands use structured output where available.
    ExcludeRules = @('PSAvoidUsingWriteHost')

    Rules = @{
        PSUseCompatibleSyntax = @{
            Enable = $true
            TargetVersions = @('5.1', '7.0')
        }
    }
}
