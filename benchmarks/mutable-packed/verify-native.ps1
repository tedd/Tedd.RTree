param([Parameter(Mandatory)][string]$Workspace)
$ErrorActionPreference='Stop'
$r=[IO.Path]::GetFullPath($Workspace)
if(-not $r.StartsWith('D:\Workspaces\AI\',[StringComparison]::OrdinalIgnoreCase)){throw 'Invalid workspace'}
$mutex=[Threading.Mutex]::new($false,'Global\Tedd.RTree.PerformanceHost');$held=$false
$savedPath=$env:PACKED_NATIVE_PATH
try {
    try {$held=$mutex.WaitOne(1000)} catch [Threading.AbandonedMutexException] {$held=$true}
    if(-not $held){throw 'Benchmark host busy'}
    $env:PACKED_NATIVE_PATH="$r\native\target\release\packed_native.dll"
    $records=@()
    foreach($n in @(0,1,16,17)) {
        $rows=[Collections.Generic.List[string]]::new();$rows.Add([string]$n)
        for($i=0;$i -lt $n;$i++) {
            $x=($i % 4)-2
            $rows.Add("$x -1 $($x+1) 1")
        }
        foreach($q in @('0 0 0 0','-3 -2 3 2','1 1 1 1','100 100 101 101','-2 -1 -2 -1','-1 -1 0 1','-3 -3 -2 -1','2 1 2 1')){$rows.Add($q)}
        $fixture="$r\boundary-$n.txt"
        [IO.File]::WriteAllLines($fixture,$rows)
        foreach($mode in @('static','geo-hilbert','geo-str')) {
            $log="$r\boundary-$n-$mode.log"
            & 'C:\Program Files\dotnet\dotnet.exe' "$r\candidate-worker\Bench.dll" $fixture "native-$mode" *> $log
            if($LASTEXITCODE -ne 0 -or -not (Select-String -LiteralPath $log -Pattern 'validated=8' -Quiet)){throw "Interop boundary failure: $n/$mode"}
            $records+=@{count=$n;mode=$mode;validated_queries=8;exit_code=$LASTEXITCODE}
        }
    }
    $result=@{checks=$records;native_sha256=(Get-FileHash -LiteralPath $env:PACKED_NATIVE_PATH -Algorithm SHA256).Hash;scope='Empty, duplicate bounds, inclusive contacts, negative coordinates, short-leaf boundary 16/17. Supplemental correctness only; timings excluded.'}
    $result | ConvertTo-Json -Depth 5 | Set-Content "$PSScriptRoot\..\results\mutable-packed\confirmation\native-boundaries.json"
} finally {$env:PACKED_NATIVE_PATH=$savedPath;if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}
