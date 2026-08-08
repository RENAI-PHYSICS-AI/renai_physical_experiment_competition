from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path


report_path = Path(os.environ["TUTOR_UI_REPORT"])


def write_failure(error: BaseException) -> None:
    report_path.write_text(
        json.dumps(
            {
                "passed": False,
                "error": "".join(traceback.format_exception(type(error), error, error.__traceback__)),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    root = Path(getattr(sys, "_MEIPASS", ""))
    require(root.is_dir(), "PyInstaller extraction root is unavailable")
    app_dir = root / "app"
    julia_exe = root / "julia_app" / "bin" / "SoundSpeedWebRuntime.exe"
    require((app_dir / "app.py").is_file(), "embedded app.py is missing")
    require(julia_exe.is_file(), "embedded Julia executable is missing")

    from _embedded_secret import reveal_api_key

    os.environ["SOUND_SPEED_APP_DIR"] = str(app_dir)
    os.environ["SOUND_SPEED_LLM_API_KEY"] = reveal_api_key()
    os.environ["SOUND_SPEED_JULIA_EXE"] = str(julia_exe)
    os.environ["SOUND_SPEED_JULIA_PROJECT_DIR"] = str(root / "julia_app")
    sys.path.insert(0, str(app_dir))

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        julia_port = int(probe.getsockname()[1])

    with tempfile.TemporaryDirectory(prefix="sound_speed_ui_julia_depot_") as empty_depot:
        environment = os.environ.copy()
        environment["JULIA_DEPOT_PATH"] = empty_depot
        environment["SOUND_SPEED_WEB_HOST"] = "127.0.0.1"
        environment["SOUND_SPEED_WEB_BROWSER_HOST"] = "127.0.0.1"
        environment["SOUND_SPEED_WEB_PORT"] = str(julia_port)
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
                    with socket.create_connection(("127.0.0.1", julia_port), timeout=0.5):
                        break
                except OSError:
                    time.sleep(0.5)
            else:
                raise RuntimeError("embedded Julia server did not start")

            os.environ["SOUND_SPEED_WEB_HOST"] = "127.0.0.1"
            os.environ["SOUND_SPEED_WEB_BROWSER_HOST"] = "127.0.0.1"
            os.environ["SOUND_SPEED_WEB_PORT"] = str(julia_port)

            import config
            import tools
            from streamlit.testing.v1 import AppTest

            config.JULIA_WEB_URL = f"http://127.0.0.1:{julia_port}"
            tools.JULIA_WEB_HOST = "127.0.0.1"
            tools.JULIA_WEB_PORT = julia_port

            app_test = AppTest.from_file(str(app_dir / "app.py"), default_timeout=180)
            app_test.run()
            require(not app_test.exception, f"embedded Streamlit app raised: {app_test.exception}")

            tab_labels = [str(tab.label) for tab in app_test.tabs]
            chat_placeholders = [str(item.placeholder) for item in app_test.chat_input]
            require("演示实验" in tab_labels, f"demo tab missing: {tab_labels}")
            require("智能问答" in tab_labels, f"Q&A tab missing: {tab_labels}")
            require(chat_placeholders, "chat input is missing")
            require(any("声速" in placeholder for placeholder in chat_placeholders), chat_placeholders)

            report = {
                "passed": True,
                "tabs": tab_labels,
                "chat_inputs": chat_placeholders,
                "julia_port": julia_port,
                "streamlit_exceptions": 0,
            }
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(report, ensure_ascii=False))
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BaseException as error:
        if not isinstance(error, SystemExit) or error.code:
            write_failure(error)
        raise
