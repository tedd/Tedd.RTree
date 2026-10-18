param([ValidateSet('build','measure')][string]$Action)
$ErrorActionPreference='Stop'
$r='D:\Workspaces\AI\rtree-csharp-charts'
$repository=[IO.Path]::GetFullPath("$PSScriptRoot\..\..")
$mutex=[Threading.Mutex]::new($false,'Global\Tedd.RTree.PerformanceHost');$held=$false
try {
    try {$held=$mutex.WaitOne(45000)} catch [Threading.AbandonedMutexException] {$held=$true}
    if(-not $held){throw 'Performance host busy'}
    New-Item -ItemType Directory -Path $r -Force | Out-Null
    $env:TEMP=$r;$env:TMP=$r;$env:DOTNET_CLI_HOME="$r\dotnet-home"
    $env:DOTNET_CLI_TELEMETRY_OPTOUT='1';$env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1'
    $env:DOTNET_GENERATE_ASPNET_CERTIFICATE='false'
    $env:MSBUILDDISABLENODEREUSE='1';$env:NUGET_PACKAGES="$r\packages";$env:NUGET_HTTP_CACHE_PATH="$r\http-cache"
    if($Action -eq 'build') {
        foreach($package in @('rbush','nettopologysuite','rtree','enyim.collections.rtree')) {
            if(-not (Test-Path -LiteralPath "$r\packages\$package")) {
                New-Item -ItemType Directory -Path "$r\packages" -Force | Out-Null
                Copy-Item -LiteralPath "C:\Users\tedd\.nuget\packages\$package" -Destination "$r\packages\$package" -Recurse
            }
        }
        & dotnet build "$PSScriptRoot\Bench.csproj" -c Release --artifacts-path "$r\artifacts" -o "$r\worker" -p:UseSharedCompilation=false
    } else { & C:\Python314\python.exe "$PSScriptRoot\run.py" $r "$repository\benchmarks\results\csharp-charts" }
    if($LASTEXITCODE -ne 0){throw "$Action failed"}
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}
