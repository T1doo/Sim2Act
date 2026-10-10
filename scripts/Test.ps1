param([ValidateSet('Engineering', 'R0')] [string] $Suite = 'Engineering', [string] $CITracePath = '', [switch] $Remaining11)
. "$PSScriptRoot\Common.ps1"
if ($Suite -eq 'R0') { throw 'R0 acceptance is not implemented; F1 engineering tests cannot pass the R0 gate.' }
if ($Remaining11 -and (-not $IsWindows -or $env:GITHUB_ACTIONS -ne 'true' -or -not $CITracePath)) {
    throw 'Remaining11 requires actual Windows GitHub CI and explicit diagnostics; no platform spoofing.'
}
Invoke-Sim2ActPython -Arguments @('-m', 'ruff', 'check', 'src', 'scripts', 'tests')
Invoke-Sim2ActPython -Arguments @('-m', 'mypy', 'src')
$PytestArguments = @('-m', 'pytest', '-q')
if ($CITracePath) {
    $PytestArguments += @('-p', 'scripts.native_pytest_diagnostics', '--ci-diagnostics', $CITracePath)
}
if ($Remaining11) {
    Write-Output 'DIAGNOSTIC_ONLY_REMAINING11: full engineering/Windows acceptance remains NOT_ACCEPTED.'
    $PytestArguments += '--ci-remaining11'
}
Invoke-Sim2ActPython -Arguments $PytestArguments
