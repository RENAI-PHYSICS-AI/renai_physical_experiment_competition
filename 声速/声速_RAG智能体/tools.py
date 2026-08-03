from __future__ import annotations

import math
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from config import (
    JULIA_PROJECT_DIR,
    JULIA_RUN_PATH,
    JULIA_WEB_HOST,
    JULIA_WEB_PATH,
    JULIA_WEB_PORT,
    JULIA_WEB_URL,
)


NUMBER = r"([-+]?\d+(?:\.\d+)?)"
_JULIA_WEB_PROCESS: subprocess.Popen | None = None
_JULIA_WEB_LOG = None


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
    return subprocess.Popen(
        command,
        cwd=JULIA_PROJECT_DIR if packaged_executable else JULIA_RUN_PATH.parent,
        creationflags=creation_flags,
    )


def julia_web_server_ready(timeout: float = 0.8) -> bool:
    try:
        with urllib.request.urlopen(f"{JULIA_WEB_URL}/", timeout=timeout) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
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
    environment = os.environ.copy()
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
