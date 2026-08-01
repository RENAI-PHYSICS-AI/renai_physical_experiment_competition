from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from ingest import normalize_text, split_text
from retrieval import HybridRetriever, index_status, tokenize
from tools import calculate_lissajous, parse_calculation_request


class TextProcessingTests(unittest.TestCase):
    def test_normalize_text(self):
        self.assertEqual(normalize_text("  相位   差\r\n\r\n\r\n频率比  "), "相位 差\n\n频率比")

    def test_chunks_overlap_and_size(self):
        text = "\n\n".join(["李萨如图形由两个垂直振动合成。" * 20] * 4)
        chunks = split_text(text, chunk_size=180, overlap=30)
        self.assertGreaterEqual(len(chunks), 4)
        self.assertTrue(all(len(chunk) <= 240 for chunk in chunks))

    def test_chinese_tokenization(self):
        tokens = tokenize("相位差与 frequency ratio")
        self.assertIn("相位", tokens)
        self.assertIn("frequency", tokens)


class CalculatorTests(unittest.TestCase):
    def test_equal_frequency_circle(self):
        result = calculate_lissajous(2.0, 2.0, 90.0, 1.0, 1.0)
        self.assertEqual(result["shape"], "圆")
        self.assertEqual(result["ratio"], "1:1")
        self.assertAlmostEqual(result["close_period"], 0.5)

    def test_rational_ratio(self):
        result = calculate_lissajous(2.0, 3.0, 30.0)
        self.assertEqual(result["ratio"], "2:3")
        self.assertTrue(result["closed"])
        self.assertAlmostEqual(result["close_period"], 1.0)

    def test_parse_request(self):
        result = parse_calculation_request("请计算 fx=2 Hz、fy=3 Hz、相位差=60 度")
        self.assertIsNotNone(result)
        self.assertEqual(result["ratio"], "2:3")


@unittest.skipUnless(index_status().get("ready"), "知识库索引尚未构建")
class RetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.retriever = HybridRetriever()

    def test_phase_query(self):
        hits = self.retriever.search("如何用李萨如图形测量相位差", top_k=5)
        self.assertGreaterEqual(len(hits), 3)
        self.assertTrue(any("相位" in hit.chunk["text"] for hit in hits))

    def test_frequency_ratio_query(self):
        hits = self.retriever.search("频率比与轨迹闭合条件", top_k=5)
        self.assertGreaterEqual(len(hits), 3)

    def test_frequency_ratio_query_excludes_unrelated_holography_page(self):
        hits = self.retriever.search("频率比为2:3时轨迹为什么闭合", top_k=6)
        locations = {(hit.chunk["source"], hit.chunk.get("page")) for hit in hits}
        self.assertFalse(any("UESTC" in source and page == 22 for source, page in locations))
        self.assertTrue(
            any("共同周期" in hit.chunk["text"] or "有理" in hit.chunk["text"] for hit in hits)
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
