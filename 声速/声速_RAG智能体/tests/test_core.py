from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from config import INDEX_DIR
from ingest import normalize_text, split_text
from tools import calculate_sound_speed, parse_calculation_request


class TextProcessingTests(unittest.TestCase):
    def test_normalize_text(self) -> None:
        self.assertEqual(normalize_text(" 声速  \r\n\r\n 测量 "), "声速\n\n测量")

    def test_chunks_overlap_and_size(self) -> None:
        text = "\n\n".join(["声速测量需要同时记录距离和传播时间。" * 20] * 4)
        chunks = split_text(text, chunk_size=220, overlap=40)
        self.assertGreater(len(chunks), 2)
        self.assertTrue(all(len(chunk) <= 260 for chunk in chunks))


class CalculatorTests(unittest.TestCase):
    def test_echo_method(self) -> None:
        result = calculate_sound_speed("echo", distance=3.43, time_delay=0.02)
        self.assertAlmostEqual(result["speed"], 343.0, places=6)

    def test_dual_microphone_method(self) -> None:
        result = calculate_sound_speed(
            "dual", distance=1.0, time_delay=1.0 / 343.0, angle_degree=0
        )
        self.assertAlmostEqual(result["speed"], 343.0, places=6)

    def test_standing_wave_method(self) -> None:
        result = calculate_sound_speed("standing", frequency=500.0, wavelength=0.686)
        self.assertAlmostEqual(result["speed"], 343.0, places=6)

    def test_parse_echo_request(self) -> None:
        result = parse_calculation_request("回声法：距离 d=3.43 m，时间差 Δt=20 ms")
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["speed"], 343.0, places=3)


@unittest.skipUnless((INDEX_DIR / "manifest.json").exists(), "知识库索引尚未构建")
class RetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from retrieval import HybridRetriever

        cls.retriever = HybridRetriever()

    def test_echo_query(self) -> None:
        hits = self.retriever.search("回声法测量空气中的声速", top_k=5)
        self.assertTrue(any(hit.chunk["topic"] == "时间差与回声法" for hit in hits))

    def test_standing_wave_query(self) -> None:
        hits = self.retriever.search("Kundt 管驻波波节间距", top_k=5)
        self.assertTrue(any(hit.chunk["topic"] == "驻波与共振法" for hit in hits))


if __name__ == "__main__":
    unittest.main()
