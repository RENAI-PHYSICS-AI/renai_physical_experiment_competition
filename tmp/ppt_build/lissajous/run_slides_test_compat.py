"""Run the official slides_test.py despite a Windows artifact-tool exit crash.

The renderer writes valid JSON and all PNGs, then the bundled native runtime exits
with 0xC0000409. This shim accepts that known-success condition and leaves the
official deck-enlargement and padding inspection logic unchanged.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


TOOLS = Path(
    r"C:\Users\junmo\.codex\plugins\cache\openai-primary-runtime"
    r"\presentations\26.805.11740\skills\presentations\container_tools"
)
sys.path.insert(0, str(TOOLS))

import render_slides  # type: ignore  # noqa: E402
import slides_test  # type: ignore  # noqa: E402


def render_accepting_known_native_exit(input_path: str, out_dir: str, dpi: int):
    scale = max(dpi / 96.0, 0.01)
    with tempfile.TemporaryDirectory(prefix="artifact_tool_workspace_") as workspace:
        proc = subprocess.run(
            [
                render_slides.node_binary(),
                os.path.join(render_slides.SCRIPT_DIR, "render_presentation.mjs"),
                "--input",
                input_path,
                "--output_dir",
                out_dir,
                "--scale",
                f"{scale:.6f}",
                "--workspace",
                workspace,
            ],
            capture_output=True,
            text=True,
            check=False,
            env=render_slides.runtime_env(),
        )

    try:
        payload = json.loads(proc.stdout)
        paths = payload["paths"]
    except Exception as exc:
        details = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"Renderer did not return valid output.\n{details}") from exc

    if not paths or not all(Path(p).is_file() for p in paths):
        raise RuntimeError("Renderer did not create every expected slide PNG.")

    if proc.returncode not in (0, -1073740791, 3221226505):
        details = (proc.stderr or "").strip()
        raise RuntimeError(f"Unexpected renderer exit code {proc.returncode}.\n{details}")
    return paths


render_slides._render_presentation_with_artifact_tool = render_accepting_known_native_exit
slides_test.main()
