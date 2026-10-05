$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot
function Import-Sim2ActConfig([string] $Config) {
    if (-not (Test-Path -LiteralPath $Config)) { throw 'Create a local configuration from .env.example first.' }
    foreach ($line in Get-Content -LiteralPath $Config -Encoding utf8) {
        if ($line.Trim() -eq '' -or $line.TrimStart().StartsWith('#')) { continue }
        if ($line -notmatch '^(SIM2ACT_[A-Z_]+)=(.*)$') { throw 'Invalid configuration line; values are not printed.' }
        [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], 'Process')
    }
}
function Get-Sim2ActPython {
    $python = Join-Path $RepoRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python)) { throw 'Run Setup.ps1 with Python 3.12 installed.' }
    return $python
}
function Invoke-Sim2ActPython([string[]] $Arguments) {
    $python = Get-Sim2ActPython
    & $python @Arguments
    if ($LASTEXITCODE -ne 0) { throw 'Command failed; inspect local diagnostics.' }
}
