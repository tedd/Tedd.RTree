param([Parameter(Mandatory)][string]$Workspace)
$ErrorActionPreference='Stop'
$r=[IO.Path]::GetFullPath($Workspace)
if(-not $r.StartsWith('D:\Workspaces\AI\',[StringComparison]::OrdinalIgnoreCase)){throw 'Invalid scratch workspace'}
# Sources must already have been downloaded and reviewed. No upstream build scripts run here.
$vs='C:\Program Files\Microsoft Visual Studio\18\Insiders'
$vcvars=Join-Path $vs 'VC\Auxiliary\Build\vcvars64.bat'
$originalPath=$env:PATH
$environment=cmd /c "`"$vcvars`" >nul && set"
if($LASTEXITCODE -ne 0){throw 'VC environment failed'}
foreach($line in $environment){if($line -match '^([^=]+)=(.*)$'){[Environment]::SetEnvironmentVariable($matches[1],$matches[2],'Process')}}
$env:PATH="$env:PATH;$originalPath"
$sdk='C:\Program Files (x86)\Windows Kits\10'
$sdkVersion='10.0.26100.0'
$env:INCLUDE="$env:INCLUDE;$sdk\Include\$sdkVersion\ucrt;$sdk\Include\$sdkVersion\shared;$sdk\Include\$sdkVersion\um"
$env:LIB="$env:LIB;$sdk\Lib\$sdkVersion\ucrt\x64;$sdk\Lib\$sdkVersion\um\x64"
$clang=Join-Path $vs 'VC\Tools\Llvm\x64\bin\clang.exe'
$clangpp=Join-Path $vs 'VC\Tools\Llvm\x64\bin\clang++.exe'
$rustbin='C:\Users\tedd\.rustup\toolchains\stable-x86_64-pc-windows-msvc\bin'
$env:PATH="$rustbin;$env:PATH"
$env:TEMP=$r; $env:TMP=$r
$env:CARGO_HOME=Join-Path $r 'cargo-home'
$env:RUSTFLAGS='-C target-cpu=native'
$env:GOCACHE=Join-Path $r 'go-cache'
$env:GOMODCACHE=Join-Path $r 'go-mod-cache'
$env:GOPATH=Join-Path $r 'go-path'
$env:GOTOOLCHAIN='local'
$env:GOPROXY='off'
$env:GOSUMDB='off'
$env:GOTELEMETRY='off'
$env:CGO_ENABLED='0'
& 'C:\Program Files\dotnet\dotnet.exe' build (Join-Path $PSScriptRoot 'Worker.csproj') -c Release --artifacts-path "$r\dotnet-artifacts" -o "$r\dotnet"
if($LASTEXITCODE -ne 0){throw '.NET build failed'}
& $clang -O3 -DNDEBUG -march=native -std=c11 -c "$r\rtree-c\rtree.c" -o "$r\rtree.obj"
if($LASTEXITCODE -ne 0){throw 'C compilation failed'}
& $clangpp -O3 -DNDEBUG -march=native -std=c++17 -DTIDWALL "-I$r\rtree-c" (Join-Path $PSScriptRoot 'native.cpp') "$r\rtree.obj" -o "$r\tidwall.exe"
if($LASTEXITCODE -ne 0){throw 'C worker build failed'}
& $clangpp -O3 -DNDEBUG -march=native -std=c++17 "-I$r\superliminal" (Join-Path $PSScriptRoot 'native.cpp') -o "$r\superliminal.exe"
if($LASTEXITCODE -ne 0){throw 'Superliminal build failed'}
$includes=@(Get-ChildItem "$r\boost\libs" -Recurse -Directory -Filter include | ForEach-Object { '-I'+$_.FullName })
& $clangpp -O3 -DNDEBUG -march=native -std=c++17 -DBOOST_TREE @includes (Join-Path $PSScriptRoot 'native.cpp') -o "$r\boost.exe"
if($LASTEXITCODE -ne 0){throw 'Boost build failed'}
& $clangpp -O3 -DNDEBUG -march=native -std=c++17 -DBOOST_TREE -DBOOST_QUERY @includes (Join-Path $PSScriptRoot 'native.cpp') -o "$r\boost-query.exe"
if($LASTEXITCODE -ne 0){throw 'Boost visitor build failed'}
New-Item -ItemType Directory "$r\rust\src","$r\go-worker","$r\flatbush\node_modules\flatqueue" -Force | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'rust\Cargo.toml') "$r\rust\Cargo.toml"
Copy-Item (Join-Path $PSScriptRoot 'rust\Cargo.lock') "$r\rust\Cargo.lock"
Copy-Item (Join-Path $PSScriptRoot 'rust\src\main.rs') "$r\rust\src\main.rs"
& "$rustbin\cargo.exe" build --offline --locked --release --manifest-path "$r\rust\Cargo.toml"
if($LASTEXITCODE -ne 0){throw 'Rust build failed'}
New-Item -ItemType Directory "$r\static-rust\src" -Force | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'static-rust\Cargo.toml') "$r\static-rust\Cargo.toml"
Copy-Item (Join-Path $PSScriptRoot 'static-rust\Cargo.lock') "$r\static-rust\Cargo.lock"
Copy-Item (Join-Path $PSScriptRoot 'static-rust\src\main.rs') "$r\static-rust\src\main.rs"
& "$rustbin\cargo.exe" build --offline --locked --release --manifest-path "$r\static-rust\Cargo.toml"
if($LASTEXITCODE -ne 0){throw 'Static Rust build failed'}
Copy-Item (Join-Path $PSScriptRoot 'worker.go') "$r\go-worker\main.go"
@"
module spatial-comparison
go 1.21
require github.com/tidwall/rtree v0.0.0
require github.com/tidwall/geoindex v1.7.0
replace github.com/tidwall/rtree => ../rtree-go
replace github.com/tidwall/geoindex => ../geoindex
"@ | Set-Content "$r\go-worker\go.mod"
Push-Location "$r\go-worker"
try { & "$r\go\bin\go.exe" build -mod=mod -trimpath -o "$r\go-worker.exe" .; if($LASTEXITCODE -ne 0){throw 'Go build failed'} }
finally { Pop-Location }
Copy-Item "$r\flatqueue\index.js","$r\flatqueue\package.json" "$r\flatbush\node_modules\flatqueue"
Copy-Item (Join-Path $PSScriptRoot 'worker.mjs') "$r\worker.mjs"
