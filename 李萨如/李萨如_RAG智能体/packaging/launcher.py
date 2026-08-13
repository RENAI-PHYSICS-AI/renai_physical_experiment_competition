from __future__ import annotations

import os
import runpy
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import uuid
import webbrowser
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from _embedded_secret import reveal_api_key


APP_NAME = "李萨如图形实验智能助教"
DEFAULT_STREAMLIT_PORT = 8501
DEFAULT_JULIA_PORT = 9384
BROWSER_PROFILE_PREFIX = "lissajous_tutor_browser_"
FIRST_CLIENT_GRACE = 180.0
CLOSE_GRACE = 20.0
CLIENT_LEASE = 120.0
MANAGED_BROWSER_STARTUP_GRACE = 30.0
JOB_NAME_ENV = "LISSAJOUS_JOB_NAME"
JOB_ACK_ENV = "LISSAJOUS_JOB_ACK"


class BrowserSession:
    def __init__(
        self,
        process: subprocess.Popen | None = None,
        profile_dir: Path | None = None,
    ) -> None:
        self.process = process
        self.profile_dir = profile_dir

    @property
    def managed(self) -> bool:
        return self.process is not None


class HeartbeatState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.started_at = time.monotonic()
        self.armed_at = self.started_at
        self.clients: dict[str, tuple[int, float, float | None]] = {}

    def arm(self) -> None:
        with self.lock:
            self.armed_at = time.monotonic()

    def heartbeat(self, client_id: str, sequence: int) -> None:
        with self.lock:
            current = self.clients.get(client_id)
            if current is not None and sequence <= current[0]:
                return
            self.clients[client_id] = (sequence, time.monotonic(), None)

    def closed(self, client_id: str, sequence: int) -> None:
        with self.lock:
            current = self.clients.get(client_id)
            if current is not None and sequence <= current[0]:
                return
            last_seen = current[1] if current is not None else time.monotonic()
            self.clients[client_id] = (sequence, last_seen, time.monotonic())

    def snapshot(self) -> tuple[float, dict[str, tuple[int, float, float | None]]]:
        with self.lock:
            return self.armed_at, dict(self.clients)

    @staticmethod
    def client_event(path: str) -> tuple[str, int] | None:
        query = parse_qs(urlsplit(path).query)
        client_id = (query.get("client") or [""])[0]
        try:
            sequence = int((query.get("seq") or [""])[0])
        except ValueError:
            return None
        if not client_id or len(client_id) > 128 or sequence < 0:
            return None
        return client_id, sequence


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
                event = state.client_event(self.path)
                if event is not None:
                    state.heartbeat(*event)
            self.send_ok()

        def do_POST(self) -> None:
            if self.path.startswith("/closed"):
                event = state.client_event(self.path)
                if event is not None:
                    state.closed(*event)
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


def safe_write_log(message: str) -> None:
    try:
        write_log(message)
    except Exception:
        pass


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
            "LISSAJOUS_CODE_OUTPUT_DIR": str(log_dir().parent / "runtime_outputs"),
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


@contextmanager
def external_windows_dll_search_path():
    """Prevent PyInstaller's private DLL path leaking into system programs."""
    if os.name != "nt" or not getattr(sys, "frozen", False):
        yield
        return
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetDllDirectoryW.argtypes = [wintypes.DWORD, wintypes.LPWSTR]
    kernel32.GetDllDirectoryW.restype = wintypes.DWORD
    kernel32.SetDllDirectoryW.argtypes = [wintypes.LPCWSTR]
    kernel32.SetDllDirectoryW.restype = wintypes.BOOL
    buffer = ctypes.create_unicode_buffer(32768)
    length = kernel32.GetDllDirectoryW(len(buffer), buffer)
    previous = buffer.value if 0 < length < len(buffer) else None
    changed = bool(kernel32.SetDllDirectoryW(None))
    try:
        yield
    finally:
        if changed:
            kernel32.SetDllDirectoryW(previous)


def external_process_environment() -> dict[str, str]:
    """Remove PyInstaller-only variables before starting system executables."""
    environment = os.environ.copy()
    for name in tuple(environment):
        if name.startswith("_PYI_"):
            environment.pop(name, None)
    environment.pop("_MEIPASS2", None)
    mei_value = str(getattr(sys, "_MEIPASS", "")).strip()
    if mei_value and environment.get("PATH"):
        try:
            mei_path = Path(mei_value).resolve()
            environment["PATH"] = os.pathsep.join(
                item
                for item in environment["PATH"].split(os.pathsep)
                if item
                and (
                    not Path(item).exists()
                    or Path(item).resolve() != mei_path
                )
            )
        except OSError:
            pass
    return environment


def streamlit_child_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--streamlit-child"]
    interpreter = str(getattr(sys, "_base_executable", sys.executable))
    return [interpreter, str(Path(__file__).resolve()), "--streamlit-child"]


def terminate_process_tree(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    write_log(f"Stopping application process tree at pid={process.pid}.")
    if os.name == "nt":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            with external_windows_dll_search_path():
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=flags,
                    check=False,
                    timeout=10,
                    env=external_process_environment(),
                )
        except (OSError, subprocess.TimeoutExpired) as exc:
            write_log(f"taskkill fallback failed for pid={process.pid}: {exc}")
    else:
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


def create_kill_on_close_job(job_name: str | None = None) -> int | None:
    """Create a Windows job whose child tree dies with the launcher."""
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class BasicLimitInformation(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class IoCounters(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_uint64),
                ("WriteOperationCount", ctypes.c_uint64),
                ("OtherOperationCount", ctypes.c_uint64),
                ("ReadTransferCount", ctypes.c_uint64),
                ("WriteTransferCount", ctypes.c_uint64),
                ("OtherTransferCount", ctypes.c_uint64),
            ]

        class ExtendedLimitInformation(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", BasicLimitInformation),
                ("IoInfo", IoCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
        kernel32.CreateJobObjectW.restype = ctypes.c_void_p
        kernel32.SetInformationJobObject.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle.restype = wintypes.BOOL

        handle = kernel32.CreateJobObjectW(None, job_name)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        info = ExtendedLimitInformation()
        info.BasicLimitInformation.LimitFlags = 0x00002000  # KILL_ON_JOB_CLOSE
        if not kernel32.SetInformationJobObject(
            handle, 9, ctypes.byref(info), ctypes.sizeof(info)
        ):
            error = ctypes.get_last_error()
            kernel32.CloseHandle(handle)
            raise ctypes.WinError(error)
        return int(handle)
    except Exception as exc:
        write_log(f"Windows process job unavailable; using taskkill fallback: {exc}")
        return None


def attach_current_process_to_named_job() -> bool:
    """Attach the Streamlit child before it can launch Julia or code runners."""
    job_name = os.getenv(JOB_NAME_ENV, "").strip()
    ack_value = os.getenv(JOB_ACK_ENV, "").strip()
    if not job_name:
        return True
    ack_path = Path(ack_value) if ack_value else None
    result = "error: unknown failure"
    handle: int | None = None
    attached = False
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenJobObjectW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.OpenJobObjectW.restype = ctypes.c_void_p
        kernel32.GetCurrentProcess.argtypes = []
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        kernel32.AssignProcessToJobObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.OpenJobObjectW(0x0001, False, job_name)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        if not kernel32.AssignProcessToJobObject(handle, kernel32.GetCurrentProcess()):
            raise ctypes.WinError(ctypes.get_last_error())
        if not kernel32.CloseHandle(handle):
            raise ctypes.WinError(ctypes.get_last_error())
        handle = None
        attached = True
        result = f"ok:{os.getpid()}"
        write_log(f"Streamlit child joined Windows job before startup; pid={os.getpid()}.")
    except Exception as exc:
        result = f"error:{exc}"
        safe_write_log(f"Unable to attach Streamlit child to Windows job: {exc}")
    finally:
        if handle is not None:
            try:
                import ctypes

                ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle(handle)
            except Exception:
                pass
        if ack_path is not None:
            try:
                temporary_ack = ack_path.with_name(
                    f".{ack_path.name}.{os.getpid()}.tmp"
                )
                temporary_ack.write_text(result, encoding="utf-8")
                os.replace(temporary_ack, ack_path)
            except OSError as exc:
                safe_write_log(f"Unable to write process-job acknowledgement: {exc}")
    return attached


def wait_for_job_attachment(
    process: subprocess.Popen,
    ack_path: Path | None,
    timeout: float = 15.0,
) -> bool:
    if ack_path is None:
        return True
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if ack_path.exists():
                result = ack_path.read_text(encoding="utf-8", errors="replace").strip()
                if result == f"ok:{process.pid}":
                    safe_write_log(f"Confirmed Streamlit child job attachment ({result}).")
                    return True
                safe_write_log(f"Streamlit child job attachment failed ({result}).")
                return False
        except OSError:
            pass
        if process.poll() is not None:
            safe_write_log(
                f"Streamlit child exited before process-job acknowledgement; exit={process.returncode}."
            )
            return False
        time.sleep(0.05)
    safe_write_log("Timed out waiting for Streamlit child process-job acknowledgement.")
    return False


def terminate_process_job(job_handle: int | None) -> None:
    if job_handle is None or os.name != "nt":
        return
    kernel32 = None
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.TerminateJobObject.argtypes = [ctypes.c_void_p, wintypes.UINT]
        kernel32.TerminateJobObject.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle.restype = wintypes.BOOL
        if not kernel32.TerminateJobObject(job_handle, 0):
            write_log(f"TerminateJobObject failed with error={ctypes.get_last_error()}.")
    except Exception as exc:
        safe_write_log(f"Unable to terminate Windows process job: {exc}")
    finally:
        if kernel32 is not None:
            try:
                kernel32.CloseHandle(job_handle)
            except Exception as exc:
                safe_write_log(f"Unable to close Windows process job handle: {exc}")


def streamlit_browser_connected(port: int) -> bool:
    if os.name != "nt":
        return False
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        with external_windows_dll_search_path():
            result = subprocess.run(
                ["netstat", "-ano", "-p", "tcp"],
                capture_output=True,
                text=True,
                errors="replace",
                creationflags=flags,
                check=False,
                timeout=5,
                env=external_process_environment(),
            )
    except (OSError, subprocess.TimeoutExpired):
        return False
    suffix = f":{port}"
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) < 4 or fields[0].upper() != "TCP":
            continue
        local_endpoint, state = fields[1], fields[3].upper()
        if local_endpoint.endswith(suffix) and state == "ESTABLISHED":
            return True
    return False


def monitor_browser(
    process: subprocess.Popen,
    state: HeartbeatState,
    port: int,
    browser_session: BrowserSession | None = None,
) -> str:
    no_live_clients_at: float | None = None
    browser_exited_at: float | None = None
    browser_ever_connected = False
    all_known_clients_closed_at: float | None = None
    while process.poll() is None:
        now = time.monotonic()
        armed_at, clients = state.snapshot()
        connected = streamlit_browser_connected(port)
        live_clients = [
            client
            for client in clients.values()
            if client[2] is None and now - client[1] < CLIENT_LEASE
        ]
        known_client = bool(clients)
        all_known_clients_closed = known_client and all(
            client[2] is not None for client in clients.values()
        )
        browser_ever_connected = browser_ever_connected or known_client or connected
        if browser_session is not None and browser_session.managed:
            if browser_session.process.poll() is not None:
                browser_exited_at = browser_exited_at or now
            else:
                browser_exited_at = None
        if all_known_clients_closed:
            all_known_clients_closed_at = all_known_clients_closed_at or now
        else:
            all_known_clients_closed_at = None
        if live_clients or (connected and not all_known_clients_closed):
            no_live_clients_at = None
        else:
            no_live_clients_at = no_live_clients_at or now
        if all_known_clients_closed_at is not None:
            if now - all_known_clients_closed_at >= CLOSE_GRACE:
                return "all browser pages closed"
        if known_client and no_live_clients_at is not None:
            if now - no_live_clients_at >= CLOSE_GRACE:
                return "all browser pages closed"
        if (
            browser_exited_at is not None
            and no_live_clients_at is not None
            and not browser_ever_connected
            and now - max(browser_exited_at, no_live_clients_at)
            >= MANAGED_BROWSER_STARTUP_GRACE
        ):
            exit_code = browser_session.process.returncode if browser_session else None
            return f"managed browser failed before connecting; exit={exit_code}"
        if (
            browser_ever_connected
            and browser_exited_at is not None
            and no_live_clients_at is not None
        ):
            if now - max(browser_exited_at, no_live_clients_at) >= CLOSE_GRACE:
                return "managed browser window closed"
        if not known_client and now - armed_at >= FIRST_CLIENT_GRACE:
            return "browser never connected"
        time.sleep(0.5)
    return f"Streamlit exited with code {process.returncode}"


def run_streamlit_child() -> None:
    if not attach_current_process_to_named_job():
        raise SystemExit(3)
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


def open_browser(url: str) -> BrowserSession:
    browser = next(iter(browser_candidates()), None)
    if browser is None:
        write_log("No Edge/Chrome executable found; opening default browser.")
        with external_windows_dll_search_path():
            webbrowser.open(url)
        return BrowserSession()
    profile_dir = Path(tempfile.mkdtemp(prefix=BROWSER_PROFILE_PREFIX))
    arguments = [
        str(browser),
        f"--user-data-dir={profile_dir}",
        f"--app={url}",
        "--disable-background-mode",
        "--no-first-run",
        "--no-default-browser-check",
        "--ignore-gpu-blocklist",
        "--enable-webgl",
        "--enable-webgl2",
        "--enable-unsafe-swiftshader",
    ]
    write_log(
        f"Opening managed browser app: {browser}; profile={profile_dir}."
    )
    try:
        with external_windows_dll_search_path():
            browser_process = subprocess.Popen(
                arguments,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                env=external_process_environment(),
            )
        write_log(f"Managed browser process started; pid={browser_process.pid}.")
        return BrowserSession(browser_process, profile_dir)
    except OSError as exc:
        write_log(f"Managed browser start failed; using default browser: {exc}")
        shutil.rmtree(profile_dir, ignore_errors=True)
        with external_windows_dll_search_path():
            webbrowser.open(url)
        return BrowserSession()


def cleanup_browser_session(session: BrowserSession | None) -> None:
    if session is None:
        return
    process = session.process
    if process is not None and process.poll() is None:
        try:
            if os.name == "nt":
                try:
                    with external_windows_dll_search_path():
                        subprocess.run(
                            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                            check=False,
                            timeout=10,
                            env=external_process_environment(),
                        )
                except (OSError, subprocess.TimeoutExpired) as exc:
                    safe_write_log(
                        f"Unable to stop managed browser pid={process.pid}: {exc}"
                    )
            else:
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired) as exc:
            safe_write_log(f"Managed browser cleanup failed for pid={process.pid}: {exc}")
    profile_dir = session.profile_dir
    if profile_dir is None:
        return
    try:
        resolved_profile = profile_dir.resolve()
        resolved_temp = Path(tempfile.gettempdir()).resolve()
        safe = (
            resolved_temp in resolved_profile.parents
            and resolved_profile.name.startswith(BROWSER_PROFILE_PREFIX)
        )
    except OSError:
        safe = False
    if not safe:
        write_log(f"Refusing to remove unexpected browser profile path: {profile_dir}")
        return
    for _ in range(10):
        try:
            shutil.rmtree(resolved_profile)
            return
        except FileNotFoundError:
            return
        except OSError:
            time.sleep(0.25)
    write_log(f"Unable to remove temporary browser profile: {resolved_profile}")


def restore_standard_streams() -> None:
    """Restore redirected pipes for PyInstaller's windowed child process."""
    for name, descriptor in (("stdout", 1), ("stderr", 2)):
        if getattr(sys, name) is not None:
            continue
        try:
            stream = open(
                descriptor,
                "w",
                encoding="utf-8",
                errors="replace",
                buffering=1,
                closefd=False,
            )
        except OSError:
            stream = open(os.devnull, "w", encoding="utf-8")
        setattr(sys, name, stream)


def main() -> int:
    if "--python-snippet" in sys.argv:
        restore_standard_streams()
        snippet_index = sys.argv.index("--python-snippet") + 1
        if snippet_index >= len(sys.argv):
            print("Missing Python snippet path.", file=sys.stderr)
            return 2
        runpy.run_path(sys.argv[snippet_index], run_name="__main__")
        return 0
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
    process: subprocess.Popen | None = None
    browser_session: BrowserSession | None = None
    job_name = f"LissajousTutorJob_{os.getpid()}_{uuid.uuid4().hex}"
    job_handle = create_kill_on_close_job(job_name)
    if os.name == "nt" and job_handle is None:
        heartbeat_server.shutdown()
        heartbeat_server.server_close()
        show_error("应用进程安全初始化失败。请重新启动或联系维护人员。")
        return 1
    ack_path = (
        Path(tempfile.gettempdir())
        / f"lissajous_job_ack_{os.getpid()}_{uuid.uuid4().hex}.txt"
        if job_handle is not None
        else None
    )
    try:
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        child_environment = application_environment(
            heartbeat_url, streamlit_port, julia_port
        )
        if job_handle is not None and ack_path is not None:
            child_environment[JOB_NAME_ENV] = job_name
            child_environment[JOB_ACK_ENV] = str(ack_path)
        process = subprocess.Popen(
            streamlit_child_command(),
            env=child_environment,
            creationflags=creation_flags,
        )
        if not wait_for_job_attachment(process, ack_path):
            show_error("应用进程安全初始化失败。请重新启动或联系维护人员。")
            return 1
        write_log(
            "Started Streamlit child "
            f"pid={process.pid}; streamlit_port={streamlit_port}; "
            f"julia_port={julia_port}; heartbeat={heartbeat_url}"
        )
        if not wait_for_app(process, streamlit_port):
            write_log(f"Streamlit readiness failed; exit={process.poll()}")
            show_error("应用启动失败。请重新启动，或联系维护人员检查安装文件。")
            return 1
        write_log("Streamlit service is ready; opening browser.")
        browser_session = open_browser(app_url)
        heartbeat_state.arm()
        reason = monitor_browser(
            process, heartbeat_state, streamlit_port, browser_session
        )
        if reason.startswith("managed browser failed before connecting"):
            write_log(f"{reason}; retrying with the default browser.")
            cleanup_browser_session(browser_session)
            browser_session = BrowserSession()
            with external_windows_dll_search_path():
                opened = webbrowser.open(app_url)
            if not opened:
                show_error("浏览器窗口启动失败。请检查系统默认浏览器后重试。")
                return 1
            heartbeat_state.arm()
            reason = monitor_browser(
                process, heartbeat_state, streamlit_port, browser_session
            )
        write_log(f"Application supervisor stopping: {reason}.")
        return 0
    finally:
        for name, cleanup in (
            ("process job", lambda: terminate_process_job(job_handle)),
            (
                "Streamlit process tree",
                lambda: terminate_process_tree(process) if process is not None else None,
            ),
            ("heartbeat server", heartbeat_server.shutdown),
            ("heartbeat socket", heartbeat_server.server_close),
            ("browser session", lambda: cleanup_browser_session(browser_session)),
        ):
            try:
                cleanup()
            except Exception as exc:
                safe_write_log(f"Cleanup step failed ({name}): {exc}")
        if ack_path is not None:
            try:
                ack_path.unlink(missing_ok=True)
            except OSError as exc:
                safe_write_log(f"Unable to remove process-job acknowledgement: {exc}")
        safe_write_log("Application process tree stopped.")


if __name__ == "__main__":
    raise SystemExit(main())
