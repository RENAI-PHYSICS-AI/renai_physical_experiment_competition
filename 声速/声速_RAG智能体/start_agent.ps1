$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $ProjectDir ".venv"
$Python = Join-Path $VenvDir "Scripts\python.exe"
$JuliaProject = Join-Path $ProjectDir "..\声速测量可视化实验说明\声速四种方法_Julia综合可视化方案\web"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "未找到 uv。请先安装 uv：https://docs.astral.sh/uv/"
}
if (-not (Get-Command julia -ErrorAction SilentlyContinue)) {
    throw "未找到 Julia。请安装 Julia 1.10 后重新运行。"
}

if (-not (Test-Path -LiteralPath $Python)) {
    uv venv --python 3.12 $VenvDir
}

uv pip install --python $Python -r (Join-Path $ProjectDir "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Python 依赖安装失败。" }

& julia --startup-file=no --project=$JuliaProject -e "using Pkg; Pkg.instantiate(); Pkg.precompile()"
if ($LASTEXITCODE -ne 0) { throw "Julia 可视化依赖安装失败。" }

$Manifest = Join-Path $ProjectDir "data\index\manifest.json"
if (-not (Test-Path -LiteralPath $Manifest)) {
    & $Python (Join-Path $ProjectDir "ingest.py")
}

& $Python -m streamlit run (Join-Path $ProjectDir "app.py") --server.port 8502
