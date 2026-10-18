param([ValidateSet('fetch','build')][string]$Action)
$ErrorActionPreference='Stop'
$taskRoot='D:\Workspaces\AI\rtree-simd-20261018'
$mutex=[Threading.Mutex]::new($false,'Global\Tedd.RTree.PerformanceHost');$held=$false
try {
    try {$held=$mutex.WaitOne(1000)} catch [Threading.AbandonedMutexException] {$held=$true}
    if(-not $held){throw 'Performance host busy'}
    $env:TEMP=$taskRoot;$env:TMP=$taskRoot;$env:CARGO_HOME="$taskRoot\cargo-home"
    $rustbin='C:\Users\tedd\.rustup\toolchains\stable-x86_64-pc-windows-msvc\bin'
    $env:PATH="$rustbin;$env:PATH";$env:RUSTFLAGS='-C target-cpu=native'
    if($Action -eq 'fetch') {
        if(Test-Path -LiteralPath "$taskRoot\native"){throw 'Native preparation already exists'}
        Copy-Item -LiteralPath "$PSScriptRoot\..\mutable-packed\native" -Destination "$taskRoot\native" -Recurse
        Copy-Item -LiteralPath "$taskRoot\static-source\static_aabb2d_index-a511a6327e14a0f0418cea01c401bf147e0e835c" -Destination "$taskRoot\static-aabb" -Recurse
        Copy-Item -LiteralPath "$taskRoot\geo-source\geo-index-e6efbb01d3c298e8963c8b7d1aab40c1bd540715" -Destination "$taskRoot\geo-index" -Recurse
        & "$rustbin\cargo.exe" fetch --locked --manifest-path "$taskRoot\native\Cargo.toml"
    } else {
        $originalPath=$env:PATH
        $vcvars='C:\Program Files\Microsoft Visual Studio\18\Insiders\VC\Auxiliary\Build\vcvars64.bat'
        $environment=cmd /c "`"$vcvars`" >nul && set"
        foreach($line in $environment){if($line -match '^([^=]+)=(.*)$'){[Environment]::SetEnvironmentVariable($matches[1],$matches[2],'Process')}}
        $env:PATH="$env:PATH;$originalPath"
        $sdk='C:\Program Files (x86)\Windows Kits\10'
        $env:LIB="$env:LIB;$sdk\Lib\10.0.26100.0\ucrt\x64;$sdk\Lib\10.0.26100.0\um\x64"
        & "$rustbin\cargo.exe" build --offline --locked --release --manifest-path "$taskRoot\native\Cargo.toml"
    }
    if($LASTEXITCODE -ne 0){throw "$Action failed"}
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}
