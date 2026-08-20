from __future__ import annotations

import unittest
from pathlib import Path


class WglReadinessContractTests(unittest.TestCase):
    def test_slow_initialization_remains_recoverable(self) -> None:
        app_dir = Path(__file__).resolve().parents[1]
        wrapper = (app_dir / "experiment_embed.py").read_text(encoding="utf-8-sig")
        web = (
            app_dir.parent
            / "李萨如图形可视化实验说明"
            / "实验一至四_Julia综合可视化方案"
            / "web.jl"
        ).read_text(encoding="utf-8-sig")

        self.assertIn("lissajous-wgl-slow", web)
        self.assertIn("window.setTimeout(check, 300)", web)
        self.assertIn(".wglmakie-spinner", web)
        self.assertIn("visibility: hidden !important", web)
        self.assertIn("if (canvas && !spinner)", web)
        self.assertNotIn("WGLMakie/Bonito 初始化超过 45 秒", web)
        self.assertIn("event.data.type === 'lissajous-wgl-slow'", wrapper)
        self.assertIn("loading.classList.add('hidden')", wrapper)
        self.assertNotIn("clientLog('wrapper-timeout'", wrapper)

    def test_all_four_routes_have_persistent_csv_export(self) -> None:
        app_dir = Path(__file__).resolve().parents[1]
        app = (app_dir / "app.py").read_text(encoding="utf-8-sig")
        web = (
            app_dir.parent
            / "李萨如图形可视化实验说明"
            / "实验一至四_Julia综合可视化方案"
            / "web.jl"
        ).read_text(encoding="utf-8-sig")

        self.assertIn('get(ENV, "LISSAJOUS_EXPORT_DIR", "")', web)
        self.assertIn('label = "导出 CSV"', web)
        self.assertIn('label = "打开导出文件夹"', web)
        self.assertIn("write_experiment_csv_atomic", web)
        self.assertIn("partial-$(time_ns())", web)
        for slug in ("phase", "amplitude", "ratio", "detune"):
            self.assertIn(f'attach_csv_export!(motion_grid, analysis, "{slug}")', web)
        self.assertIn('"distance_to_start"', web)
        self.assertIn('"relative_phase_rad"', web)
        self.assertIn('st.caption(f"CSV 保存位置：{export_location}")', app)


if __name__ == "__main__":
    unittest.main()
