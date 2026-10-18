param([Parameter(Mandatory)][string]$Workspace,[Parameter(Mandatory)][string]$Action,[string]$Stage='candidate')
$ErrorActionPreference='Stop'
$r=[IO.Path]::GetFullPath($Workspace)
if($r -ne 'D:\Workspaces\AI\rtree-mutation-regressions'){throw 'Invalid workspace'}
$mutex=[Threading.Mutex]::new($false,'Global\Tedd.RTree.PerformanceHost');$held=$false
try {
    try {$held=$mutex.WaitOne(45000)} catch [Threading.AbandonedMutexException] {$held=$true}
    if(-not $held){throw 'Performance host busy'}
    $env:TEMP=$r;$env:TMP=$r
    switch($Action) {
        'build' {
            $project=if($Stage -in 'old','baseline','metrics'){"$r\$Stage-source\src\Tedd.RTree\Tedd.RTree.csproj"}else{"$PSScriptRoot\..\..\src\Tedd.RTree\Tedd.RTree.csproj"}
            & dotnet build $project -t:Rebuild -c Release --artifacts-path "$r\$Stage-library-artifacts" -o "$r\$Stage-library" -p:UseSharedCompilation=false
            if($LASTEXITCODE -ne 0){throw 'Library build failed'}
            & dotnet build "$PSScriptRoot\..\generic-packed\Bench.csproj" -t:Rebuild -c Release --artifacts-path "$r\$Stage-worker-artifacts" -o "$r\$Stage-worker" -p:UseSharedCompilation=false "-p:LibraryPath=$r\$Stage-library\Tedd.RTree.dll"
        }
        'test' {
            & dotnet build "$PSScriptRoot\..\..\tests\Tedd.RTree.Tests\Tedd.RTree.Tests.csproj" -c Release --artifacts-path "$r\test-artifacts" -o "$r\tests" -p:UseSharedCompilation=false
            if($LASTEXITCODE -ne 0){throw 'Test build failed'}
            & dotnet exec --fx-version 10.0.13 "$r\tests\Tedd.RTree.Tests.dll"
        }
        'caller' {
            & dotnet build "$PSScriptRoot\..\generic-packed\Bench.csproj" -t:Rebuild -c Release --artifacts-path "$r\caller-artifacts" -o "$r\caller" -p:UseSharedCompilation=false "-p:LibraryPath=$r\baseline-library\Tedd.RTree.dll"
            if($LASTEXITCODE -ne 0){throw 'Caller build failed'}
            foreach($variant in @('old','baseline','metrics','mutation','candidate')) {
                if(-not (Test-Path -LiteralPath "$r\$variant-library\Tedd.RTree.dll")){continue}
                New-Item -ItemType Directory -Path "$r\$variant-worker" -Force | Out-Null
                Get-ChildItem -LiteralPath "$r\caller" -File | Where-Object {$_.Name -notlike 'Tedd.RTree.*'} | Copy-Item -Destination "$r\$variant-worker"
                Copy-Item -LiteralPath "$r\$variant-library\Tedd.RTree.dll" -Destination "$r\$variant-worker\Tedd.RTree.dll"
            }
        }
        'codegen' {
            $names=@('DOTNET_TieredCompilation','DOTNET_JitDisasm','DOTNET_JitDisasmAssemblies','DOTNET_JitStdOutFile');$saved=@{}
            foreach($name in $names){$saved[$name]=[Environment]::GetEnvironmentVariable($name,'Process')}
            try {
                $env:DOTNET_TieredCompilation='0';$env:DOTNET_JitDisasm='*Split* *ChooseSubtree* *Search* *CollectValues* *Volume* *Area* *IntegerExtent* *BulkLoad* *SortIndices* *Normalize* *Morton* *Encode*';$env:DOTNET_JitDisasmAssemblies='Tedd.RTree'
                foreach($case in @(@('3','int','plain'),@('3','double','plain'),@('2','long','plain'),@('2','double','original'))) {
                    $coordinate=$case[1];$label=if($case[2] -eq 'original'){'original'}else{$coordinate}
                    $env:DOTNET_JitStdOutFile="$PSScriptRoot\..\..\Research\2026-10-18-mutation-regressions\$Stage-$label-jit.txt"
                    if(Test-Path -LiteralPath $env:DOTNET_JitStdOutFile){throw 'Do not append to frozen code evidence'}
                    & dotnet exec --fx-version 10.0.13 "$r\$Stage-worker\Bench.dll" $case[0] $coordinate 10000 clustered $case[2] > "$r\$Stage-$label-codegen.out"
                    if($LASTEXITCODE -ne 0){throw 'Codegen failed'}
                    $lines=Get-Content -LiteralPath $env:DOTNET_JitStdOutFile | ForEach-Object {$_.TrimEnd()}
                    [IO.File]::WriteAllText([IO.Path]::GetFullPath($env:DOTNET_JitStdOutFile),($lines -join "`n")+"`n")
                }
            } finally {foreach($name in $names){[Environment]::SetEnvironmentVariable($name,$saved[$name],'Process')}}
        }
        'validate' {
            & dotnet build "$PSScriptRoot\..\..\Tedd.RTree.sln" -c Release --artifacts-path "$r\full-artifacts" -p:UseSharedCompilation=false
            if($LASTEXITCODE -ne 0){throw 'Solution build failed'}
            foreach($project in @('Tedd.RTree.Tests','Tedd.RTree.Benchmarks')) {
                $assemblies=@(Get-ChildItem -LiteralPath "$r\full-artifacts\bin\$project" -Recurse -Filter "$project.dll")
                if($assemblies.Count -ne 1){throw 'Ambiguous validation assembly'}
                $arguments=@('exec','--fx-version','10.0.13',$assemblies[0].FullName)
                if($project -eq 'Tedd.RTree.Benchmarks'){$arguments+='--validate-packages'}
                & dotnet @arguments
                if($LASTEXITCODE -ne 0){throw "$project validation failed"}
            }
        }
        'stability' {
            New-Item -ItemType Directory -Path "$r\alias-worker" -Force | Out-Null
            Get-ChildItem -LiteralPath "$r\baseline-worker" -File | Copy-Item -Destination "$r\alias-worker"
            & C:\Python314\python.exe "$PSScriptRoot\stability.py" $r
        }
        'query-guard' {
            Get-ChildItem -LiteralPath "$r\baseline-worker" -File | Copy-Item -Destination "$r\alias-worker"
            & C:\Python314\python.exe "$PSScriptRoot\final-query-guard.py" $r
        }
        'snapshot-release' {
            if(Test-Path -LiteralPath "$r\release-worker"){throw 'Frozen release worker already exists'}
            Copy-Item -LiteralPath "$r\candidate-worker" -Destination "$r\release-worker" -Recurse
        }
        {$_ -in 'exploration','exploration-metrics','exploration-metrics-matched','confirmation','adverse','integer','union-inline','final'} {
            & C:\Python314\python.exe "$PSScriptRoot\run.py" $r "$PSScriptRoot\..\results\mutation-regressions\$Action" $Action
        }
        default {throw 'Unknown action'}
    }
    if($null -ne $LASTEXITCODE -and $LASTEXITCODE -ne 0){throw "$Action failed: $LASTEXITCODE"}
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}
