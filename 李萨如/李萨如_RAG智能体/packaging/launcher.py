from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

from _embedded_secret import reveal_api_key


APP_NAME = "李萨如图形实验智能助教"
STREAMLIT_PORT = 8501
JULIA_PORT = 9384


def log_path() -> Path:
    directory = Path(os.getenv("LOCALAPPDATA", Path.home())) / "LissajousExperimentTutor" / "logs"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "launcher.log"


def write_log(message: str) -> None:
    with log_path().open("a", encoding="utf-8") as handle:
        handle.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")


def bundle_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def application_environment() -> dict[str, str]:
    root = bundle_root()
    environment = os.environ.copy()
    environment.update(
        {
            "LISSAJOUS_APP_DIR": str(root / "app"),
            "LISSAJOUS_JULIA_EXE": str(
                root / "julia_app" / "bin" / "LissajousWebRuntime.exe"
            ),
            "LISSAJOUS_JULIA_PROJECT_DIR": str(root / "julia_app"),
            "LISSAJOUS_WEB_HOST": "127.0.0.1",
            "LISSAJOUS_WEB_PORT": str(JULIA_PORT),
            "LISSAJOUS_LLM_API_KEY": reveal_api_key(),
            "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
        }
    )
    environment.pop("LISSAJOUS_JULIA_SCRIPT", None)
    environment.pop("JULIA_DEPOT_PATH", None)
    return environment


def port_is_open(port: int, timeout: float = 0.25) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def wait_for_app(process: subprocess.Popen, timeout: float = 90.0) -> bool:
    deadline = time.monotonic() + timeout
    health_url = f"http://127.0.0.1:{STREAMLIT_PORT}/_stcore/health"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(health_url, timeout=0.8) as response:
                if response.status == 200:
                    return True
        except OSError:
            pass
        time.sleep(0.35)
    return False


def show_error(message: str) -> None:
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, message, APP_NAME, 0x10)
    except Exception:
        pass


def run_streamlit_child() -> None:
    root = bundle_root()
    os.environ.update(application_environment())
    stream = log_path().open("a", encoding="utf-8", buffering=1)
    sys.stdout = stream
    sys.stderr = stream
    write_log(f"Starting Streamlit child from {root}")
    sys.argv = [
        "streamlit",
        "run",
        str(root / "app" / "app.py"),
        "--global.developmentMode=false",
        "--server.address=127.0.0.1",
        f"--server.port={STREAMLIT_PORT}",
        "--server.headless=true",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
        "--client.toolbarMode=viewer",
    ]
    from streamlit.web.cli import main

    try:
        raise SystemExit(main())
    except BaseException as error:
        write_log(f"Streamlit child failed: {error!r}")
        raise


def main() -> int:
    if "--streamlit-child" in sys.argv:
        run_streamlit_child()

    app_url = f"http://127.0.0.1:{STREAMLIT_PORT}"
    if port_is_open(STREAMLIT_PORT):
        write_log("Existing Streamlit service found; opening it.")
        webbrowser.open(app_url)
        return 0

    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen(
        [sys.executable, "--streamlit-child"],
        env=application_environment(),
        creationflags=creation_flags,
    )
    write_log(f"Started Streamlit child pid={process.pid}")
    if not wait_for_app(process):
        write_log(f"Streamlit readiness failed; exit={process.poll()}")
        show_error("应用启动失败。请重新启动，或联系维护人员检查安装文件。")
        return 1
    write_log("Streamlit service is ready.")
    webbrowser.open(app_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
