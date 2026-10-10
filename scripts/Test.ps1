param([ValidateSet('Engineering', 'R0')] [string] $Suite = 'Engineering', [string] $CITracePath = '')
. "$PSScriptRoot\Common.ps1"
if ($Suite -eq 'R0') { throw 'R0 acceptance is not implemented; F1 engineering tests cannot pass the R0 gate.' }
Invoke-Sim2ActPython -Arguments @('-m', 'ruff', 'check', 'src', 'scripts', 'tests')
Invoke-Sim2ActPython -Arguments @('-m', 'mypy', 'src')
$PytestArguments = @('-m', 'pytest', '-q')
if ($CITracePath) {
    $PytestArguments += @('-p', 'scripts.native_pytest_diagnostics', '--ci-diagnostics', $CITracePath)
}
Invoke-Sim2ActPython -Arguments $PytestArguments
