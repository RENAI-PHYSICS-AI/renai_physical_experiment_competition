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
$AsciiStage = Join-Path $env:LOCALAPPDATA "LissajousTutorBuild\julia_app"
$BuildStamp = Get-Date -Format "yyyyMMdd_HHmmss"
$ShortBuildRoot = Join-Path $env:SystemDrive "LT\LissajousBuild_$BuildStamp"
$PythonDist = Join-Path $ShortBuildRoot "dist"
$PythonWork = Join-Path $ShortBuildRoot "work"
$InstallerStage = Join-Path $ShortBuildRoot "installer"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "找不到项目 Python 环境：$Python"
}
if (-not (Test-Path -LiteralPath $Secrets)) {
    throw "找不到本地密钥文件：$Secrets"
}

& $Python (Join-Path $PackagingDir "encode_secret.py") $Secrets $EmbeddedSecret

if (-not $SkipJulia) {
    $env:LISSAJOUS_JULIA_OUTPUT_DIR = $AsciiStage
    & julia --startup-file=no (Join-Path $PackagingDir "build_julia_app.jl")
    if ($LASTEXITCODE -ne 0) { throw "Julia 应用构建失败。" }
}

if (-not (Test-Path -LiteralPath (Join-Path $AsciiStage "bin\LissajousWebRuntime.exe"))) {
    throw "缺少 Julia 应用，请取消 -SkipJulia 后重新构建。"
}

$env:LISSAJOUS_JULIA_APP_SOURCE = $AsciiStage

if (-not $SkipPython) {
    New-Item -ItemType Directory -Force -Path $ShortBuildRoot | Out-Null
    $Uv = (Get-Command uv -ErrorAction Stop).Source
    & $Uv pip install --python $Python "pyinstaller>=6.10,<7"
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller 安装失败。" }
    & $Python -m PyInstaller --noconfirm --clean --distpath $PythonDist --workpath $PythonWork $Spec
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

$SourceDir = if ($SkipPython) {
    $env:LISSAJOUS_PYINSTALLER_SOURCE
} else {
    Join-Path $PythonDist "LissajousExperimentTutor"
}
if (-not $SourceDir -or -not (Test-Path -LiteralPath $SourceDir)) {
    throw "缺少 PyInstaller 便携目录；使用 -SkipPython 时请设置 LISSAJOUS_PYINSTALLER_SOURCE。"
}

New-Item -ItemType Directory -Force -Path $InstallerStage | Out-Null
& $Iscc "/DSourceDir=$SourceDir" "/DOutputDir=$InstallerStage" (Join-Path $PackagingDir "installer.iss")
if ($LASTEXITCODE -ne 0) { throw "安装程序构建失败。" }

$OutputDir = Join-Path $Dist "installer"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$BuiltInstallers = Get-ChildItem -LiteralPath $InstallerStage -Filter "*.exe"
$BuiltInstallers | Copy-Item -Destination $OutputDir -Force
Get-ChildItem -LiteralPath $OutputDir -Filter "*.exe" | Select-Object FullName, Length
