from __future__ import annotations

import ast
import os
import re
import shutil
import subprocess
import sys
import textwrap
import uuid
from pathlib import Path


PY_CODE_BLOCK_RE = re.compile(r"```(?:python|py)\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
OUTPUT_PREVIEW_CHARS = 20_000

SENSITIVE_ENV_KEYWORDS = (
    "KEY", "TOKEN", "SECRET", "PASSWORD", "API", "AUTH", "SIGNATURE", "ACCESS",
)
SENSITIVE_CODE_PATTERNS = (
    r"\bos\.environ\b",
    r"\bos\.getenv\s*\(",
    r"\bgetenv\s*\(",
    r"\benviron\.",
    r"\bsubprocess\.",
    r"\bprintenv\b",
    r"\bset\b",
    r"\bst\.secrets\b",
    r"\bstreamlit\.secrets\b",
)

ALLOWED_IMPORT_ROOTS = {"matplotlib", "numpy", "scipy", "PIL"}
BLOCKED_MODULE_ROOTS = {
    "builtins", "ctypes", "glob", "http", "importlib", "io", "multiprocessing",
    "pathlib", "pickle", "requests", "shutil", "socket", "subprocess", "sys",
    "tempfile", "urllib", "xml",
}
BLOCKED_CALLS = {"open", "eval", "exec", "compile", "input", "__import__"}
BLOCKED_ATTRIBUTES = {"__builtins__", "__class__", "__code__", "__globals__", "__subclasses__"}


def extract_python_blocks(markdown_text: str) -> list[str]:
    """Extract non-empty Python fenced code blocks from Markdown."""
    return [block.strip() for block in PY_CODE_BLOCK_RE.findall(markdown_text or "") if block.strip()]


def inspect_code_safety(code: str) -> tuple[bool, str]:
    """Apply the teaching-agent blacklist before starting a subprocess."""
    upper_code = (code or "").upper()
    has_sensitive_keyword = any(keyword in upper_code for keyword in SENSITIVE_ENV_KEYWORDS)
    hits = [pattern for pattern in SENSITIVE_CODE_PATTERNS if re.search(pattern, code or "", re.IGNORECASE)]

    if hits and has_sensitive_keyword:
        return False, "代码尝试读取环境变量或密钥配置，并可能泄露敏感信息，已阻止执行。"
    if re.search(r"\b(os\.environ|os\.getenv|getenv)\b", code or "", re.IGNORECASE):
        return False, "代码包含环境变量读取操作，已阻止执行。"
    if re.search(r"\b(st\.secrets|streamlit\.secrets)\b", code or "", re.IGNORECASE):
        return False, "代码尝试读取 Streamlit secrets 配置，已阻止执行。"

    try:
        tree = ast.parse(code or "")
    except SyntaxError as exc:
        return False, f"代码语法错误，已阻止执行：{exc}"

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = node.names if isinstance(node, ast.Import) else [node]
            for item in names:
                module = item.name if isinstance(node, ast.Import) else (item.module or "")
                root = module.split(".", 1)[0]
                if root in BLOCKED_MODULE_ROOTS or root not in ALLOWED_IMPORT_ROOTS:
                    return False, f"代码尝试导入受限模块 `{module}`，已阻止执行。"
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in BLOCKED_CALLS:
                return False, f"代码调用受限函数 `{node.func.id}`，已阻止执行。"
            if isinstance(node.func, ast.Attribute) and node.func.attr in {
                "system", "popen", "run", "call", "check_call", "check_output",
            }:
                return False, f"代码尝试调用受限进程操作 `{node.func.attr}`，已阻止执行。"
        elif isinstance(node, ast.Attribute) and node.attr in BLOCKED_ATTRIBUTES:
            return False, f"代码尝试访问受限运行时属性 `{node.attr}`，已阻止执行。"

    return True, ""


def _bootstrap_tail() -> str:
    return r'''

# ---- auto-capture matplotlib outputs for the experiment tutor ----
try:
    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt
    from matplotlib.animation import Animation

    import os as _os
    _existing_anim = any(
        _name.lower().endswith((".gif", ".mp4", ".webm"))
        for _name in _os.listdir(".")
    )
    if not _existing_anim:
        for _name, _value in list(globals().items()):
            if isinstance(_value, Animation):
                try:
                    _value.save("animation.gif", writer="pillow", fps=20)
                except Exception as _anim_exc:
                    print(f"[auto-capture-warning] animation save failed: {_anim_exc}")
                break

    if plt.get_fignums():
        for _idx, _fig_num in enumerate(plt.get_fignums(), start=1):
            try:
                _fig = plt.figure(_fig_num)
                _width, _height = _fig.get_size_inches()
                _dpi = 150
                _pixels = max(_width * _dpi, 1) * max(_height * _dpi, 1)
                if _pixels > 40_000_000:
                    _scale = (40_000_000 / _pixels) ** 0.5
                    _dpi = max(30, int(_dpi * _scale))
                    print(f"[auto-capture-warning] figure too large; saving at dpi={_dpi}")
                _fig.savefig(f"figure_{_idx}.png", dpi=_dpi, bbox_inches="tight")
            except Exception as _fig_exc:
                print(f"[auto-capture-warning] figure save failed: {_fig_exc}")
except Exception as _capture_exc:
    print(f"[auto-capture-warning] {_capture_exc}")
'''


def _child_command(script_path: Path) -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--python-snippet", str(script_path)]
    return [sys.executable, str(script_path)]


def run_python_block(code: str, output_root: str | os.PathLike, timeout: int = 60) -> dict:
    """Run one approved code block in a unique directory and collect its outputs."""
    is_safe, reason = inspect_code_safety(code)
    if not is_safe:
        return {
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "visuals": [],
            "run_dir": "",
            "blocked": True,
            "block_reason": reason,
        }

    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    run_dir = output_root / f"run_{uuid.uuid4().hex[:12]}"
    run_dir.mkdir(parents=True, exist_ok=True)

    script_path = run_dir / "snippet.py"
    script_path.write_text(
        "import matplotlib\nmatplotlib.use('Agg', force=True)\n\n"
        + code
        + "\n"
        + textwrap.dedent(_bootstrap_tail()),
        encoding="utf-8",
    )

    env = {
        "MPLBACKEND": "Agg",
        "PYTHONIOENCODING": "utf-8",
        "PATH": os.environ.get("PATH", ""),
        "SystemRoot": os.environ.get("SystemRoot", ""),
        "WINDIR": os.environ.get("WINDIR", ""),
        "TEMP": os.environ.get("TEMP", ""),
        "TMP": os.environ.get("TMP", ""),
    }
    mpl_config_dir = run_dir / "mplconfig"
    mpl_config_dir.mkdir(exist_ok=True)
    env["MPLCONFIGDIR"] = str(mpl_config_dir)

    proc = subprocess.run(
        _child_command(script_path),
        cwd=str(run_dir),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    visuals: list[Path] = []
    for pattern in ("*.gif", "*.png", "*.jpg", "*.jpeg", "*.mp4", "*.webm"):
        visuals.extend(path for path in run_dir.glob(pattern) if path.is_file())

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    stdout_path = run_dir / "stdout.txt"
    stderr_path = run_dir / "stderr.txt"
    if stdout:
        stdout_path.write_text(stdout, encoding="utf-8", errors="replace")
    if stderr:
        stderr_path.write_text(stderr, encoding="utf-8", errors="replace")

    return {
        "returncode": proc.returncode,
        "stdout": stdout[-OUTPUT_PREVIEW_CHARS:],
        "stderr": stderr[-OUTPUT_PREVIEW_CHARS:],
        "stdout_truncated": len(stdout) > OUTPUT_PREVIEW_CHARS,
        "stderr_truncated": len(stderr) > OUTPUT_PREVIEW_CHARS,
        "stdout_path": str(stdout_path) if stdout else "",
        "stderr_path": str(stderr_path) if stderr else "",
        "visuals": [str(path) for path in sorted(visuals)],
        "run_dir": str(run_dir),
        "blocked": False,
    }


def cleanup_old_runs(output_root: str | os.PathLike, keep: int = 25) -> None:
    output_root = Path(output_root)
    if not output_root.exists():
        return
    runs = sorted(
        (path for path in output_root.glob("run_*") if path.is_dir()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for old in runs[keep:]:
        shutil.rmtree(old, ignore_errors=True)
