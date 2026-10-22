# Internal bounded installer supervisor: original dependencies, exact owned
# Process handle, .NET descendant cleanup. No process-name search or privileges.
param([Parameter(Mandatory=$true)][string]$Config)
$ErrorActionPreference = 'Stop'
$Spec = Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
$Until = [double]$Spec.until_ms
$Started = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
if ($Started -ge $Until) { throw 'Single work deadline expired before installer' }
$Process = [System.Diagnostics.Process]::new()
$Process.StartInfo.FileName = $Spec.executable
$Process.StartInfo.UseShellExecute = $false
$Process.StartInfo.WorkingDirectory = $Spec.cwd
foreach ($Arg in $Spec.arguments) { $Process.StartInfo.ArgumentList.Add([string]$Arg) }
$Receipt = [ordered]@{ started = $false; exit_code = $null; timed_out = $false; forced_tree_stop = $false; direct_exit = $null }
try {
    if (-not $Process.Start()) { throw 'Owned installer did not start' }
    $Receipt.started = $true
    $Receipt.pid = $Process.Id
    $Wait = [Math]::Max(0, $Until - [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())
    if (-not $Process.WaitForExit([int]$Wait)) {
        $Receipt.timed_out = $true
        throw 'Owned installer exceeded the original work deadline'
    }
    $Receipt.exit_code = $Process.ExitCode
    if ($Process.ExitCode -ne 0) { throw 'Original locked dependency install failed' }
} finally {
    # The live Process object retains the exact started process identity.
    # Never kill via a PID/name search or attempt another method on denial.
    try {
        if ($Receipt.started -and -not $Process.HasExited) {
            $Receipt.forced_tree_stop = $true
            $Process.Kill($true)
            # WaitForExit only proves this direct process, not descendants.
            $Receipt.direct_exit = $Process.WaitForExit([int][Math]::Max(0,[Math]::Min(1000,$Until+10000-[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())))
        }
    } finally {
        $Receipt.finished_ms = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
        $Receipt | ConvertTo-Json -Compress | Set-Content -LiteralPath $Spec.receipt -Encoding utf8
        $Process.Dispose()
    }
}
