param([ValidateSet('fetch','build','measure')][string]$Action)
$ErrorActionPreference='Stop'
$r='D:\Workspaces\AI\rtree-mutation-regressions\cross'
$repository=[IO.Path]::GetFullPath("$PSScriptRoot\..\..")
$mutex=[Threading.Mutex]::new($false,'Global\Tedd.RTree.PerformanceHost');$held=$false
try {
    try {$held=$mutex.WaitOne(45000)} catch [Threading.AbandonedMutexException] {$held=$true}
    if(-not $held){throw 'Performance host busy'}
    New-Item -ItemType Directory -Path $r -Force | Out-Null
    $env:TEMP=$r;$env:TMP=$r;$env:CARGO_HOME="$r\cargo-home";$env:CARGO_TARGET_DIR="$r\native\target"
    $rustbin='C:\Users\tedd\.rustup\toolchains\stable-x86_64-pc-windows-msvc\bin'
    $env:PATH="$rustbin;$env:PATH";$env:RUSTFLAGS='-C target-cpu=native'
    $env:RUSTC="$rustbin\rustc.exe";$env:RUSTC_WRAPPER='';$env:RUSTC_WORKSPACE_WRAPPER=''
    switch($Action) {
        'fetch' {
            foreach($source in @(@('static-aabb','https://github.com/jbuckmccready/static_aabb2d_index.git','a511a6327e14a0f0418cea01c401bf147e0e835c'),@('geo-index','https://github.com/georust/geo-index.git','e6efbb01d3c298e8963c8b7d1aab40c1bd540715'))) {
                if(Test-Path -LiteralPath "$r\$($source[0])"){throw 'Do not overwrite an existing source checkout'}
                & git init "$r\$($source[0])"
                & git -C "$r\$($source[0])" remote add origin $source[1]
                & git -C "$r\$($source[0])" fetch --depth 1 origin $source[2]
                if($LASTEXITCODE -ne 0){throw 'Pinned source fetch failed'}
                & git -C "$r\$($source[0])" checkout --detach FETCH_HEAD
                if($LASTEXITCODE -ne 0){throw 'Pinned checkout failed'}
            }
            New-Item -ItemType Directory -Path "$r\native\src" -Force | Out-Null
            Copy-Item -LiteralPath "$repository\benchmarks\mutable-packed\native\Cargo.toml" -Destination "$r\native\Cargo.toml"
            Copy-Item -LiteralPath "$repository\benchmarks\mutable-packed\native\Cargo.lock" -Destination "$r\native\Cargo.lock"
            Get-ChildItem -LiteralPath "$repository\benchmarks\mutable-packed\native\src" -Filter '*.rs' | Copy-Item -Destination "$r\native\src"
            & "$rustbin\cargo.exe" fetch --locked --manifest-path "$r\native\Cargo.toml"
        }
        'build' {
            $originalPath=$env:PATH
            $vcvars='C:\Program Files\Microsoft Visual Studio\18\Insiders\VC\Auxiliary\Build\vcvars64.bat'
            $environment=cmd /c "`"$vcvars`" >nul && set"
            foreach($line in $environment){if($line -match '^([^=]+)=(.*)$'){[Environment]::SetEnvironmentVariable($matches[1],$matches[2],'Process')}}
            $env:PATH="$env:PATH;$originalPath"
            $sdk='C:\Program Files (x86)\Windows Kits\10'
            $env:LIB="$env:LIB;$sdk\Lib\10.0.26100.0\ucrt\x64;$sdk\Lib\10.0.26100.0\um\x64"
            & "$rustbin\cargo.exe" build --offline --locked --release --target-dir "$r\native\target" --manifest-path "$r\native\Cargo.toml"
            if($LASTEXITCODE -ne 0){throw 'Native build failed'}
            & dotnet build "$repository\benchmarks\mutable-packed\Bench.csproj" -t:Rebuild -c Release --artifacts-path "$r\caller-artifacts" -o "$r\caller" -p:UseSharedCompilation=false "-p:LibraryPath=$r\..\baseline-library\Tedd.RTree.dll"
            if($LASTEXITCODE -ne 0){throw 'Cross-language caller build failed'}
            foreach($stage in @('control','candidate')) {
                New-Item -ItemType Directory -Path "$r\$stage-worker" -Force | Out-Null
                Get-ChildItem -LiteralPath "$r\caller" -File | Where-Object {$_.Name -notlike 'Tedd.RTree.*'} | Copy-Item -Destination "$r\$stage-worker"
                $library=if($stage -eq 'control'){'baseline'}else{'candidate'}
                Copy-Item -LiteralPath "$r\..\$library-library\Tedd.RTree.dll" -Destination "$r\$stage-worker\Tedd.RTree.dll"
            }
        }
        'measure' { & C:\Python314\python.exe "$PSScriptRoot\cross-run.py" $r "$repository\benchmarks\results\mutation-regressions\cross" confirmation }
    }
    if($LASTEXITCODE -ne 0){throw "$Action failed: $LASTEXITCODE"}
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}
