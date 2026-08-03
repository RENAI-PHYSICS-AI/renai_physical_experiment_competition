from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from _embedded_secret import reveal_api_key


APP_NAME = "李萨如图形实验智能助教"
DEFAULT_STREAMLIT_PORT = 8501
DEFAULT_JULIA_PORT = 9384


class HeartbeatState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.started_at = time.monotonic()
        self.last_seen: float | None = None
        self.closed_at: float | None = None

    def heartbeat(self) -> None:
        with self.lock:
            self.last_seen = time.monotonic()
            self.closed_at = None

    def closed(self) -> None:
        with self.lock:
            self.closed_at = time.monotonic()

    def snapshot(self) -> tuple[float | None, float | None]:
        with self.lock:
            return self.last_seen, self.closed_at


def heartbeat_handler(state: HeartbeatState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def send_ok(self) -> None:
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        def do_OPTIONS(self) -> None:
            self.send_ok()

        def do_GET(self) -> None:
            if self.path.startswith("/heartbeat"):
                state.heartbeat()
            self.send_ok()

        def do_POST(self) -> None:
            if self.path.startswith("/closed"):
                state.closed()
            elif self.path.startswith("/client-log"):
                length = min(int(self.headers.get("Content-Length", "0") or "0"), 65536)
                payload = self.rfile.read(length).decode("utf-8", errors="replace")
                write_browser_log(payload)
            self.send_ok()

        def log_message(self, _format: str, *_args: object) -> None:
            return

    return Handler


def start_heartbeat_server() -> tuple[ThreadingHTTPServer, HeartbeatState, str]:
    state = HeartbeatState()
    server = ThreadingHTTPServer(("127.0.0.1", 0), heartbeat_handler(state))
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, name="browser-heartbeat", daemon=True)
    thread.start()
    port = server.server_address[1]
    return server, state, f"http://127.0.0.1:{port}/heartbeat"


def log_path() -> Path:
    return log_dir() / "launcher.log"


def log_dir() -> Path:
    directory = Path(os.getenv("LOCALAPPDATA", Path.home())) / "LissajousExperimentTutor" / "logs"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def write_log(message: str) -> None:
    with log_path().open("a", encoding="utf-8") as handle:
        handle.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")


def write_browser_log(message: str) -> None:
    with (log_dir() / "browser_diagnostics.log").open("a", encoding="utf-8") as handle:
        handle.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")


def bundle_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "").strip() or default)
    except ValueError:
        return default


def find_available_port(preferred: int) -> int:
    for candidate in (preferred, 0):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.bind(("127.0.0.1", candidate))
                return int(probe.getsockname()[1])
        except OSError:
            continue
    raise RuntimeError("No local TCP port is available.")


def application_environment(
    heartbeat_url: str | None = None,
    streamlit_port: int | None = None,
    julia_port: int | None = None,
) -> dict[str, str]:
    root = bundle_root()
    streamlit_port = streamlit_port or env_int("LISSAJOUS_STREAMLIT_PORT", DEFAULT_STREAMLIT_PORT)
    julia_port = julia_port or env_int("LISSAJOUS_WEB_PORT", DEFAULT_JULIA_PORT)
    environment = os.environ.copy()
    environment.update(
        {
            "LISSAJOUS_APP_DIR": str(root / "app"),
            "LISSAJOUS_JULIA_EXE": str(
                root / "julia_app" / "bin" / "LissajousWebRuntime.exe"
            ),
            "LISSAJOUS_JULIA_PROJECT_DIR": str(root / "julia_app"),
            "LISSAJOUS_WEB_HOST": "127.0.0.1",
            "LISSAJOUS_WEB_BROWSER_HOST": "127.0.0.1",
            "LISSAJOUS_WEB_PORT": str(julia_port),
            "LISSAJOUS_STREAMLIT_PORT": str(streamlit_port),
            "LISSAJOUS_LOG_DIR": str(log_dir()),
            "LISSAJOUS_LLM_API_KEY": reveal_api_key(),
            "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
        }
    )
    if heartbeat_url:
        environment["LISSAJOUS_HEARTBEAT_URL"] = heartbeat_url
    environment.pop("LISSAJOUS_JULIA_SCRIPT", None)
    environment.pop("JULIA_DEPOT_PATH", None)
    return environment


def port_is_open(port: int, timeout: float = 0.25) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def wait_for_app(process: subprocess.Popen, port: int, timeout: float = 90.0) -> bool:
    deadline = time.monotonic() + timeout
    health_url = f"http://127.0.0.1:{port}/_stcore/health"
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


def terminate_process_tree(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    write_log(f"Stopping application process tree at pid={process.pid}.")
    if os.name == "nt":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
            check=False,
        )
    else:
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


def streamlit_browser_connected(port: int) -> bool:
    if os.name != "nt":
        return False
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    result = subprocess.run(
        ["netstat", "-ano", "-p", "tcp"],
        capture_output=True,
        text=True,
        errors="replace",
        creationflags=flags,
        check=False,
    )
    suffix = f":{port}"
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) < 4 or fields[0].upper() != "TCP":
            continue
        local_endpoint, state = fields[1], fields[3].upper()
        if local_endpoint.endswith(suffix) and state == "ESTABLISHED":
            return True
    return False


def monitor_browser(process: subprocess.Popen, state: HeartbeatState, port: int) -> str:
    connection_seen = False
    disconnected_at: float | None = None
    while process.poll() is None:
        now = time.monotonic()
        last_seen, closed_at = state.snapshot()
        connected = streamlit_browser_connected(port)
        if connected:
            connection_seen = True
            disconnected_at = None
        elif connection_seen:
            disconnected_at = disconnected_at or now
            if now - disconnected_at >= 8.0:
                return "browser connection closed"
        if closed_at is not None and (last_seen is None or last_seen <= closed_at):
            if now - closed_at >= 8.0:
                return "browser page closed"
        if last_seen is not None and now - last_seen >= 180.0:
            return "browser heartbeat expired"
        if last_seen is None and now - state.started_at >= 180.0:
            return "browser never connected"
        time.sleep(0.5)
    return f"Streamlit exited with code {process.returncode}"


def run_streamlit_child() -> None:
    root = bundle_root()
    streamlit_port = env_int("LISSAJOUS_STREAMLIT_PORT", DEFAULT_STREAMLIT_PORT)
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
        f"--server.port={streamlit_port}",
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


def browser_candidates() -> list[Path]:
    paths: list[Path] = []
    for env_name in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        base = os.getenv(env_name)
        if not base:
            continue
        root = Path(base)
        paths.extend(
            [
                root / "Microsoft" / "Edge" / "Application" / "msedge.exe",
                root / "Google" / "Chrome" / "Application" / "chrome.exe",
            ]
        )
    return [path for path in paths if path.exists()]


def open_browser(url: str) -> None:
    browser = next(iter(browser_candidates()), None)
    if browser is None:
        write_log("No Edge/Chrome executable found; opening default browser.")
        webbrowser.open(url)
        return
    arguments = [
        str(browser),
        "--new-window",
        "--ignore-gpu-blocklist",
        "--enable-webgl",
        "--enable-webgl2",
        "--enable-unsafe-swiftshader",
        url,
    ]
    write_log(
        "Opening browser: "
        f"{browser}; flags=--ignore-gpu-blocklist --enable-webgl --enable-webgl2 --enable-unsafe-swiftshader"
    )
    subprocess.Popen(
        arguments,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def main() -> int:
    if "--streamlit-child" in sys.argv:
        run_streamlit_child()

    streamlit_port = find_available_port(DEFAULT_STREAMLIT_PORT)
    julia_port = find_available_port(DEFAULT_JULIA_PORT)
    app_url = f"http://127.0.0.1:{streamlit_port}"
    write_log(
        "Launcher environment: "
        f"bundle_root={bundle_root()}; log_dir={log_dir()}; "
        f"python_exe={sys.executable}; streamlit_port={streamlit_port}; julia_port={julia_port}"
    )

    heartbeat_server, heartbeat_state, heartbeat_url = start_heartbeat_server()
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen(
        [sys.executable, "--streamlit-child"],
        env=application_environment(heartbeat_url, streamlit_port, julia_port),
        creationflags=creation_flags,
    )
    write_log(
        "Started Streamlit child "
        f"pid={process.pid}; streamlit_port={streamlit_port}; "
        f"julia_port={julia_port}; heartbeat={heartbeat_url}"
    )
    try:
        if not wait_for_app(process, streamlit_port):
            write_log(f"Streamlit readiness failed; exit={process.poll()}")
            show_error("应用启动失败。请重新启动，或联系维护人员检查安装文件。")
            return 1
        write_log("Streamlit service is ready; opening browser.")
        open_browser(app_url)
        reason = monitor_browser(process, heartbeat_state, streamlit_port)
        write_log(f"Application supervisor stopping: {reason}.")
        return 0
    finally:
        heartbeat_server.shutdown()
        heartbeat_server.server_close()
        terminate_process_tree(process)
        write_log("Application process tree stopped.")


if __name__ == "__main__":
    raise SystemExit(main())
