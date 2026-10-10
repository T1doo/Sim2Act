param([ValidateSet('Setup', 'Test', 'Report', 'Cleanup')] [string] $Phase)
$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot
if (-not $IsWindows -or $env:GITHUB_ACTIONS -ne 'true' -or -not $env:RUNNER_TEMP) {
    throw 'This harness requires the actual Windows GitHub runner; no platform spoofing.'
}
$JobRoot = Join-Path $env:RUNNER_TEMP "sim2act-native-$env:GITHUB_RUN_ID-$env:GITHUB_RUN_ATTEMPT"
$Cluster = Join-Path $JobRoot 'pgdata'
$Config = Join-Path $JobRoot 'runtime.env'
$TestOwnerConfig = Join-Path $JobRoot 'test-owner.env'
$PGBinary = $env:PGBIN
if (-not $PGBinary -or -not (Test-Path (Join-Path $PGBinary 'pg_ctl.exe'))) {
    throw 'Runner PostgreSQL binaries unavailable; no fallback installer or container.'
}
function Invoke-PG([string] $Program, [string[]] $Arguments) {
    & (Join-Path $PGBinary "$Program.exe") @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Native PostgreSQL $Program failed." }
}
function Set-JobVariable([string] $Name, [string] $Value) {
    [Environment]::SetEnvironmentVariable($Name, $Value, 'Process')
    [IO.File]::AppendAllText($env:GITHUB_ENV, "$Name=$Value`n", [Text.UTF8Encoding]::new($false))
}
function Write-Config([string] $File, [string] $Url) {
    $DataRoot = Join-Path $JobRoot '中文 空格应用数据'
    [IO.File]::WriteAllText($File, @"
SIM2ACT_DATABASE_URL=$Url
SIM2ACT_DATA_DIR=$DataRoot
SIM2ACT_MODEL_MODE=mock
SIM2ACT_LIVE_ENABLED=false
SIM2ACT_MODEL=intern-s2
SIM2ACT_INTERN_TOKEN=
INTERN_API_TOKEN=
"@, [Text.UTF8Encoding]::new($false))
}
if ($Phase -eq 'Setup') {
    New-Item -ItemType Directory -Path $JobRoot -Force | Out-Null
    $OS = Get-CimInstance Win32_OperatingSystem
    $Identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $Principal = [Security.Principal.WindowsPrincipal]::new($Identity)
    $Context = [ordered]@{
        commit = $env:GITHUB_SHA; runner = 'windows-2025'; image = $env:ImageVersion
        os_caption = $OS.Caption; os_version = $OS.Version; os_build = $OS.BuildNumber
        powershell = "$($PSVersionTable.PSVersion)"
        admin_context = $Principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
        uac_enable_lua = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System').EnableLUA
        win11_acceptance = 'NOT_RUN - Windows Server is not Windows 11'
        model = 'MOCK; real model budget 0'; database = 'native temporary localhost cluster'
    }
    $Context | ConvertTo-Json -Compress | Write-Output
    "## Actual Windows Server runner context`n`n$($Context | ConvertTo-Json)`n" | Add-Content $env:GITHUB_STEP_SUMMARY
    & python -c "import sys,struct,os; assert os.name=='nt' and sys.version_info[:2]==(3,12) and struct.calcsize('P')==8; print('Python '+sys.version.split()[0]+' native x64 PASS')"
    if ($LASTEXITCODE -ne 0) { throw 'Python native x64 smoke failed.' }
    $Password = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).ToLowerInvariant()
    $RuntimePassword = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).ToLowerInvariant()
    # GitHub's masking commands are consumed by the log processor; credentials are never echoed.
    Write-Output "::add-mask::$Password"
    Write-Output "::add-mask::$RuntimePassword"
    $Suffix = [Guid]::NewGuid().ToString('N').Substring(0, 12)
    $AdminUser = "ci_owner_$Suffix"
    $RuntimeUser = "ci_runtime_$Suffix"
    $Listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
    $Listener.Start(); $Port = $Listener.LocalEndpoint.Port; $Listener.Stop()
    $PasswordFile = Join-Path $JobRoot 'initdb-password.txt'
    [IO.File]::WriteAllText($PasswordFile, $Password, [Text.UTF8Encoding]::new($false))
    try {
        Invoke-PG -Program 'initdb' -Arguments @('-D', $Cluster, '-U', $AdminUser, '--auth=scram-sha-256', '--encoding=UTF8', '--locale=C', "--pwfile=$PasswordFile")
    } finally { Remove-Item -LiteralPath $PasswordFile -Force -ErrorAction SilentlyContinue }
    "`nlisten_addresses = '127.0.0.1'`nport = $Port`n" | Add-Content (Join-Path $Cluster 'postgresql.conf')
    Invoke-PG -Program 'pg_ctl' -Arguments @('-D', $Cluster, '-l', (Join-Path $JobRoot 'postgres.log'), '-w', '-t', '30', 'start')
    Invoke-PG -Program 'postgres' -Arguments @('--version')
    $env:PGPASSWORD = $Password
    Invoke-PG -Program 'createdb' -Arguments @('-h', '127.0.0.1', '-p', "$Port", '-U', $AdminUser, '--no-password', 'sim2act_ci')
    $AdminUrl = "postgresql+psycopg://${AdminUser}:${Password}@127.0.0.1:${Port}/sim2act_ci"
    $RuntimeUrl = "postgresql+psycopg://${RuntimeUser}:${RuntimePassword}@127.0.0.1:${Port}/sim2act_ci"
    Write-Output "::add-mask::$AdminUrl"
    Write-Output "::add-mask::$RuntimeUrl"
    # The owner URL must never enter GITHUB_ENV or later smoke/runtime environments.
    [IO.File]::WriteAllText($TestOwnerConfig, "SIM2ACT_TEST_DATABASE_URL=$AdminUrl", [Text.UTF8Encoding]::new($false))
    Set-JobVariable 'SIM2ACT_CI_CONFIG' $Config
    $MigrationConfig = Join-Path $JobRoot 'migration.env'
    Write-Config $MigrationConfig $AdminUrl
    if (Test-Path '.venv') { throw 'Fresh checkout must have no venv; first-install branch required.' }
    & py -3.12 -c "import sys,os,struct; assert os.name=='nt' and sys.version_info[:3]==(3,12,10) and struct.calcsize('P')==8; print('PASS: real py -3.12 launcher selects '+sys.version.split()[0]+' x64 at '+sys.executable)"
    if ($LASTEXITCODE -ne 0) { throw 'Native Python launcher 3.12.10 x64 prerequisite failed.' }
    # Setup itself must create the missing venv via its unchanged py-launcher branch.
    & ./scripts/Setup.ps1 -Config $MigrationConfig -InitializeDatabase
    & ./.venv/Scripts/python.exe scripts/windows_ci_dependencies.py
    if ($LASTEXITCODE -ne 0) { throw 'Windows lock or first-created interpreter verification failed.' }
    $SQLFile = Join-Path $JobRoot 'runtime-role.sql'
    [IO.File]::WriteAllText($SQLFile, @"
CREATE ROLE $RuntimeUser LOGIN PASSWORD '$RuntimePassword' NOSUPERUSER NOCREATEDB NOCREATEROLE;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO $RuntimeUser;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO $RuntimeUser;
"@, [Text.UTF8Encoding]::new($false))
    try { Invoke-PG -Program 'psql' -Arguments @('-h', '127.0.0.1', '-p', "$Port", '-U', $AdminUser, '-d', 'sim2act_ci', '--no-password', '-v', 'ON_ERROR_STOP=1', '-f', $SQLFile) }
    finally { Remove-Item -LiteralPath $SQLFile -Force -ErrorAction SilentlyContinue; Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue }
    Write-Config $Config $RuntimeUrl
    Remove-Item -LiteralPath $MigrationConfig -Force
    'PASS: native PostgreSQL / existing Setup / migration; runtime role has no DDL grant.' | Add-Content $env:GITHUB_STEP_SUMMARY
    # Engineering HTTP/DOM drivers need the already qualified developer lock.
    # Install into this job's temporary directory, before pytest can use Node.
    $NodeTools = Join-Path $JobRoot 'engineering-node'
    New-Item -ItemType Directory -Path $NodeTools -Force | Out-Null
    Copy-Item -LiteralPath 'scripts/engineering-ci/package.json', 'scripts/engineering-ci/package-lock.json' -Destination $NodeTools
    & npm ci --prefix $NodeTools --ignore-scripts --no-audit --no-fund --registry=https://registry.npmjs.org --cache (Join-Path $JobRoot 'npm-cache') --fetch-retries=0 --fetch-timeout=30000
    if ($LASTEXITCODE -ne 0) { throw 'Locked engineering Node dependency install failed; no alternative source.' }
} elseif ($Phase -eq 'Test') {
    $Xml = Join-Path $JobRoot 'engineering.xml'
    $env:PYTEST_ADDOPTS = "--junitxml=`"$Xml`" --durations=30 -ra"
    $PreviousNodePath = $env:NODE_PATH
    try {
        $env:NODE_PATH = Join-Path $JobRoot 'engineering-node/node_modules'
        & node -e 'const p=require.resolve("jsdom/package.json"); if(require(p).version!=="30.1.2" || !p.startsWith(process.argv[1]+require("path").sep))process.exit(1); console.log("PASS: owned locked engineering jsdom30.1.2 before pytest")' $env:NODE_PATH
        if ($LASTEXITCODE -ne 0) { throw 'Owned locked engineering jsdom verification failed.' }
        $env:SIM2ACT_TEST_DATABASE_URL = ([IO.File]::ReadAllText($TestOwnerConfig) -split '=', 2)[1]
        & ./scripts/Test.ps1 -Suite Engineering -CITracePath (Join-Path $JobRoot 'pytest-events.jsonl')
    } finally {
        $env:NODE_PATH = $PreviousNodePath
        Remove-Item Env:SIM2ACT_TEST_DATABASE_URL -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $TestOwnerConfig -Force -ErrorAction SilentlyContinue
    }
} elseif ($Phase -eq 'Report') {
    $Xml = Join-Path $JobRoot 'engineering.xml'
    & ./.venv/Scripts/python.exe scripts/native_pytest_diagnostics.py --report (Join-Path $JobRoot 'pytest-events.jsonl') --junit $Xml
    if ($LASTEXITCODE -ne 0) { throw 'Report step failed.' }
} else {
    try {
        if ((Test-Path '.venv/Scripts/python.exe') -and (Test-Path $Config)) {
            & ./scripts/Stop.ps1 -Config $Config
        }
    } finally {
        if (Test-Path (Join-Path $Cluster 'postmaster.pid')) {
            Invoke-PG -Program 'pg_ctl' -Arguments @('-D', $Cluster, '-w', '-t', '30', '-m', 'fast', 'stop')
        }
        if (Test-Path $JobRoot) { Remove-Item -LiteralPath $JobRoot -Force -Recurse }
    }
    'Cleanup complete: owned local processes and temporary job cluster; no deployment.' | Add-Content $env:GITHUB_STEP_SUMMARY
}
