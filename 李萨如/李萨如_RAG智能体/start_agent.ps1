$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $ProjectDir ".venv"
$Python = Join-Path $VenvDir "Scripts\python.exe"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "未找到 uv。请先安装 uv：https://docs.astral.sh/uv/"
}

if (-not (Test-Path -LiteralPath $Python)) {
    uv venv --python 3.12 $VenvDir
}

uv pip install --python $Python -r (Join-Path $ProjectDir "requirements.txt")

$Manifest = Join-Path $ProjectDir "data\index\manifest.json"
if (-not (Test-Path -LiteralPath $Manifest)) {
    & $Python (Join-Path $ProjectDir "ingest.py")
}

& $Python -m streamlit run (Join-Path $ProjectDir "app.py")

