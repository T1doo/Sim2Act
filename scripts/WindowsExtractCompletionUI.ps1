# Same official Windows/installed Edge route. This supervisor holds the exact
# created Python process handle throughout setup, browser work and cleanup.
param([switch]$DeleteOnly)
$ErrorActionPreference = 'Stop'
if (-not $IsWindows -or $env:GITHUB_ACTIONS -ne 'true') { throw 'Actual Windows runner required' }
$Until = [double]$env:SIM2ACT_UI_UNTIL
$Root = Join-Path $env:RUNNER_TEMP "sim2act-extract-ui-$env:GITHUB_RUN_ID-1"
if ($DeleteOnly) {
    # Invoked only after Python exits and DLLs are no longer loaded. Literal
    # own-run directory, no process search/other project/alternate permission.
    if ($env:GITHUB_RUN_ID -notmatch '^\d+$' -or $env:GITHUB_RUN_ATTEMPT -ne '1') { throw 'Invalid owned directory' }
    Remove-Item -LiteralPath $Root -Recurse -Force
    exit 0
}
$Edge = Join-Path ${env:ProgramFiles(x86)} 'Microsoft\Edge\Application\msedge.exe'
if (-not (Test-Path $Edge)) { throw 'Installed Edge unavailable; no download/fallback' }
$Signature = Get-AuthenticodeSignature -LiteralPath $Edge
if ($Signature.Status -ne 'Valid' -or $Signature.SignerCertificate.Subject -notmatch 'Microsoft Corporation') { throw 'Installed Edge signature rejected' }
@{ edge_version=(Get-Item $Edge).VersionInfo.ProductVersion; signature=[string]$Signature.Status; signer=$Signature.SignerCertificate.Subject; install_browser=$false } | ConvertTo-Json -Compress | Write-Output
$Process = [System.Diagnostics.Process]::new()
# setup-python supplies one exact toolcache root. PATH lookup can return both
# that interpreter and a WindowsApps execution alias; never concatenate them
# or try an alternate executable when this authoritative path is unavailable.
if ([string]::IsNullOrWhiteSpace($env:pythonLocation) -or $env:pythonLocation -match '[\r\n]') { throw 'Selected Python root missing or ambiguous' }
$Python = Join-Path $env:pythonLocation 'python.exe'
if (-not [IO.Path]::IsPathFullyQualified($Python) -or -not (Test-Path -LiteralPath $Python -PathType Leaf)) { throw 'Exact selected Python executable unavailable; no PATH fallback' }
$Process.StartInfo.FileName = [IO.Path]::GetFullPath($Python)
$Process.StartInfo.UseShellExecute = $false
$Process.StartInfo.ArgumentList.Add('scripts/protocol_completion_browser_ci.py')
$Receipt = [ordered]@{started=$false; timed_out=$false; forced_tree_stop=$false; process_exited=$false; exit_code=$null}
try {
    $Remaining = $Until - [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    if ($Remaining -le 0) { throw 'Original work deadline expired during Actions setup' }
    if (-not $Process.Start()) { throw 'Owned Python did not start' }
    $Receipt.started=$true
    $Receipt.pid=$Process.Id
    if (-not $Process.WaitForExit([int]$Remaining)) {
        $Receipt.timed_out=$true
        throw 'Single 180s work deadline; no retry'
    }
    $Receipt.exit_code=$Process.ExitCode
    if ($Process.ExitCode -ne 0) { throw 'Native UI validation failed; no retry' }
} finally {
    try {
        if ($Receipt.started -and -not $Process.HasExited) {
            $CleanupUntil=[Math]::Min([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()+10000,$Until+10000)
            if (Test-Path $Root) {
                $Shared=Join-Path $Root 'cleanup-until.json'
                if (Test-Path $Shared) { $CleanupUntil=[Math]::Min($CleanupUntil,1000*[double](Get-Content $Shared -Raw)) }
                [IO.File]::WriteAllText((Join-Path $Root 'stop'),'')
            }
            $Grace=[Math]::Max(0,$CleanupUntil-[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()-2000)
            if (-not $Process.WaitForExit([int]$Grace)) {
                $Receipt.forced_tree_stop=$true
                $Process.Kill($true) # Exact handle and its own descendants only.
                $Process.WaitForExit([int][Math]::Max(0,$CleanupUntil-[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())) | Out-Null
            }
        }
    } catch {
        # Access denial is recorded; no other kill mechanism/privilege is tried.
        $Receipt.cleanup_error=$_.Exception.Message
    } finally {
        if ($Receipt.started) { $Receipt.process_exited=$Process.HasExited }
        # Loaded pyd/DLL files cannot be deleted while Python is alive. Cleanup
        # uses the same earliest deadline; dependency/cache deletion is watched
        # through one exact child handle, and any timeout remains UNKNOWN.
        if ($Receipt.process_exited -and $Receipt.exit_code -eq 0 -and -not $Receipt.forced_tree_stop -and -not $Receipt.timed_out) {
            $Delete = $null
            try {
                $Shared = Join-Path $Root 'cleanup-until.json'
                $CleanupUntil = [Math]::Min($Until+10000,1000*[double](Get-Content $Shared -Raw))
                $Remaining=[Math]::Max(0,$CleanupUntil-[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())
                if ($Remaining -le 0) { throw 'Shared cleanup deadline expired before dependency deletion' }
                $Delete=[System.Diagnostics.Process]::new()
                $Delete.StartInfo.FileName=(Get-Process -Id $PID).Path
                $Delete.StartInfo.UseShellExecute=$false
                foreach ($Arg in @('-NoProfile','-NonInteractive','-File',$PSCommandPath,'-DeleteOnly')) { $Delete.StartInfo.ArgumentList.Add($Arg) }
                if (-not $Delete.Start()) { throw 'Owned cleanup did not start' }
                if (-not $Delete.WaitForExit([int][Math]::Max(0,$Remaining-1000))) {
                    $Delete.Kill($true)
                    $Delete.WaitForExit([int][Math]::Max(0,$CleanupUntil-[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())) | Out-Null
                    throw 'Owned dependency cleanup UNKNOWN at deadline'
                }
                if ($Delete.ExitCode -ne 0 -or (Test-Path $Root)) { throw 'Owned dependency cleanup incomplete' }
                $Receipt.owned_directory_deleted=$true
            } catch { $Receipt.cleanup_error=$_.Exception.Message }
            finally { if ($null -ne $Delete) { $Delete.Dispose() } }
        }
        $Receipt.finished_ms=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
        $Receipt | ConvertTo-Json -Compress | Write-Output
        $Process.Dispose()
    }
}
if (-not $Receipt.process_exited -or $Receipt.forced_tree_stop -or $Receipt.timed_out -or $Receipt.cleanup_error) { throw 'UNKNOWN cleanup/timeout; no retry' }
