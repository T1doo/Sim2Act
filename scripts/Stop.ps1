param([string] $Config = '.env')
. "$PSScriptRoot\Common.ps1"
Import-Sim2ActConfig $Config
Invoke-Sim2ActPython -Arguments @('scripts/manage.py', 'stop')
