param([Parameter(Mandatory)][string]$Workspace, [Parameter(Mandatory)][string]$Action)
$ErrorActionPreference='Stop'
$r=[IO.Path]::GetFullPath($Workspace)
if(-not $r.StartsWith('D:\Workspaces\AI\',[StringComparison]::OrdinalIgnoreCase)){throw 'Invalid task workspace'}
$mutex=[Threading.Mutex]::new($false,'Global\Tedd.RTree.PerformanceHost')
$held=$false
try {
    try {$held=$mutex.WaitOne(1000)} catch [Threading.AbandonedMutexException] {$held=$true}
    if(-not $held){throw 'Another cooperating benchmark owns the host lock'}
    $env:TEMP=$r; $env:TMP=$r
    switch($Action){
        'build-control' {
            & 'C:\Program Files\dotnet\dotnet.exe' build "$PSScriptRoot\Bench.csproj" -c Release "-p:LibraryPath=$r\control\Tedd.RTree.dll" --artifacts-path "$r\control-worker-artifacts" -o "$r\control-worker"
        }
        'build-algorithm' {
            & 'C:\Program Files\dotnet\dotnet.exe' build "$PSScriptRoot\Bench.csproj" -c Release --artifacts-path "$r\algorithm-artifacts" -o "$r\algorithm-worker"
        }
        'build-algorithm-reference' {
            if(-not (Test-Path "$r\algorithm-library.dll")){Copy-Item "$r\algorithm-worker\Tedd.RTree.dll" "$r\algorithm-library.dll"}
            New-Item -ItemType Directory "$r\algorithm-library" -Force | Out-Null
            Copy-Item "$r\algorithm-library.dll" "$r\algorithm-library\Tedd.RTree.dll"
            & 'C:\Program Files\dotnet\dotnet.exe' build "$PSScriptRoot\Bench.csproj" -t:Rebuild -c Release "-p:LibraryPath=$r\algorithm-library\Tedd.RTree.dll" --artifacts-path "$r\algorithm-reference-artifacts" -o "$r\algorithm-worker"
            if($LASTEXITCODE -ne 0){throw 'Algorithm reference build failed'}
        }
        'build-candidate' {
            & 'C:\Program Files\dotnet\dotnet.exe' build "$PSScriptRoot\Bench.csproj" -c Release --artifacts-path "$r\candidate-artifacts" -o "$r\candidate-worker"
        }
        'build-layout-reference' {
            New-Item -ItemType Directory "$r\layout-library" -Force | Out-Null
            if(-not (Test-Path "$r\layout-library\Tedd.RTree.dll")){Copy-Item "$r\candidate-worker\Tedd.RTree.dll" "$r\layout-library\Tedd.RTree.dll"}
            & 'C:\Program Files\dotnet\dotnet.exe' build "$PSScriptRoot\Bench.csproj" -t:Rebuild -c Release "-p:LibraryPath=$r\layout-library\Tedd.RTree.dll" --artifacts-path "$r\layout-reference-artifacts" -o "$r\layout-worker"
        }
        {$_ -in 'build-copy-reference','build-input-reference','build-radix-reference','build-inline-reference','build-fill-reference','build-scale-reference','build-scratch-reference'} {
            $stageName=$Action.Substring(6,$Action.Length-16)
            New-Item -ItemType Directory "$r\$stageName-library" -Force | Out-Null
            if(-not (Test-Path "$r\$stageName-library\Tedd.RTree.dll")){Copy-Item "$r\candidate-worker\Tedd.RTree.dll" "$r\$stageName-library\Tedd.RTree.dll"}
            & 'C:\Program Files\dotnet\dotnet.exe' build "$PSScriptRoot\Bench.csproj" -t:Rebuild -c Release "-p:LibraryPath=$r\$stageName-library\Tedd.RTree.dll" --artifacts-path "$r\$stageName-reference-artifacts" -o "$r\$stageName-worker"
        }
        'test' {
            & 'C:\Program Files\dotnet\dotnet.exe' build "$PSScriptRoot\..\..\tests\Tedd.RTree.Tests\Tedd.RTree.Tests.csproj" -c Release --artifacts-path "$r\test-artifacts" -o "$r\tests"
            if($LASTEXITCODE -ne 0){throw 'Test build failed'}
            & 'C:\Program Files\dotnet\dotnet.exe' "$r\tests\Tedd.RTree.Tests.dll"
        }
        {$_ -in 'algorithm','layout','copy','input','radix','inline','span','fill','scale','scratch','confirmation'} {
            $output="$PSScriptRoot\..\results\mutable-packed\$Action"
            & 'C:\Python314\python.exe' "$PSScriptRoot\run.py" $r $output $Action
        }
        default {throw 'Unknown driver action'}
    }
    if($LASTEXITCODE -ne 0){throw "$Action failed: $LASTEXITCODE"}
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}
