param(
    [switch]$SkipJulia,
    [string]$JuliaAppSource = ""
)

$ErrorActionPreference = "Stop"
$PackagingDir = $PSScriptRoot
$AppDir = Split-Path -Parent $PackagingDir
$Python = Join-Path $AppDir ".venv\Scripts\python.exe"
$Secrets = Join-Path $AppDir ".streamlit\secrets.toml"
$EmbeddedSecret = Join-Path $PackagingDir "_embedded_secret.py"
$Spec = Join-Path $PackagingDir "lissajous_onefile.spec"
$Dist = Join-Path $PackagingDir "dist"
$DefaultJuliaStage = Join-Path $env:LOCALAPPDATA "LissajousTutorBuild\julia_app"
$DefaultJuliaBuild = Join-Path $env:LOCALAPPDATA "LissajousTutorBuild\julia_build"
$AsciiStage = if ($JuliaAppSource) {
    (Resolve-Path -LiteralPath $JuliaAppSource -ErrorAction Stop).Path
} else {
    $DefaultJuliaStage
}
$BuildStamp = Get-Date -Format "yyyyMMdd_HHmmss"
$ShortBuildRoot = Join-Path $env:SystemDrive "LT\LissajousOnefile_$BuildStamp"
$PythonDist = Join-Path $ShortBuildRoot "dist"
$PythonWork = Join-Path $ShortBuildRoot "work"
$OutputDir = Join-Path $Dist "single"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "找不到项目 Python 环境：$Python"
}
if (-not (Test-Path -LiteralPath $Secrets)) {
    throw "找不到本地密钥文件：$Secrets"
}

& $Python (Join-Path $PackagingDir "encode_secret.py") $Secrets $EmbeddedSecret

if (-not $SkipJulia) {
    if ($JuliaAppSource) {
        throw "指定 -JuliaAppSource 时请同时使用 -SkipJulia。"
    }
    $env:LISSAJOUS_JULIA_OUTPUT_DIR = $AsciiStage
    $env:LISSAJOUS_JULIA_BUILD_DIR = $DefaultJuliaBuild
    & julia --startup-file=no (Join-Path $PackagingDir "build_julia_app.jl")
    if ($LASTEXITCODE -ne 0) { throw "Julia 应用构建失败。" }
}

if (-not (Test-Path -LiteralPath (Join-Path $AsciiStage "bin\LissajousWebRuntime.exe"))) {
    throw "缺少 Julia 应用，请取消 -SkipJulia 后重新构建。"
}

New-Item -ItemType Directory -Force -Path $ShortBuildRoot | Out-Null
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$env:LISSAJOUS_JULIA_APP_SOURCE = $AsciiStage
$Uv = (Get-Command uv -ErrorAction Stop).Source
& $Uv pip install --python $Python "pyinstaller>=6.10,<7"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller 安装失败。" }

& $Python -m PyInstaller --noconfirm --clean --distpath $PythonDist --workpath $PythonWork $Spec
if ($LASTEXITCODE -ne 0) { throw "单文件应用构建失败。" }

$BuiltExe = Get-ChildItem -LiteralPath $PythonDist -Filter "*单文件版*.exe" | Select-Object -First 1
if (-not $BuiltExe) {
    throw "未找到单文件 exe 输出。"
}

$Target = Join-Path $OutputDir $BuiltExe.Name
Copy-Item -LiteralPath $BuiltExe.FullName -Destination $Target -Force
Get-Item -LiteralPath $Target | Select-Object FullName, Length, LastWriteTime
