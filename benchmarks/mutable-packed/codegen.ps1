param([Parameter(Mandatory)][string]$Workspace,[string]$Stage='candidate-worker',[Parameter(Mandatory)][string]$Output)
$ErrorActionPreference='Stop'
$mutex=[Threading.Mutex]::new($false,'Global\Tedd.RTree.PerformanceHost');$held=$false
$saved=@{}
foreach($name in @('DOTNET_TieredCompilation','DOTNET_JitDisasm','DOTNET_JitDisasmAssemblies','DOTNET_JitStdOutFile')){$saved[$name]=[Environment]::GetEnvironmentVariable($name,'Process')}
try {
    try {$held=$mutex.WaitOne(1000)} catch [Threading.AbandonedMutexException] {$held=$true}
    if(-not $held){throw 'Benchmark host busy'}
    $env:DOTNET_TieredCompilation='0'
    $env:DOTNET_JitDisasm='*Search* *BulkLoad* *CollectValues* *SortIndices* *Encode*'
    $env:DOTNET_JitDisasmAssemblies='Tedd.RTree'
    $env:DOTNET_JitStdOutFile=[IO.Path]::GetFullPath($Output)
    & 'C:\Program Files\dotnet\dotnet.exe' exec --fx-version 10.0.13 "$Workspace\$Stage\Bench.dll" "$Workspace\100000-uniform.txt" codegen
    if($LASTEXITCODE -ne 0){throw 'Code generation run failed'}
    # Normal exit flushes JIT's native output stream. Whitespace normalization preserves instructions.
    $text=Get-Content -LiteralPath $env:DOTNET_JitStdOutFile | ForEach-Object {$_.TrimEnd()}
    [IO.File]::WriteAllText($env:DOTNET_JitStdOutFile,($text -join "`n")+"`n")
} finally {
    foreach($name in $saved.Keys){[Environment]::SetEnvironmentVariable($name,$saved[$name],'Process')}
    if($held){$mutex.ReleaseMutex()};$mutex.Dispose()
}
