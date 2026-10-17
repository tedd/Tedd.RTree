param([Parameter(Mandatory)][string]$Workspace, [ValidateSet('fetch','build')][string]$Action='build')
$ErrorActionPreference='Stop'
$r=[IO.Path]::GetFullPath($Workspace)
if(-not $r.StartsWith('D:\Workspaces\AI\',[StringComparison]::OrdinalIgnoreCase)){throw 'Invalid workspace'}
$mutex=[Threading.Mutex]::new($false,'Global\Tedd.RTree.PerformanceHost'); $held=$false
try {
    try {$held=$mutex.WaitOne(1000)} catch [Threading.AbandonedMutexException] {$held=$true}
    if(-not $held){throw 'Benchmark host is busy'}
    $env:TEMP=$r; $env:TMP=$r; $env:CARGO_HOME="$r\cargo-home"
    $rustbin='C:\Users\tedd\.rustup\toolchains\stable-x86_64-pc-windows-msvc\bin'
    $env:PATH="$rustbin;$env:PATH"
    $env:RUSTFLAGS='-C target-cpu=native'
    New-Item -ItemType Directory "$r\native\src" -Force | Out-Null
    Copy-Item "$PSScriptRoot\native\Cargo.toml" "$r\native\Cargo.toml"
    Copy-Item "$PSScriptRoot\native\src\*.rs" "$r\native\src"
    if(Test-Path "$PSScriptRoot\native\Cargo.lock"){Copy-Item "$PSScriptRoot\native\Cargo.lock" "$r\native\Cargo.lock"}
    if($Action -eq 'fetch') {
        & "$rustbin\cargo.exe" fetch --manifest-path "$r\native\Cargo.toml"
        if($LASTEXITCODE -ne 0){throw 'Source fetch failed'}
        Copy-Item "$r\native\Cargo.lock" "$PSScriptRoot\native\Cargo.lock"
    } else {
        $vs='C:\Program Files\Microsoft Visual Studio\18\Insiders'
        $originalPath=$env:PATH
        $vcvars="$vs\VC\Auxiliary\Build\vcvars64.bat"
        $environment=cmd /c "`"$vcvars`" >nul && set"
        foreach($line in $environment){if($line -match '^([^=]+)=(.*)$'){[Environment]::SetEnvironmentVariable($matches[1],$matches[2],'Process')}}
        $env:PATH="$env:PATH;$originalPath"
        $sdk='C:\Program Files (x86)\Windows Kits\10'
        $env:LIB="$env:LIB;$sdk\Lib\10.0.26100.0\ucrt\x64;$sdk\Lib\10.0.26100.0\um\x64"
        & "$rustbin\cargo.exe" build --offline --locked --release --manifest-path "$r\native\Cargo.toml"
        if($LASTEXITCODE -ne 0){throw 'Native build failed'}
    }
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}
