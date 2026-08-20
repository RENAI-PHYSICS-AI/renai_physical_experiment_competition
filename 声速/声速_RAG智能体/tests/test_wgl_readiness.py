from __future__ import annotations

import unittest
from pathlib import Path


class WglReadinessContractTests(unittest.TestCase):
    def test_slow_initialization_remains_recoverable(self) -> None:
        app_dir = Path(__file__).resolve().parents[1]
        wrapper = (app_dir / "experiment_embed.py").read_text(encoding="utf-8-sig")
        web = (
            app_dir.parent
            / "声速测量可视化实验说明"
            / "声速四种方法_Julia综合可视化方案"
            / "web"
            / "web.jl"
        ).read_text(encoding="utf-8-sig")

        self.assertIn("sound-speed-wgl-slow", web)
        self.assertIn("window.setTimeout(check, 300)", web)
        self.assertNotIn('send("sound-speed-wgl-failed", "WGLMakie 初始化超过 60 秒")', web)
        self.assertIn("event.data.type === 'sound-speed-wgl-slow'", wrapper)
        self.assertIn("loading.classList.add('hidden')", wrapper)
        self.assertNotIn("clientLog('wrapper-timeout'", wrapper)

    def test_csv_export_uses_persistent_directory_and_clear_controls(self) -> None:
        app_dir = Path(__file__).resolve().parents[1]
        app = (app_dir / "app.py").read_text(encoding="utf-8-sig")
        web = (
            app_dir.parent
            / "声速测量可视化实验说明"
            / "声速四种方法_Julia综合可视化方案"
            / "web"
            / "web.jl"
        ).read_text(encoding="utf-8-sig")

        self.assertIn('get(ENV, "SOUND_SPEED_EXPORT_DIR", "")', web)
        self.assertNotIn('joinpath(LAB_DIR, "output")', web)
        self.assertIn('label = "打开导出文件夹"', web)
        self.assertIn("write_csv_atomic", web)
        self.assertIn("partial-$(time_ns())", web)
        self.assertIn("export_success_status(path)", web)
        self.assertIn("已导出（完整路径）", web)
        self.assertNotIn('status[] = "已导出：$(basename(path))"', web)
        self.assertIn('st.caption(f"CSV 保存位置：{export_location}")', app)


if __name__ == "__main__":
    unittest.main()
