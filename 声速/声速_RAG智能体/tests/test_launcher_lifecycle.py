from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import types
import unittest
import importlib.util
import os
from pathlib import Path
from unittest.mock import MagicMock, patch


PROJECT_DIR = Path(__file__).resolve().parents[1]
PACKAGING_DIR = PROJECT_DIR / "packaging"
sys.path.insert(0, str(PACKAGING_DIR))
sys.path.insert(0, str(PROJECT_DIR))

if "_embedded_secret" not in sys.modules:
    secret_module = types.ModuleType("_embedded_secret")
    secret_module.reveal_api_key = lambda: ""
    sys.modules["_embedded_secret"] = secret_module

SPEC = importlib.util.spec_from_file_location("sound_speed_launcher_lifecycle", PACKAGING_DIR / "launcher.py")
assert SPEC is not None and SPEC.loader is not None
launcher = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = launcher
SPEC.loader.exec_module(launcher)


class FakeProcess:
    def __init__(self, polls: list[int | None]) -> None:
        self.polls = iter(polls)
        self.returncode = None

    def poll(self) -> int | None:
        try:
            value = next(self.polls)
        except StopIteration:
            value = 0
        self.returncode = value
        return value


class LauncherLifecycleTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "win32", "Windows Job Object test")
    def test_named_job_child_attaches_before_descendants(self) -> None:
        import uuid

        job_name = f"SoundSpeedTestJob_{os.getpid()}_{uuid.uuid4().hex}"
        ack_path = Path(tempfile.gettempdir()) / f"sound_speed_test_ack_{uuid.uuid4().hex}.txt"
        job_handle = launcher.create_kill_on_close_job(job_name)
        self.assertIsNotNone(job_handle)
        environment = os.environ.copy()
        environment[launcher.JOB_NAME_ENV] = job_name
        environment[launcher.JOB_ACK_ENV] = str(ack_path)
        child = subprocess.Popen(
            [
                str(getattr(sys, "_base_executable", sys.executable)),
                "-c",
                (
                    "import importlib.util,sys,time,types;"
                    "x=types.ModuleType('_embedded_secret');x.reveal_api_key=lambda:'';"
                    "sys.modules['_embedded_secret']=x;"
                    f"p=r'{PACKAGING_DIR / 'launcher.py'}';"
                    "s=importlib.util.spec_from_file_location('job_child_launcher',p);"
                    "m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m);"
                    "raise SystemExit(0 if m.attach_current_process_to_named_job() else 73)"
                ),
            ],
            env=environment,
        )
        try:
            self.assertTrue(launcher.wait_for_job_attachment(child, ack_path, timeout=5))
            child.wait(timeout=5)
            self.assertEqual(child.returncode, 0)
        finally:
            launcher.terminate_process_job(job_handle)
            ack_path.unlink(missing_ok=True)

    def test_late_heartbeat_cannot_revive_closed_client(self) -> None:
        state = launcher.HeartbeatState()
        state.heartbeat("client-a", 1)
        state.closed("client-a", 2)
        state.heartbeat("client-a", 1)
        _armed_at, clients = state.snapshot()
        self.assertIsNotNone(clients["client-a"][2])

    def test_multiple_clients_are_tracked_independently(self) -> None:
        state = launcher.HeartbeatState()
        state.heartbeat("client-a", 1)
        state.heartbeat("client-b", 1)
        state.closed("client-a", 2)
        _armed_at, clients = state.snapshot()
        self.assertIsNotNone(clients["client-a"][2])
        self.assertIsNone(clients["client-b"][2])

    def test_external_environment_drops_pyinstaller_internal_values(self) -> None:
        with patch.dict(
            launcher.os.environ,
            {"_PYI_ARCHIVE_FILE": "private", "_MEIPASS2": "private", "KEEP_ME": "ok"},
            clear=True,
        ):
            environment = launcher.external_process_environment()
        self.assertNotIn("_PYI_ARCHIVE_FILE", environment)
        self.assertNotIn("_MEIPASS2", environment)
        self.assertEqual(environment["KEEP_ME"], "ok")

    def test_managed_browser_exit_waits_for_connection_to_close(self) -> None:
        app_process = FakeProcess([None, None, 0])
        browser_process = FakeProcess([0, 0])
        session = launcher.BrowserSession(browser_process, None)
        with (
            patch.object(launcher.time, "sleep"),
            patch.object(launcher, "streamlit_browser_connected", return_value=True),
        ):
            reason = launcher.monitor_browser(app_process, launcher.HeartbeatState(), 8502, session)
        self.assertEqual(reason, "Streamlit exited with code 0")

    def test_managed_browser_exit_after_connection_closes(self) -> None:
        app_process = FakeProcess([None, None])
        browser_process = FakeProcess([0, 0])
        session = launcher.BrowserSession(browser_process, None)
        state = launcher.HeartbeatState()
        state.heartbeat("client-a", 1)
        state.closed("client-a", 2)
        with (
            patch.object(launcher.time, "sleep"),
            patch.object(launcher, "streamlit_browser_connected", return_value=False),
            patch.object(launcher, "CLOSE_GRACE", 0.0),
        ):
            reason = launcher.monitor_browser(app_process, state, 8502, session)
        self.assertEqual(reason, "all browser pages closed")

    def test_managed_browser_early_exit_is_startup_failure(self) -> None:
        app_process = FakeProcess([None, None])
        browser_process = FakeProcess([7, 7])
        session = launcher.BrowserSession(browser_process, None)
        with (
            patch.object(launcher.time, "sleep"),
            patch.object(launcher, "streamlit_browser_connected", return_value=False),
            patch.object(launcher, "MANAGED_BROWSER_STARTUP_GRACE", 0.0),
        ):
            reason = launcher.monitor_browser(
                app_process, launcher.HeartbeatState(), 8502, session
            )
        self.assertEqual(reason, "managed browser failed before connecting; exit=7")

    def test_open_browser_uses_isolated_app_profile(self) -> None:
        browser = Path("C:/Program Files/Browser/browser.exe")
        fake_process = MagicMock()
        profile_dir: Path | None = None
        with (
            patch.object(launcher, "browser_candidates", return_value=[browser]),
            patch.object(launcher.subprocess, "Popen", return_value=fake_process) as popen,
            patch.object(launcher, "write_log"),
        ):
            session = launcher.open_browser("http://127.0.0.1:8502")
            profile_dir = session.profile_dir
        self.assertIs(session.process, fake_process)
        arguments = popen.call_args.args[0]
        self.assertIn("--app=http://127.0.0.1:8502", arguments)
        self.assertIn("--disable-background-mode", arguments)
        self.assertTrue(any(arg.startswith("--user-data-dir=") for arg in arguments))
        if profile_dir is not None:
            shutil.rmtree(profile_dir, ignore_errors=True)

    def test_cleanup_only_removes_expected_temporary_profile(self) -> None:
        profile = Path(tempfile.mkdtemp(prefix=launcher.BROWSER_PROFILE_PREFIX))
        (profile / "probe.txt").write_text("temporary", encoding="utf-8")
        launcher.cleanup_browser_session(launcher.BrowserSession(None, profile))
        self.assertFalse(profile.exists())

    def test_cleanup_profile_continues_after_taskkill_timeout(self) -> None:
        profile = Path(tempfile.mkdtemp(prefix=launcher.BROWSER_PROFILE_PREFIX))
        process = MagicMock()
        process.poll.return_value = None
        process.pid = 4242
        process.wait.side_effect = subprocess.TimeoutExpired("wait", 10)
        with (
            patch.object(launcher.os, "name", "nt"),
            patch.object(
                launcher.subprocess,
                "run",
                side_effect=subprocess.TimeoutExpired("taskkill", 10),
            ),
        ):
            launcher.cleanup_browser_session(launcher.BrowserSession(process, profile))
        self.assertFalse(profile.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
