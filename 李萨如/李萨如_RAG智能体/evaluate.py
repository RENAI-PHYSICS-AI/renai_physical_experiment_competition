from __future__ import annotations

import json
from pathlib import Path

from retrieval import HybridRetriever


def main() -> None:
    project_dir = Path(__file__).resolve().parent
    questions = json.loads(
        (project_dir / "tests" / "evaluation_questions.json").read_text(encoding="utf-8")
    )
    retriever = HybridRetriever()
    matched = 0
    for item in questions:
        hits = retriever.search(item["question"], top_k=5)
        topics = {hit.chunk.get("topic") for hit in hits}
        success = item["topic"] in topics
        matched += int(success)
        marker = "PASS" if success else "MISS"
        best = hits[0].citation if hits else "无结果"
        print(f"[{marker}] {item['question']}\n       首条：{best}")
    ratio = matched / len(questions) if questions else 0.0
    print(f"\n主题命中率：{matched}/{len(questions)} = {ratio:.1%}")
    if ratio < 0.7:
        raise SystemExit("检索评估未达到 70% 基线。")


if __name__ == "__main__":
    main()

