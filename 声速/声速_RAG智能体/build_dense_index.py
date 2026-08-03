from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

import numpy as np
from sentence_transformers import SentenceTransformer

from config import INDEX_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description="为声速测量知识库构建稠密语义向量")
    parser.add_argument(
        "--model",
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    parser.add_argument("--batch-size", type=int, default=24)
    args = parser.parse_args()

    chunks_path = INDEX_DIR / "chunks.jsonl"
    if not chunks_path.exists():
        raise FileNotFoundError("请先运行 ingest.py 构建基础索引。")
    with chunks_path.open("r", encoding="utf-8") as handle:
        chunks = [json.loads(line) for line in handle if line.strip()]

    model = SentenceTransformer(args.model)
    embeddings = model.encode(
        [chunk["text"] for chunk in chunks],
        batch_size=args.batch_size,
        normalize_embeddings=True,
        show_progress_bar=True,
    ).astype(np.float32)
    np.save(INDEX_DIR / "dense_embeddings.npy", embeddings)
    (INDEX_DIR / "dense_manifest.json").write_text(
        json.dumps(
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "model": args.model,
                "chunks": len(chunks),
                "dimensions": int(embeddings.shape[1]),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"稠密向量已构建：{embeddings.shape}")


if __name__ == "__main__":
    main()
