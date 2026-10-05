param([string] $Config = '.env', [switch] $InitializeDatabase)
. "$PSScriptRoot\Common.ps1"
Import-Sim2ActConfig $Config
if (-not (Test-Path '.venv')) {
    & py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 x64 first.' }
}
Invoke-Sim2ActPython -Arguments @('-m', 'pip', 'install', '-r', 'requirements.lock')
Invoke-Sim2ActPython -Arguments @('-m', 'pip', 'install', '-e', '.', '--no-deps')
if ($InitializeDatabase) {
    # Explicit schema creation, using the migration role selected in this Config.
    Invoke-Sim2ActPython -Arguments @('-m', 'sim2act.cli', 'migrate')
}
