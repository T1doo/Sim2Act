# Same authorized Windows job; normal installed browser only, no OS/security changes.
$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot
if (-not $IsWindows -or $env:GITHUB_ACTIONS -ne 'true' -or -not $env:RUNNER_TEMP) {
    throw 'Actual Windows GitHub runner required; no platform substitution.'
}
$Edge = Join-Path ${env:ProgramFiles(x86)} 'Microsoft\Edge\Application\msedge.exe'
if (-not (Test-Path $Edge)) { throw 'BLOCKED: installed Microsoft Edge unavailable; no browser download/fallback.' }
$Signature = Get-AuthenticodeSignature -LiteralPath $Edge
if ($Signature.Status -ne 'Valid' -or $Signature.SignerCertificate.Subject -notmatch 'Microsoft Corporation') {
    throw 'BLOCKED: installed Edge signature not verified; no replacement installer.'
}
$Inventory = [ordered]@{
    edge_version = (Get-Item $Edge).VersionInfo.ProductVersion
    signature = "$($Signature.Status)"; signer = $Signature.SignerCertificate.Subject
    node = (& node --version); runner = 'windows-2025'
    sandbox_requested = $true; browser_install = $false; added_runner = $false
    job_timeout_minutes = 15; browser_step_timeout_minutes = 4
    win11_acceptance = 'NOT_RUN'; real_model_requests = 0
}
$Inventory | ConvertTo-Json -Compress | Write-Output
$JobRoot = Join-Path $env:RUNNER_TEMP "sim2act-browser-$env:GITHUB_RUN_ID-$env:GITHUB_RUN_ATTEMPT"
New-Item -ItemType Directory -Path $JobRoot -Force | Out-Null
try {
    # Official fixed dependency, integrity-locked, no lifecycle scripts/browser downloads.
    & npm ci --prefix scripts/browser-ci --ignore-scripts --no-audit --no-fund --registry=https://registry.npmjs.org --cache (Join-Path $JobRoot 'npm-cache') --fetch-retries=0 --fetch-timeout=30000
    if ($LASTEXITCODE -ne 0) { throw 'Official browser automation dependency install failed; no alternative source.' }
    $Inventory | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $JobRoot 'inventory.json') -Encoding utf8
    & ./.venv/Scripts/python.exe scripts/windows_browser_ci.py --root $JobRoot
    if ($LASTEXITCODE -ne 0) { throw 'Protected browser verification failed; see synthetic evidence in job log.' }
} finally {
    # Python owns/joins its API child in finally; do not kill unrelated browser/system processes.
    if (Test-Path $JobRoot) { Remove-Item -LiteralPath $JobRoot -Force -Recurse }
}
