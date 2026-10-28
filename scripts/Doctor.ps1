param([string] $Config = '.env', [string] $SpecSelection = '')
. "$PSScriptRoot\Common.ps1"
Import-Sim2ActConfig $Config
$arguments = @('scripts/manage.py', 'doctor')
if ($SpecSelection) { $arguments += @('--spec-selection', $SpecSelection) }
Invoke-Sim2ActPython -Arguments $arguments
