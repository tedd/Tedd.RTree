$ErrorActionPreference='Stop'
$r='D:\Workspaces\AI\rtree-mutation-regressions'
if(Test-Path -LiteralPath $r){throw 'Use a fresh task workspace; do not overwrite retained work'}
New-Item -ItemType Directory -Path $r | Out-Null
$repository=[IO.Path]::GetFullPath("$PSScriptRoot\..\..")
foreach($entry in @(@('old','3d2d88f'),@('baseline','79a5dd2'),@('metrics','9a61db5'))) {
    $stage=$entry[0];$revision=$entry[1]
    & git -C $repository archive --format=zip "--output=$r\$stage.zip" $revision src/Tedd.RTree
    if($LASTEXITCODE -ne 0){throw 'Source extraction failed'}
    Expand-Archive -LiteralPath "$r\$stage.zip" -DestinationPath "$r\$stage-source"
}
