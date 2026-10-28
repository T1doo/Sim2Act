param(
    [Parameter(Mandatory=$true)][string] $CandidateRoot,
    [Parameter(Mandatory=$true)][string] $SdkPackage,
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{40}$')][string] $SourceCommit,
    [string] $Compiler = ''
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$desktopRoot = [IO.Path]::GetFullPath($CandidateRoot)
function Assert-Ordinary([string] $Path) {
    $current = Get-Item -LiteralPath $Path -Force
    while ($null -ne $current) {
        if (($current.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Linked path refused: $Path" }
        $current = if ($current -is [IO.DirectoryInfo]) { $current.Parent }
        elseif ($current -is [IO.FileInfo]) { $current.Directory }
        else { throw "Unsupported filesystem object: $Path" }
    }
}
Assert-Ordinary $desktopRoot
if (-not (Test-Path -LiteralPath (Join-Path $desktopRoot 'runtime\python.exe') -PathType Leaf)) { throw 'Existing assembled private Python runtime required.' }
$portableFile = Join-Path $desktopRoot 'portable-manifest.json'
$portable = Get-Content -LiteralPath $portableFile -Raw -Encoding UTF8 | ConvertFrom-Json
if ($portable.format -cne 'sim2act-offline-windows-sqlite-preview.v1' -or $null -eq $portable.files -or $portable.product_commit -cne $SourceCommit) { throw 'Application source commit mismatch; do not attach the new host to an old app.' }
foreach ($entry in $portable.files.PSObject.Properties) {
    if (-not $entry.Name.StartsWith('runtime/',[StringComparison]::Ordinal)) { continue }
    if ($entry.Name -match '(^/|\\|:|(^|/)\.\.(/|$))') { throw 'Invalid runtime manifest path.' }
    $path = Join-Path $desktopRoot $entry.Name
    Assert-Ordinary $path
    $actual = Get-Item -LiteralPath $path
    if ($actual.Length -ne $entry.Value.bytes -or (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $entry.Value.sha256) { throw "Application input changed: $($entry.Name)" }
}
foreach ($name in @('Sim2ActDesktop.cs','desktop.manifest','Build-Desktop.ps1','README.md')) {
    $expected = $portable.files.PSObject.Properties['desktop-build/'+$name]
    if ($null -eq $expected) { throw "Candidate host source missing: $name" }
    $inputPath = Join-Path $PSScriptRoot $name
    Assert-Ordinary $inputPath
    $inputFile = Get-Item -LiteralPath $inputPath
    if ($inputFile.Length -ne $expected.Value.bytes -or (Get-FileHash -LiteralPath $inputPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $expected.Value.sha256) { throw "Invoked host input differs from frozen candidate: $name" }
}
$exe = Join-Path $desktopRoot 'Sim2Act.exe'
if (Test-Path -LiteralPath $exe) { throw 'New candidate directory required; existing EXE is preserved.' }
$package = Get-Item -LiteralPath $SdkPackage
if ($package.Length -ne 9818548 -or (Get-FileHash -LiteralPath $package.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -ne '90778deb1b77e36292828b4b5833c9255c27533f40e0ddd55891ae718944edc4') { throw 'Exact Microsoft WebView2 SDK 1.0.4314.35 package required.' }
if (-not $Compiler) {
    foreach ($relative in @('Microsoft.NET\Framework64\v4.0.30319\csc.exe','Microsoft.NET\Framework\v4.0.30319\csc.exe')) {
        $available = Join-Path $env:WINDIR $relative
        if (Test-Path -LiteralPath $available -PathType Leaf) { $Compiler = $available; break }
    }
}
if (-not $Compiler -or -not (Test-Path -LiteralPath $Compiler -PathType Leaf)) { throw 'Existing .NET Framework C# compiler missing; nothing is installed.' }
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [IO.Compression.ZipFile]::OpenRead($package.FullName)
try {
    $entries = @{
        'lib/net462/Microsoft.Web.WebView2.Core.dll' = 'Microsoft.Web.WebView2.Core.dll'
        'lib/net462/Microsoft.Web.WebView2.WinForms.dll' = 'Microsoft.Web.WebView2.WinForms.dll'
        'runtimes/win-x64/native/WebView2Loader.dll' = 'WebView2Loader.dll'
        'LICENSE.txt' = 'WEBVIEW2-SDK-LICENSE.txt'
    }
    foreach ($name in $entries.Keys) {
        $target = Join-Path $desktopRoot $entries[$name]
        if (Test-Path -LiteralPath $target) { throw "Existing SDK output preserved: $target" }
        $entry = $archive.GetEntry($name)
        if ($null -eq $entry) { throw "SDK member missing: $name" }
        [IO.Compression.ZipFileExtensions]::ExtractToFile($entry,$target,$false)
    }
} finally { $archive.Dispose() }
$temp = Join-Path $desktopRoot 'temp'
if (-not (Test-Path -LiteralPath $temp)) { [void](New-Item -ItemType Directory -Path $temp) }
Assert-Ordinary $temp
$priorTemp,$priorTmp = $env:TEMP,$env:TMP
try {
    $env:TEMP=$temp; $env:TMP=$temp
    $arguments = @('/nologo','/target:winexe','/platform:x64','/optimize+','/langversion:5','/codepage:65001',
        ('/win32manifest:'+(Join-Path $PSScriptRoot 'desktop.manifest')),('/out:'+$exe),
        '/reference:System.Windows.Forms.dll,System.Drawing.dll,System.Web.Extensions.dll',
        ('/reference:'+(Join-Path $desktopRoot 'Microsoft.Web.WebView2.Core.dll')),
        ('/reference:'+(Join-Path $desktopRoot 'Microsoft.Web.WebView2.WinForms.dll')),
        (Join-Path $PSScriptRoot 'Sim2ActDesktop.cs'))
    & $Compiler @arguments 1> (Join-Path $desktopRoot 'desktop-build.stdout.log') 2> (Join-Path $desktopRoot 'desktop-build.stderr.log')
    if ($LASTEXITCODE -ne 0) { throw "Desktop compile failed ($LASTEXITCODE); preserve logs and staged inputs." }
} finally { $env:TEMP=$priorTemp; $env:TMP=$priorTmp }
$files = @{}
foreach ($name in @('Sim2Act.exe','Microsoft.Web.WebView2.Core.dll','Microsoft.Web.WebView2.WinForms.dll','WebView2Loader.dll','WEBVIEW2-SDK-LICENSE.txt')) {
    $file = Get-Item -LiteralPath (Join-Path $desktopRoot $name)
    $files[$name] = @{bytes=$file.Length;sha256=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}
}
$record = @{
    format='sim2act-native-desktop.v1';status='BUILT_NOT_WINDOWS_EXECUTED';host='WINFORMS_WEBVIEW2_NO_BROWSER_FALLBACK';
    source_commit=$SourceCommit;portable_manifest_sha256=(Get-FileHash -LiteralPath $portableFile -Algorithm SHA256).Hash.ToLowerInvariant();
    sdk_version='1.0.4314.35';sdk_package_sha256='90778deb1b77e36292828b4b5833c9255c27533f40e0ddd55891ae718944edc4';
    sdk_url='https://api.nuget.org/v3-flatcontainer/microsoft.web.webview2/1.0.4314.35/microsoft.web.webview2.1.0.4314.35.nupkg';
    host_source_sha256=(Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'Sim2ActDesktop.cs') -Algorithm SHA256).Hash.ToLowerInvariant();
    files=$files
}
$record | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $desktopRoot 'desktop-manifest.json') -Encoding UTF8
Write-Output 'Native desktop EXE built. Runtime/window/lifecycle acceptance remains NOT_RUN.'
