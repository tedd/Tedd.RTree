param([Parameter(Mandatory)][string]$Workspace)
$ErrorActionPreference='Stop'
$r=[IO.Path]::GetFullPath($Workspace)
if(-not $r.StartsWith('D:\Workspaces\AI\',[StringComparison]::OrdinalIgnoreCase)){throw 'Invalid scratch workspace'}
if(Test-Path -LiteralPath $r){throw 'Use a new, dedicated workspace'}
New-Item -ItemType Directory -Path $r | Out-Null
$lock=Get-Content (Join-Path $PSScriptRoot 'sources.lock.json') -Raw | ConvertFrom-Json
foreach($source in $lock.sources){
    $path=Join-Path $r $source.name
    & git init --quiet $path
    & git -C $path remote add origin $source.url
    & git -C $path fetch --quiet --depth 1 origin $source.commit
    if($LASTEXITCODE -ne 0){throw "Fetch failed: $($source.name)"}
    & git -C $path checkout --quiet --detach FETCH_HEAD
    if($LASTEXITCODE -ne 0){throw "Checkout failed: $($source.name)"}
}
$modules=@($lock.boostSubmodules | ForEach-Object {($_.Trim() -split ' ')[1]})
& git -C "$r\boost" submodule update --init --depth 1 -- @modules
if($LASTEXITCODE -ne 0){throw 'Boost header fetch failed'}
$goVersion=($lock.goVersion -split ' ')[2]
$archive="$goVersion.windows-amd64.zip"
Invoke-WebRequest "https://go.dev/dl/$archive" -OutFile "$r\go.zip"
if((Get-FileHash "$r\go.zip" -Algorithm SHA256).Hash.ToLower() -ne $lock.goArchiveSha256){throw 'Go checksum mismatch'}
Expand-Archive "$r\go.zip" -DestinationPath $r
New-Item -ItemType Directory "$r\rust\src" -Force | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'rust\Cargo.toml') "$r\rust\Cargo.toml"
Copy-Item (Join-Path $PSScriptRoot 'rust\Cargo.lock') "$r\rust\Cargo.lock"
Copy-Item (Join-Path $PSScriptRoot 'rust\src\main.rs') "$r\rust\src\main.rs"
$env:CARGO_HOME=Join-Path $r 'cargo-home'
& 'C:\Users\tedd\.rustup\toolchains\stable-x86_64-pc-windows-msvc\bin\cargo.exe' fetch --locked --manifest-path "$r\rust\Cargo.toml"
if($LASTEXITCODE -ne 0){throw 'Rust source fetch failed'}
New-Item -ItemType Directory "$r\static-rust\src" -Force | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'static-rust\Cargo.toml') "$r\static-rust\Cargo.toml"
Copy-Item (Join-Path $PSScriptRoot 'static-rust\Cargo.lock') "$r\static-rust\Cargo.lock"
Copy-Item (Join-Path $PSScriptRoot 'static-rust\src\main.rs') "$r\static-rust\src\main.rs"
& 'C:\Users\tedd\.rustup\toolchains\stable-x86_64-pc-windows-msvc\bin\cargo.exe' fetch --locked --manifest-path "$r\static-rust\Cargo.toml"
if($LASTEXITCODE -ne 0){throw 'Static Rust source fetch failed'}
# Fetch only: inspect source/build scripts before invoking build.ps1.
