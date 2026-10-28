param([string] $Config = '.env', [int] $Port = 8000, [string] $SpecSelection = '')
. "$PSScriptRoot\Common.ps1"
Import-Sim2ActConfig $Config
$arguments = @('scripts/manage.py', 'start', '--port', "$Port")
if ($SpecSelection) { $arguments += @('--spec-selection', $SpecSelection) }
Invoke-Sim2ActPython -Arguments $arguments
