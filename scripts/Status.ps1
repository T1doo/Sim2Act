param([string] $Config = '.env', [int] $Port = 8000)
. "$PSScriptRoot\Common.ps1"
Import-Sim2ActConfig $Config
Invoke-Sim2ActPython -Arguments @('scripts/manage.py', 'status', '--port', "$Port")
