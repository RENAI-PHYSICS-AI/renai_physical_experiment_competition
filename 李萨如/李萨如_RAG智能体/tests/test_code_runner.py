from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

import code_runner


class CodeRunnerTests(unittest.TestCase):
    def test_extracts_python_blocks(self):
        blocks = code_runner.extract_python_blocks(
            "说明\n```python\nprint('a')\n```\n```py\nprint('b')\n```"
        )
        self.assertEqual(blocks, ["print('a')", "print('b')"])

    def test_blocks_sensitive_and_file_access(self):
        for source in (
            "import requests",
            "print(open('secret.txt').read())",
            "import os\nprint(os.environ)",
            "eval('1 + 1')",
        ):
            with self.subTest(source=source):
                self.assertFalse(code_runner.inspect_code_safety(source)[0])

    def test_allows_scientific_code(self):
        safe, reason = code_runner.inspect_code_safety(
            "import numpy as np\nimport matplotlib.pyplot as plt\nplt.plot(np.arange(3))"
        )
        self.assertTrue(safe, reason)

    def test_uses_unique_directory_filtered_environment_and_timeout(self):
        completed = subprocess.CompletedProcess([], 0, "ok", "")
        with tempfile.TemporaryDirectory() as output_root:
            with patch("code_runner.subprocess.run", return_value=completed) as mocked_run:
                first = code_runner.run_python_block("print('ok')", output_root, timeout=7)
                first_call = mocked_run.call_args
                second = code_runner.run_python_block("print('ok')", output_root, timeout=7)
        self.assertNotEqual(first["run_dir"], second["run_dir"])
        self.assertEqual(first_call.kwargs["timeout"], 7)
        self.assertEqual(first_call.kwargs["cwd"], first["run_dir"])
        self.assertNotIn("LISSAJOUS_LLM_API_KEY", first_call.kwargs["env"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
