param([Parameter(Mandatory=$true)][string] $TestRoot)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
# Invoke the real builder function, not a copied implementation or mock.
$tokens = $null; $parseErrors = $null
$builder = Join-Path $PSScriptRoot 'Build-Desktop.ps1'
$tree = [Management.Automation.Language.Parser]::ParseFile($builder,[ref]$tokens,[ref]$parseErrors)
if ($parseErrors.Count -ne 0) { throw 'Builder parse failed.' }
$functions = @($tree.FindAll({ param($node)
    $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Assert-Ordinary'
},$true))
if ($functions.Count -ne 1) { throw 'Expected the one real Assert-Ordinary definition.' }
. ([scriptblock]::Create($functions[0].Extent.Text))
$pathRoot = [IO.Path]::GetFullPath($TestRoot)
if (Test-Path -LiteralPath $pathRoot) { throw 'New test directory required; existing data preserved.' }
Assert-Ordinary ([IO.Path]::GetDirectoryName($pathRoot))
$leafDirectory = [IO.Directory]::CreateDirectory((Join-Path $pathRoot 'first\second\third'))
$file = Join-Path $leafDirectory.FullName 'ordinary.txt'
[IO.File]::WriteAllText($file,'synthetic ordinary-path regression')
Assert-Ordinary $file
Assert-Ordinary $leafDirectory.FullName
# The original failure occurred after .Parent returned raw DirectoryInfo objects
# without the provider's PSIsContainer extension. Exercise the entire raw chain.
$current = $leafDirectory
$visited = 0
while ($null -ne $current) {
    if ($current -isnot [IO.DirectoryInfo]) { throw 'Raw directory identity lost.' }
    Assert-Ordinary $current.FullName
    $visited++
    $current = $current.Parent
}
if ($visited -lt 4) { throw 'Did not traverse the real ancestor chain.' }
[ordered]@{ status='PASS';powershell=$PSVersionTable.PSVersion.ToString();raw_directory_ancestors=$visited;
    checks=@('ordinary file','ordinary directory','raw DirectoryInfo Parent chain');
    retained_directory=$pathRoot;builder_sha256=(Get-FileHash -LiteralPath $builder -Algorithm SHA256).Hash.ToLowerInvariant()
} | ConvertTo-Json -Depth 5
