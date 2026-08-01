$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectDir ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "环境尚未创建，请先运行 start_agent.ps1。"
}

& $Python (Join-Path $ProjectDir "ingest.py") @args

