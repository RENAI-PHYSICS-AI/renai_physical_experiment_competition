from __future__ import annotations

import math
import os
import re
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

from config import (
    JULIA_PROJECT_DIR,
    JULIA_RUN_PATH,
    JULIA_WEB_HOST,
    JULIA_WEB_PATH,
    JULIA_WEB_PORT,
)


NUMBER = r"([-+]?\d+(?:\.\d+)?)"
_JULIA_WEB_PROCESS: subprocess.Popen | None = None
_JULIA_WEB_LOG = None


def _external_process_environment() -> dict[str, str]:
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
                if item and (not Path(item).exists() or Path(item).resolve() != mei_path)
            )
        except OSError:
            pass
    return environment


@contextmanager
def _external_dll_search_path():
    if os.name != "nt" or not getattr(sys, "frozen", False):
        yield
        return
    kernel32 = None
    changed = False
    previous = None
    try:
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
    except Exception:
        kernel32 = None
    try:
        yield
    finally:
        if changed and kernel32 is not None:
            kernel32.SetDllDirectoryW(previous)


def calculate_sound_speed(
    method: str,
    *,
    distance: float | None = None,
    time_delay: float | None = None,
    frequency: float | None = None,
    wavelength: float | None = None,
    angle_degree: float = 0.0,
    phase_degree: float | None = None,
    cycles: int = 0,
) -> dict:
    method = method.lower().strip()
    if method in {"echo", "回声"}:
        if not distance or not time_delay or distance <= 0 or time_delay <= 0:
            raise ValueError("回声法需要正的墙面距离和时间差。")
        speed = 2.0 * distance / time_delay
        formula = "v = 2d / Δt"
    elif method in {"dual", "双麦克风", "时间差"}:
        if not distance or not time_delay or distance <= 0 or time_delay <= 0:
            raise ValueError("双麦克风法需要正的麦克风间距和时间差。")
        projected_distance = distance * math.cos(math.radians(angle_degree))
        if projected_distance <= 0:
            raise ValueError("传播方向与麦克风基线的夹角必须小于 90°。")
        speed = projected_distance / time_delay
        formula = "v = d cosθ / Δt"
    elif method in {"standing", "驻波", "共振"}:
        if not frequency or not wavelength or frequency <= 0 or wavelength <= 0:
            raise ValueError("驻波法需要正的频率和波长。")
        speed = frequency * wavelength
        formula = "v = fλ"
    elif method in {"phase", "相位", "示波器"}:
        if not distance or not frequency or phase_degree is None:
            raise ValueError("相位差法需要距离、频率、包裹相位和完整周期数。")
        total_phase = 2.0 * math.pi * cycles + math.radians(phase_degree % 360)
        if distance <= 0 or frequency <= 0 or total_phase <= 0:
            raise ValueError("相位差法参数必须给出正的总传播相位。")
        speed = 2.0 * math.pi * frequency * distance / total_phase
        formula = "v = 2πfd / (2πn + φ)"
    else:
        raise ValueError(f"不支持的声速测量方法：{method}")
    return {
        "method": method,
        "speed": speed,
        "formula": formula,
        "distance": distance,
        "time_delay": time_delay,
        "frequency": frequency,
        "wavelength": wavelength,
        "angle_degree": angle_degree,
        "phase_degree": phase_degree,
        "cycles": cycles,
    }


def _match_value(question: str, labels: tuple[str, ...]) -> float | None:
    for label in labels:
        match = re.search(rf"(?:{label})\s*[为=:]?\s*{NUMBER}", question, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def parse_calculation_request(question: str) -> dict | None:
    lowered = question.lower()
    distance = _match_value(lowered, (r"距离", r"间距", r"管长", r"d"))
    delay_ms = _match_value(lowered, (r"时间差", r"时延", r"延迟", r"Δt", r"dt"))
    frequency = _match_value(lowered, (r"频率", r"f"))
    wavelength = _match_value(lowered, (r"波长", r"λ", r"lambda"))
    angle = _match_value(lowered, (r"夹角", r"θ", r"theta")) or 0.0
    phase = _match_value(lowered, (r"相位差", r"相位", r"φ", r"phi"))
    cycles_value = _match_value(lowered, (r"完整周期数", r"周期数", r"n"))

    # Natural-language measurements usually state delay in milliseconds.
    time_delay = delay_ms / 1000.0 if delay_ms is not None and "ms" in lowered else delay_ms
    try:
        if "回声" in lowered and distance is not None and time_delay is not None:
            return calculate_sound_speed("echo", distance=distance, time_delay=time_delay)
        if any(key in lowered for key in ("双麦克风", "时间差法", "互相关")) and distance is not None and time_delay is not None:
            return calculate_sound_speed(
                "dual",
                distance=distance,
                time_delay=time_delay,
                angle_degree=angle,
            )
        if any(key in lowered for key in ("驻波", "共振")) and frequency and wavelength:
            return calculate_sound_speed("standing", frequency=frequency, wavelength=wavelength)
        if any(key in lowered for key in ("相位差法", "示波器")) and distance and frequency and phase is not None:
            return calculate_sound_speed(
                "phase",
                distance=distance,
                frequency=frequency,
                phase_degree=phase,
                cycles=int(cycles_value or 0),
            )
    except ValueError:
        return None
    return None


def format_calculation(result: dict) -> str:
    return (
        f"确定性计算结果：采用 {result['formula']}，"
        f"得到声速 v = {result['speed']:.3f} m/s。"
    )


def julia_launch_command() -> list[str]:
    packaged_executable = os.getenv("SOUND_SPEED_JULIA_EXE")
    if packaged_executable:
        packaged_script = os.getenv("SOUND_SPEED_JULIA_SCRIPT")
        if packaged_script:
            return [
                packaged_executable,
                "--startup-file=no",
                "--compiled-modules=yes",
                "--pkgimages=no",
                f"--project={JULIA_PROJECT_DIR}",
                packaged_script,
                "--no-instantiate",
            ]
        return [packaged_executable]
    return [
        "julia",
        f"--project={JULIA_PROJECT_DIR}",
        str(JULIA_WEB_PATH),
        "--no-instantiate",
    ]


def launch_julia_visualization() -> subprocess.Popen:
    packaged_executable = os.getenv("SOUND_SPEED_JULIA_EXE")
    if not packaged_executable and not JULIA_RUN_PATH.exists():
        raise FileNotFoundError(f"未找到 Julia 可视化程序：{JULIA_RUN_PATH}")
    creation_flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    command = (
        julia_launch_command()
        if packaged_executable
        else [
            "julia",
            f"--project={JULIA_RUN_PATH.parent}",
            str(JULIA_RUN_PATH),
            "--no-instantiate",
        ]
    )
    with _external_dll_search_path():
        return subprocess.Popen(
            command,
            cwd=JULIA_PROJECT_DIR if packaged_executable else JULIA_RUN_PATH.parent,
            env=_external_process_environment(),
            creationflags=creation_flags,
        )


def julia_web_server_ready(timeout: float = 0.8) -> bool:
    # The WGLMakie root page is expensive to render and can routinely take
    # longer than this readiness timeout.  Probing it repeatedly also adds
    # load to the single Julia service.  A successful TCP connection is the
    # appropriate readiness signal here; the browser will request the page
    # only after the listener exists.
    probe_host = JULIA_WEB_HOST
    if probe_host in {"", "0.0.0.0", "::"}:
        probe_host = "127.0.0.1"
    try:
        with socket.create_connection((probe_host, JULIA_WEB_PORT), timeout=timeout):
            return True
    except OSError:
        return False


def launch_julia_web_server() -> subprocess.Popen | None:
    global _JULIA_WEB_LOG, _JULIA_WEB_PROCESS
    if julia_web_server_ready():
        return _JULIA_WEB_PROCESS
    if _JULIA_WEB_PROCESS is not None and _JULIA_WEB_PROCESS.poll() is None:
        return _JULIA_WEB_PROCESS
    packaged_executable = os.getenv("SOUND_SPEED_JULIA_EXE")
    if not packaged_executable and not JULIA_WEB_PATH.exists():
        raise FileNotFoundError(f"未找到 Julia 网页实验程序：{JULIA_WEB_PATH}")

    log_dir = os.getenv("SOUND_SPEED_LOG_DIR", "").strip()
    if log_dir:
        persistent_log_dir = Path(log_dir).resolve()
        persistent_log_dir.mkdir(parents=True, exist_ok=True)
        log_path = persistent_log_dir / "julia_web.log"
    else:
        log_path = JULIA_PROJECT_DIR / "web_stdout.log"
    _JULIA_WEB_LOG = log_path.open("a", encoding="utf-8")
    creation_flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    creation_flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
    environment = _external_process_environment()
    environment["SOUND_SPEED_WEB_HOST"] = JULIA_WEB_HOST
    environment["SOUND_SPEED_WEB_PORT"] = str(JULIA_WEB_PORT)
    environment["SOUND_SPEED_WEB_BROWSER_HOST"] = "127.0.0.1"
    command = (
        julia_launch_command()
        if packaged_executable
        else [
            "julia",
            f"--project={JULIA_PROJECT_DIR}",
            str(JULIA_WEB_PATH),
            "--no-instantiate",
        ]
    )
    with _external_dll_search_path():
        _JULIA_WEB_PROCESS = subprocess.Popen(
            command,
            cwd=JULIA_PROJECT_DIR,
            env=environment,
            stdout=_JULIA_WEB_LOG,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags,
        )
    return _JULIA_WEB_PROCESS


def ensure_julia_web_server(timeout: float = 90.0) -> subprocess.Popen | None:
    process = launch_julia_web_server()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if julia_web_server_ready():
            return process
        if process is not None and process.poll() is not None:
            log_name = getattr(_JULIA_WEB_LOG, "name", "web_stdout.log")
            raise RuntimeError(f"Julia 网页实验服务启动失败，请检查日志：{log_name}")
        time.sleep(0.5)
    raise TimeoutError("Julia 网页实验服务启动超时，请稍后刷新页面。")
