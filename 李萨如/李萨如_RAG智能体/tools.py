from __future__ import annotations

import math
import os
import re
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from fractions import Fraction
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


def calculate_lissajous(
    frequency_x: float,
    frequency_y: float,
    phase_degree: float = 0.0,
    amplitude_x: float = 1.0,
    amplitude_y: float = 1.0,
) -> dict:
    if frequency_x <= 0 or frequency_y <= 0:
        raise ValueError("频率必须为正数。")
    if amplitude_x <= 0 or amplitude_y <= 0:
        raise ValueError("振幅必须为正数。")
    ratio = Fraction(frequency_x / frequency_y).limit_denominator(64)
    rational_error = abs(float(ratio) - frequency_x / frequency_y)
    closed = rational_error < 1.0e-6
    common_frequency = frequency_x / ratio.numerator if closed else None
    close_period = 1.0 / common_frequency if common_frequency else None
    phase_radian = math.radians(phase_degree)
    shape = "一般李萨如曲线"
    area = None
    if math.isclose(frequency_x, frequency_y, rel_tol=1.0e-9):
        sine = math.sin(phase_radian)
        if abs(sine) < 1.0e-8:
            shape = "直线"
        elif math.isclose(amplitude_x, amplitude_y, rel_tol=1.0e-9) and math.isclose(
            abs(sine), 1.0, rel_tol=1.0e-8
        ):
            shape = "圆"
        else:
            shape = "椭圆"
        area = math.pi * amplitude_x * amplitude_y * abs(sine)
    return {
        "frequency_x": frequency_x,
        "frequency_y": frequency_y,
        "ratio": f"{ratio.numerator}:{ratio.denominator}",
        "closed": closed,
        "close_period": close_period,
        "phase_degree": phase_degree % 360,
        "shape": shape,
        "area": area,
    }


def parse_calculation_request(question: str) -> dict | None:
    patterns = {
        "frequency_x": [rf"f[_ ]?x\s*[=:为]?\s*{NUMBER}", rf"x方向频率\s*[为=:]?\s*{NUMBER}"],
        "frequency_y": [rf"f[_ ]?y\s*[=:为]?\s*{NUMBER}", rf"y方向频率\s*[为=:]?\s*{NUMBER}"],
        "phase_degree": [rf"(?:相位差|phi|φ)\s*[为=:]?\s*{NUMBER}"],
        "amplitude_x": [rf"a[_ ]?x\s*[=:为]?\s*{NUMBER}"],
        "amplitude_y": [rf"a[_ ]?y\s*[=:为]?\s*{NUMBER}"],
    }
    values: dict[str, float] = {}
    lowered = question.lower()
    for key, candidates in patterns.items():
        for pattern in candidates:
            match = re.search(pattern, lowered, flags=re.IGNORECASE)
            if match:
                values[key] = float(match.group(1))
                break
    if "frequency_x" not in values or "frequency_y" not in values:
        return None
    values.setdefault("phase_degree", 0.0)
    values.setdefault("amplitude_x", 1.0)
    values.setdefault("amplitude_y", 1.0)
    return calculate_lissajous(**values)


def format_calculation(result: dict) -> str:
    close_text = (
        f"闭合周期约为 {result['close_period']:.6g} s"
        if result["close_period"] is not None
        else "在当前有理数容差下不形成严格闭合轨迹"
    )
    area_text = (
        f"；轨迹面积约为 {result['area']:.6g}"
        if result["area"] is not None
        else ""
    )
    return (
        f"计算工具结果：频率比 fx:fy = {result['ratio']}；"
        f"形状判定为{result['shape']}；{close_text}{area_text}。"
    )


def julia_launch_command() -> list[str]:
    packaged_executable = os.getenv("LISSAJOUS_JULIA_EXE")
    if packaged_executable:
        packaged_script = os.getenv("LISSAJOUS_JULIA_SCRIPT")
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
        str(JULIA_RUN_PATH),
        "--no-instantiate",
    ]


def launch_julia_visualization() -> subprocess.Popen:
    if not JULIA_RUN_PATH.exists():
        raise FileNotFoundError(f"未找到 Julia 可视化程序：{JULIA_RUN_PATH}")
    creation_flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    with _external_dll_search_path():
        return subprocess.Popen(
            julia_launch_command(),
            cwd=JULIA_PROJECT_DIR,
            env=_external_process_environment(),
            creationflags=creation_flags,
        )


def julia_web_server_ready(timeout: float = 0.8) -> bool:
    # Rendering the WGLMakie root page is too expensive for a readiness probe.
    # Check the dedicated listener instead, then let the embedded browser make
    # the actual page request once Julia is accepting connections.
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
    packaged_executable = os.getenv("LISSAJOUS_JULIA_EXE")
    if not packaged_executable and not JULIA_WEB_PATH.exists():
        raise FileNotFoundError(f"未找到 Julia 网页实验程序：{JULIA_WEB_PATH}")

    log_dir = os.getenv("LISSAJOUS_LOG_DIR", "").strip()
    if log_dir:
        persistent_log_dir = os.path.abspath(log_dir)
        os.makedirs(persistent_log_dir, exist_ok=True)
        log_path = os.path.join(persistent_log_dir, "julia_web.log")
    else:
        log_path = JULIA_PROJECT_DIR / "web_stdout.log"
    from pathlib import Path
    log_path = Path(log_path)
    _JULIA_WEB_LOG = log_path.open("a", encoding="utf-8")
    creation_flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    creation_flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
    environment = _external_process_environment()
    environment["LISSAJOUS_WEB_HOST"] = JULIA_WEB_HOST
    environment["LISSAJOUS_WEB_PORT"] = str(JULIA_WEB_PORT)
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


def ensure_julia_web_server(timeout: float = 75.0) -> subprocess.Popen | None:
    process = launch_julia_web_server()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if julia_web_server_ready():
            return process
        if process is not None and process.poll() is not None:
            raise RuntimeError(f"Julia 网页实验服务启动失败，请检查日志：{getattr(_JULIA_WEB_LOG, 'name', 'web_stdout.log')}")
        time.sleep(0.5)
    raise TimeoutError("Julia 网页实验服务启动超时，请稍后刷新页面。")
