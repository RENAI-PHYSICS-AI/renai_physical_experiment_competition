$ErrorActionPreference = "Stop"
$PackagingDir = $PSScriptRoot
$RuntimeDir = Join-Path $PackagingDir "julia_runtime"
$DepotDir = Join-Path $PackagingDir "julia_depot"
$ProjectDir = Join-Path $PackagingDir "julia_project"
$WebSource = Join-Path $PackagingDir "..\..\李萨如图形可视化实验说明\实验一至四_Julia综合可视化方案\web.jl"
$JuliaCommand = (Get-Command julia -ErrorAction Stop).Source
$JuliaBin = (& julia --startup-file=no -e "print(Sys.BINDIR)")
$JuliaRoot = Split-Path -Parent $JuliaBin

if (-not (Test-Path -LiteralPath $WebSource)) {
    throw "找不到网页实验源文件：$WebSource"
}

New-Item -ItemType Directory -Force -Path $RuntimeDir, $DepotDir, $ProjectDir | Out-Null
Copy-Item -LiteralPath (Join-Path $PackagingDir "julia_runtime_project.toml") -Destination (Join-Path $ProjectDir "Project.toml") -Force
Copy-Item -LiteralPath $WebSource -Destination (Join-Path $ProjectDir "web.jl") -Force

$PreviousDepot = $env:JULIA_DEPOT_PATH
try {
    $env:JULIA_DEPOT_PATH = $DepotDir
    & $JuliaCommand --startup-file=no --project=$ProjectDir -e "using Pkg; Pkg.instantiate(); Pkg.precompile(); using Bonito, WGLMakie"
    if ($LASTEXITCODE -ne 0) { throw "Julia 专用包环境构建失败。" }
}
finally {
    $env:JULIA_DEPOT_PATH = $PreviousDepot
}

& robocopy $JuliaRoot $RuntimeDir /E /NFL /NDL /NJH /NJS /NP /XD "doc" "include" | Out-Null
if ($LASTEXITCODE -ge 8) { throw "复制 Julia 运行时失败，robocopy=$LASTEXITCODE" }

foreach ($name in @("registries", "logs", "clones", "downloads")) {
    $candidate = Join-Path $DepotDir $name
    if (Test-Path -LiteralPath $candidate) {
        Remove-Item -LiteralPath $candidate -Recurse -Force
    }
}

Write-Output "Julia portable runtime ready."
