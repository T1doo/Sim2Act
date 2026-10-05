param([string] $Config = '.env', [switch] $InitializeDatabase)
. "$PSScriptRoot\Common.ps1"
Import-Sim2ActConfig $Config
if (-not (Test-Path '.venv')) {
    & py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 x64 first.' }
}
Invoke-Sim2ActPython -Arguments @('-m', 'pip', 'install', '--no-deps', '--only-binary=:all:', '-r', 'requirements-windows.lock')
# Build with the explicitly locked backend, without an independently resolved build environment.
Invoke-Sim2ActPython -Arguments @('-m', 'pip', 'install', '-e', '.', '--no-deps', '--no-build-isolation')
Invoke-Sim2ActPython -Arguments @('-m', 'pip', 'check')
if ($InitializeDatabase) {
    # Explicit schema creation, using the migration role selected in this Config.
    Invoke-Sim2ActPython -Arguments @('-m', 'sim2act.cli', 'migrate')
}
