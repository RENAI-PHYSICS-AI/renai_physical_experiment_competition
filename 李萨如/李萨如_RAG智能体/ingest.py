from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

import fitz
import joblib
import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer

from config import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    EXPERIMENT_DIR,
    INDEX_DIR,
    REFERENCE_DIR,
    TFIDF_MAX_FEATURES,
    ensure_directories,
)


SPACE_RE = re.compile(r"[\t\u00a0\u3000 ]+")
BLANK_RE = re.compile(r"\n{3,}")
YEAR_RE = re.compile(r"(?:18|19|20)\d{2}")


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(SPACE_RE.sub(" ", line).strip() for line in text.splitlines())
    text = BLANK_RE.sub("\n\n", text)
    return text.strip()


def infer_metadata(path: Path) -> dict:
    stem = path.stem
    year_match = YEAR_RE.search(stem)
    language = "zh" if re.search(r"[\u4e00-\u9fff]", stem) else "en"
    topic = "基础理论"
    lowered = stem.lower()
    if any(key in lowered for key in ("melde", "helmholtz", "chladni")):
        language = "de"
    if any(key in lowered for key in ("mems", "scann", "投影", "图像重建")):
        topic = "扫描与工程应用"
    elif any(key in lowered for key in ("oscilloscope", "示波器", "测频率", "phase")):
        topic = "示波器与相位测量"
    elif any(key in lowered for key in ("pendulum", "摆", "mechanical", "振动")):
        topic = "机械振动与实验"
    elif any(
        key in lowered
        for key in (
            "interpolation",
            "chebyshev",
            "superintegr",
            "orbit",
            "oscillator",
            "semiclassical",
            "doll_ingold",
            "cena_",
        )
    ):
        topic = "数学与动力学拓展"
    elif any(
        key in lowered
        for key in (
            "history",
            "terquem",
            "helmholtz",
            "chladni",
            "fourier_1878",
            "melde_1860",
            "mpiwg",
        )
    ):
        topic = "历史与经典理论"
    return {
        "title": stem.replace("_", " "),
        "year": int(year_match.group()) if year_match else None,
        "language": language,
        "topic": topic,
    }


def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", text) if item.strip()]
    chunks: list[str] = []
    buffer = ""
    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            if buffer:
                chunks.append(buffer)
                buffer = ""
            step = max(1, chunk_size - overlap)
            for start in range(0, len(paragraph), step):
                piece = paragraph[start : start + chunk_size].strip()
                if piece:
                    chunks.append(piece)
                if start + chunk_size >= len(paragraph):
                    break
            continue
        candidate = paragraph if not buffer else f"{buffer}\n\n{paragraph}"
        if len(candidate) <= chunk_size:
            buffer = candidate
        else:
            chunks.append(buffer)
            tail = buffer[-overlap:] if overlap else ""
            buffer = f"{tail}\n\n{paragraph}".strip()
    if buffer:
        chunks.append(buffer)
    return [chunk for chunk in chunks if len(chunk) >= 40]


def chunk_id(source: str, page: int | None, index: int, text: str) -> str:
    raw = f"{source}|{page}|{index}|{text[:120]}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:16]


def extract_pdf(path: Path, chunk_size: int, overlap: int) -> tuple[list[dict], dict]:
    metadata = infer_metadata(path)
    chunks: list[dict] = []
    empty_pages: list[int] = []
    document = fitz.open(path)
    for page_index, page in enumerate(document):
        text = normalize_text(page.get_text("text"))
        page_number = page_index + 1
        if len(text) < 30:
            empty_pages.append(page_number)
            continue
        for local_index, content in enumerate(split_text(text, chunk_size, overlap)):
            chunks.append(
                {
                    "id": chunk_id(path.name, page_number, local_index, content),
                    "source": path.name,
                    "source_type": "pdf",
                    "page": page_number,
                    "chunk": local_index,
                    "text": content,
                    **metadata,
                }
            )
    report = {
        "source": path.name,
        "pages": len(document),
        "chunks": len(chunks),
        "empty_pages": empty_pages,
        "ocr_recommended": len(empty_pages) > max(2, len(document) // 3),
    }
    document.close()
    return chunks, report


def extract_markdown(path: Path, chunk_size: int, overlap: int) -> list[dict]:
    metadata = infer_metadata(path)
    text = path.read_text(encoding="utf-8")
    chunks = []
    for local_index, content in enumerate(split_text(text, chunk_size, overlap)):
        chunks.append(
            {
                "id": chunk_id(path.name, None, local_index, content),
                "source": path.name,
                "source_type": "markdown",
                "page": None,
                "chunk": local_index,
                "text": content,
                **metadata,
            }
        )
    return chunks


def source_files() -> Iterable[Path]:
    melde_ocr = REFERENCE_DIR / "Melde_1860_Erregung_stehender_Wellen_1860_OCR.pdf"
    melde_volume = REFERENCE_DIR / "Melde_1860_Erregung_stehender_Wellen_Annalen_volume.pdf"
    for path in sorted(REFERENCE_DIR.glob("*.pdf")):
        if path == melde_volume and melde_ocr.exists():
            continue
        yield path
    readme = REFERENCE_DIR / "README.md"
    if readme.exists():
        yield readme
    for path in sorted(EXPERIMENT_DIR.rglob("*.md")):
        yield path


def build_index(chunk_size: int, overlap: int) -> dict:
    ensure_directories()
    all_chunks: list[dict] = []
    reports: list[dict] = []
    files = list(source_files())
    for number, path in enumerate(files, start=1):
        print(f"[{number}/{len(files)}] 提取 {path.name}", flush=True)
        try:
            if path.suffix.lower() == ".pdf":
                chunks, report = extract_pdf(path, chunk_size, overlap)
                reports.append(report)
            else:
                chunks = extract_markdown(path, chunk_size, overlap)
            all_chunks.extend(chunks)
        except Exception as exc:
            reports.append({"source": path.name, "error": str(exc), "chunks": 0})
            print(f"  跳过：{exc}", file=sys.stderr)

    if not all_chunks:
        raise RuntimeError("没有提取到可索引文本。")

    corpus = [chunk["text"] for chunk in all_chunks]
    vectorizer = TfidfVectorizer(
        analyzer="char",
        ngram_range=(2, 4),
        min_df=2,
        max_df=0.995,
        max_features=TFIDF_MAX_FEATURES,
        sublinear_tf=True,
        norm="l2",
        dtype=np.float32,
    )
    matrix = vectorizer.fit_transform(corpus)

    chunks_path = INDEX_DIR / "chunks.jsonl"
    with chunks_path.open("w", encoding="utf-8") as handle:
        for chunk in all_chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    joblib.dump(vectorizer, INDEX_DIR / "tfidf_vectorizer.joblib")
    sparse.save_npz(INDEX_DIR / "tfidf_matrix.npz", matrix)
    (INDEX_DIR / "extraction_report.json").write_text(
        json.dumps(reports, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "documents": len(files),
        "pdf_documents": sum(path.suffix.lower() == ".pdf" for path in files),
        "chunks": len(all_chunks),
        "features": int(matrix.shape[1]),
        "chunk_size": chunk_size,
        "chunk_overlap": overlap,
        "retrieval": "character TF-IDF + BM25",
        "ocr_recommended_documents": [
            item["source"] for item in reports if item.get("ocr_recommended")
        ],
    }
    (INDEX_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="构建李萨如文献 RAG 索引")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--overlap", type=int, default=DEFAULT_CHUNK_OVERLAP)
    args = parser.parse_args()
    manifest = build_index(args.chunk_size, args.overlap)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
