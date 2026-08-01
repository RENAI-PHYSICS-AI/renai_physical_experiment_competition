param(
    [switch]$SkipJulia,
    [switch]$SkipPython
)

$ErrorActionPreference = "Stop"
$PackagingDir = $PSScriptRoot
$AppDir = Split-Path -Parent $PackagingDir
$Python = Join-Path $AppDir ".venv\Scripts\python.exe"
$Secrets = Join-Path $AppDir ".streamlit\secrets.toml"
$EmbeddedSecret = Join-Path $PackagingDir "_embedded_secret.py"
$Spec = Join-Path $PackagingDir "lissajous.spec"
$Dist = Join-Path $PackagingDir "dist"
$Work = Join-Path $PackagingDir "build"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "找不到项目 Python 环境：$Python"
}
if (-not (Test-Path -LiteralPath $Secrets)) {
    throw "找不到本地密钥文件：$Secrets"
}

& $Python (Join-Path $PackagingDir "encode_secret.py") $Secrets $EmbeddedSecret

if (-not $SkipJulia) {
    & julia --startup-file=no (Join-Path $PackagingDir "build_julia_app.jl")
    if ($LASTEXITCODE -ne 0) { throw "Julia 应用构建失败。" }
}

if (-not (Test-Path -LiteralPath (Join-Path $PackagingDir "julia_app\bin\LissajousWebRuntime.exe"))) {
    throw "缺少 Julia 应用，请取消 -SkipJulia 后重新构建。"
}

$AsciiStage = Join-Path $env:LOCALAPPDATA "LissajousTutorBuild\julia_app"
New-Item -ItemType Directory -Force -Path $AsciiStage | Out-Null
& robocopy (Join-Path $PackagingDir "julia_app") $AsciiStage /E /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "Julia 应用暂存失败，robocopy=$LASTEXITCODE" }
$env:LISSAJOUS_JULIA_APP_SOURCE = $AsciiStage

if (-not $SkipPython) {
    $Uv = (Get-Command uv -ErrorAction Stop).Source
    & $Uv pip install --python $Python "pyinstaller>=6.10,<7"
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller 安装失败。" }
    & $Python -m PyInstaller --noconfirm --clean --distpath $Dist --workpath $Work $Spec
    if ($LASTEXITCODE -ne 0) { throw "Windows 应用构建失败。" }
}

$Iscc = @(
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1

if (-not $Iscc) {
    throw "未找到 Inno Setup 6，请先安装后重新执行本脚本。"
}

$SourceDir = Join-Path $Dist "李萨如图形实验智能助教"
$OutputDir = Join-Path $Dist "installer"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
& $Iscc "/DSourceDir=$SourceDir" "/DOutputDir=$OutputDir" (Join-Path $PackagingDir "installer.iss")
if ($LASTEXITCODE -ne 0) { throw "安装程序构建失败。" }

Get-ChildItem -LiteralPath $OutputDir -Filter "*.exe" | Select-Object FullName, Length
