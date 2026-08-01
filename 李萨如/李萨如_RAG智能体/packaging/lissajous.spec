import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata


packaging_dir = Path(SPEC).resolve().parent
app_dir = packaging_dir.parent
julia_app = Path(os.environ.get("LISSAJOUS_JULIA_APP_SOURCE", packaging_dir / "julia_app"))

datas = [
    (str(app_dir / "app.py"), "app"),
    (str(app_dir / "assets"), "app/assets"),
    (str(app_dir / "data"), "app/data"),
    (str(app_dir / "prompts"), "app/prompts"),
    (str(julia_app), "julia_app"),
]
datas += collect_data_files("streamlit")
for distribution in ("streamlit", "scikit-learn", "scipy", "numpy", "ddgs", "joblib"):
    datas += copy_metadata(distribution)

hiddenimports = collect_submodules("streamlit") + [
    "agent",
    "config",
    "retrieval",
    "tools",
    "web_search",
    "ddgs",
    "joblib",
    "numpy",
    "scipy.sparse",
    "sklearn.feature_extraction.text",
]

a = Analysis(
    [str(packaging_dir / "launcher.py")],
    pathex=[str(app_dir), str(packaging_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "notebook",
        "IPython",
        "pytest",
        "sentence_transformers",
        "torch",
        "tensorflow",
    ],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="李萨如图形实验智能助教",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="李萨如图形实验智能助教",
)
