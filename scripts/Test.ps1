param([ValidateSet('Engineering', 'R0')] [string] $Suite = 'Engineering')
. "$PSScriptRoot\Common.ps1"
if ($Suite -eq 'R0') { throw 'R0 acceptance is not implemented; F1 engineering tests cannot pass the R0 gate.' }
Invoke-Sim2ActPython -Arguments @('-m', 'ruff', 'check', 'src', 'scripts', 'tests')
Invoke-Sim2ActPython -Arguments @('-m', 'mypy', 'src')
Invoke-Sim2ActPython -Arguments @('-m', 'pytest', '-q')
