param([Parameter(Mandatory)][string]$Workspace,[Parameter(Mandatory)][string]$Action,[string]$Stage='candidate')
$ErrorActionPreference='Stop'
$r=[IO.Path]::GetFullPath($Workspace)
if(-not $r.StartsWith('D:\Workspaces\AI\',[StringComparison]::OrdinalIgnoreCase)){throw 'Invalid workspace'}
$mutex=[Threading.Mutex]::new($false,'Global\Tedd.RTree.PerformanceHost');$held=$false
try {
    try {$held=$mutex.WaitOne(1000)} catch [Threading.AbandonedMutexException] {$held=$true}
    if(-not $held){throw 'Performance host busy'}
    $env:TEMP=$r;$env:TMP=$r
    switch($Action) {
        'build' {
            $buildArgs=@('build',"$PSScriptRoot\Bench.csproj",'-t:Rebuild','-c','Release','--artifacts-path',"$r\$Stage-artifacts",'-o',"$r\$Stage-worker",'-p:UseSharedCompilation=false')
            if($Stage -eq 'control'){$buildArgs+="-p:LibraryPath=$r\control\Tedd.RTree.dll"}
            & dotnet @buildArgs
        }
        'test' {
            & dotnet build "$PSScriptRoot\..\..\tests\Tedd.RTree.Tests\Tedd.RTree.Tests.csproj" -c Release --artifacts-path "$r\test-artifacts" -o "$r\tests" -p:UseSharedCompilation=false
            if($LASTEXITCODE -ne 0){throw 'Test build failed'}
            & dotnet exec --fx-version 10.0.13 "$r\tests\Tedd.RTree.Tests.dll"
        }
        'codegen' {
            $names=@('DOTNET_TieredCompilation','DOTNET_JitDisasm','DOTNET_JitDisasmAssemblies','DOTNET_JitStdOutFile');$saved=@{}
            foreach($name in $names){$saved[$name]=[Environment]::GetEnvironmentVariable($name,'Process')}
            try {
                $env:DOTNET_TieredCompilation='0';$env:DOTNET_JitDisasm='*Search* *BulkLoad* *CollectValues* *Center* *Hilbert* *Morton*';$env:DOTNET_JitDisasmAssemblies='Tedd.RTree'
                foreach($coordinate in @('int','double')) {
                    $env:DOTNET_JitStdOutFile="$PSScriptRoot\..\..\Research\2026-10-18-generic-packed\$Stage-$coordinate-jit.txt"
                    & dotnet exec --fx-version 10.0.13 "$r\$Stage-worker\Bench.dll" 3 $coordinate 100000 uniform plain codegen
                    if($LASTEXITCODE -ne 0){throw 'Codegen failed'}
                    $lines=Get-Content -LiteralPath $env:DOTNET_JitStdOutFile | ForEach-Object {$_.TrimEnd()}
                    [IO.File]::WriteAllText([IO.Path]::GetFullPath($env:DOTNET_JitStdOutFile),($lines -join "`n")+"`n")
                }
            } finally {foreach($name in $names){[Environment]::SetEnvironmentVariable($name,$saved[$name],'Process')}}
        }
        {$_ -in 'ordering','transfer','inline','confirmation'} {
            & C:\Python314\python.exe "$PSScriptRoot\run.py" $r "$PSScriptRoot\..\results\generic-packed\$Action" $Action
        }
        default {throw 'Unknown action'}
    }
    if($LASTEXITCODE -ne 0){throw "$Action failed: $LASTEXITCODE"}
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}
