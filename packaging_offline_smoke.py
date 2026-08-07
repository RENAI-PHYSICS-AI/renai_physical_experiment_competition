from __future__ import annotations

import importlib
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.request
from pathlib import Path


report_path = Path(os.environ["TUTOR_SMOKE_REPORT"])


def report_unhandled(error_type, error, error_traceback) -> None:
    report_path.write_text(
        "OFFLINE_SMOKE_FAILED\n"
        + "".join(traceback.format_exception(error_type, error, error_traceback)),
        encoding="utf-8",
    )


sys.excepthook = report_unhandled


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


kind = os.environ["TUTOR_SMOKE_KIND"]
root = Path(getattr(sys, "_MEIPASS", ""))
require(root.is_dir(), "PyInstaller extraction root is unavailable")
app_dir = root / "app"
require((app_dir / "app.py").is_file(), "embedded Streamlit app is missing")
require((app_dir / "data" / "index" / "manifest.json").is_file(), "embedded index is missing")
require((app_dir / "prompts" / "system.md").is_file(), "embedded prompt is missing")
prefix = "LISSAJOUS" if kind == "lissajous" else "SOUND_SPEED"
from _embedded_secret import reveal_api_key

embedded_api_key = reveal_api_key()
require(bool(embedded_api_key), "embedded model credential is missing")
os.environ[f"{prefix}_APP_DIR"] = str(app_dir)
os.environ[f"{prefix}_LLM_API_KEY"] = embedded_api_key
sys.path.insert(0, str(app_dir))

for module_name in (
    "streamlit",
    "numpy",
    "scipy",
    "sklearn",
    "matplotlib",
    "PIL",
    "joblib",
    "ddgs",
    "agent",
    "code_runner",
    "config",
    "experiment_embed",
    "retrieval",
    "tools",
    "web_search",
):
    importlib.import_module(module_name)

from code_runner import run_python_block
from retrieval import HybridRetriever

query = "频率比与相位差" if kind == "lissajous" else "回声法测量声速"
hits = HybridRetriever().search(query, top_k=3)
require(bool(hits), "embedded knowledge index returned no results")

with tempfile.TemporaryDirectory(prefix=f"{kind}_python_smoke_") as output_dir:
    result = run_python_block(
        "import matplotlib.pyplot as plt\n"
        "plt.plot([0, 1, 2], [0, 1, 0])\n"
        "plt.savefig('offline_smoke.png')\n"
        "print('PYTHON_RUNNER_OK')",
        output_dir,
        timeout=180,
    )
    require(not result["blocked"], f"embedded Python runner was blocked: {result}")
    require(result["returncode"] == 0, f"embedded Python runner failed: {result}")
    require(result["visuals"], "embedded Python runner produced no plot")

if kind == "lissajous":
    julia_name = "LissajousWebRuntime.exe"
    routes = ("/", "/phase", "/amplitude", "/ratio", "/detune")
else:
    julia_name = "SoundSpeedWebRuntime.exe"
    routes = ("/",)

julia_exe = root / "julia_app" / "bin" / julia_name
require(julia_exe.is_file(), f"embedded Julia executable is missing: {julia_exe}")

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
    probe.bind(("127.0.0.1", 0))
    port = int(probe.getsockname()[1])

with tempfile.TemporaryDirectory(prefix=f"{kind}_julia_depot_") as empty_depot:
    environment = os.environ.copy()
    environment["JULIA_DEPOT_PATH"] = empty_depot
    environment[f"{prefix}_WEB_HOST"] = "127.0.0.1"
    environment[f"{prefix}_WEB_BROWSER_HOST"] = "127.0.0.1"
    environment[f"{prefix}_WEB_PORT"] = str(port)
    process = subprocess.Popen(
        [str(julia_exe)],
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"embedded Julia exited early with {process.returncode}")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                    break
            except OSError:
                time.sleep(0.5)
        else:
            raise RuntimeError("embedded Julia server did not start")

        assets: set[str] = set()
        for route in routes:
            url = f"http://127.0.0.1:{port}{route}"
            with urllib.request.urlopen(url, timeout=90) as response:
                body = response.read().decode("utf-8", errors="replace")
                require(response.status == 200, f"route failed: {url}")
                require("Bonito" in body or "李萨如" in body or "声速" in body, f"unexpected route body: {url}")
                assets.update(re.findall(rf"http://127\.0\.0\.1:{port}/assets/[^'\"\)]+", body))
        require(bool(assets), "Julia pages exposed no bundled assets")
        for asset_url in sorted(assets):
            with urllib.request.urlopen(asset_url, timeout=90) as response:
                payload = response.read()
                require(response.status == 200 and payload, f"asset failed: {asset_url}")

        import config
        import tools
        from streamlit.testing.v1 import AppTest

        os.environ[f"{prefix}_WEB_HOST"] = "127.0.0.1"
        os.environ[f"{prefix}_WEB_BROWSER_HOST"] = "127.0.0.1"
        os.environ[f"{prefix}_WEB_PORT"] = str(port)
        config.JULIA_WEB_URL = f"http://127.0.0.1:{port}"
        tools.JULIA_WEB_HOST = "127.0.0.1"
        tools.JULIA_WEB_PORT = port
        app_test = AppTest.from_file(str(app_dir / "app.py"), default_timeout=180)
        app_test.run()
        require(not app_test.exception, f"embedded Streamlit app raised: {app_test.exception}")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)

summary = (
    f"OFFLINE_SMOKE_OK kind={kind} modules=16 retrieval={len(hits)} "
    f"credential=present python_runner=ok streamlit_app=ok "
    f"julia_routes={len(routes)} assets={len(assets)}"
)
report_path.write_text(summary + "\n", encoding="utf-8")
print(summary)
