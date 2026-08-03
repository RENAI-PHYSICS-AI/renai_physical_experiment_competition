from __future__ import annotations

import json
import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
from scipy import sparse

from config import DEFAULT_TOP_K, INDEX_DIR


LATIN_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]+")
HAN_SEQUENCE_RE = re.compile(r"[\u4e00-\u9fff]+")
MIN_RELATIVE_SCORE = 0.55

QUERY_EXPANSIONS = {
    "回声": "echo time of flight round trip reflection delay 声程 时间延迟",
    "时间差": "time of flight delay cross correlation 双麦克风 采样率",
    "双麦克风": "stereo microphone time delay cross correlation projected distance",
    "互相关": "cross correlation lag peak sample rate time delay",
    "相位差": "phase comparison wrapped phase wavelength oscilloscope ultrasound",
    "示波器": "oscilloscope phase comparison dual channel wavelength sound speed",
    "驻波": "standing wave nodes antinodes Kundt tube resonance wavelength",
    "共振": "resonance tube Kundt standing wave wavelength frequency",
    "温度": "temperature dependence ideal gas adiabatic Laplace speed of sound",
    "水中声速": "velocity of sound in water Colladon Sturm ultrasound phase",
    "历史": "Laplace Kundt Regnault Colladon history velocity of sound",
    "kundt": "Kundt tube standing wave nodes sound velocity gas solid",
    "colladon": "Colladon Sturm Lake Geneva velocity of sound in water",
}

QUERY_TOPIC_KEYWORDS = {
    "时间差与回声法": ("回声", "时间差", "飞行时间", "双麦克风", "互相关", "time of flight"),
    "相位与超声测量": ("相位差", "示波器", "超声", "水中声速", "phase", "ultrasound"),
    "驻波与共振法": ("驻波", "共振", "波节", "波腹", "kundt", "管长"),
    "历史与经典实验": ("历史", "经典", "laplace", "kundt", "regnault", "colladon", "马大猷"),
    "现代声学拓展": ("超材料", "吸声", "时间反演", "布里渊", "metamaterial"),
    "声速基础理论": ("绝热", "比热比", "温度", "湿度", "理想气体", "声速公式"),
    "综合实验与教学": ("实验设计", "误差", "可视化", "教学", "数据处理"),
}


def expand_query(query: str) -> str:
    lowered = query.lower()
    additions = [value for key, value in QUERY_EXPANSIONS.items() if key in lowered]
    return f"{query} {' '.join(additions)}".strip()


def detect_query_topics(query: str) -> set[str]:
    lowered = query.lower()
    return {
        topic
        for topic, keywords in QUERY_TOPIC_KEYWORDS.items()
        if any(keyword in lowered for keyword in keywords)
    }


def tokenize(text: str) -> list[str]:
    lowered = text.lower()
    latin = LATIN_WORD_RE.findall(lowered)
    han_tokens: list[str] = []
    for sequence in HAN_SEQUENCE_RE.findall(lowered):
        if len(sequence) == 1:
            han_tokens.append(sequence)
        else:
            han_tokens.extend(sequence[index : index + 2] for index in range(len(sequence) - 1))
    return latin + han_tokens


@dataclass(frozen=True)
class SearchHit:
    score: float
    vector_score: float
    bm25_score: float
    chunk: dict

    @property
    def citation(self) -> str:
        page = self.chunk.get("page")
        location = f"p.{page}" if page else "文档"
        return f"{self.chunk['source']}，{location}"

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "vector_score": self.vector_score,
            "bm25_score": self.bm25_score,
            "citation": self.citation,
            **self.chunk,
        }


class HybridRetriever:
    def __init__(self, index_dir: Path = INDEX_DIR):
        self.index_dir = Path(index_dir)
        self.chunks = self._load_chunks()
        self.vectorizer = joblib.load(self.index_dir / "tfidf_vectorizer.joblib")
        self.matrix = sparse.load_npz(self.index_dir / "tfidf_matrix.npz").tocsr()
        if self.matrix.shape[0] != len(self.chunks):
            raise RuntimeError("索引矩阵与文本块数量不一致，请重新构建知识库。")
        self.doc_tokens = [tokenize(chunk["text"]) for chunk in self.chunks]
        self.doc_lengths = np.asarray([len(tokens) for tokens in self.doc_tokens], dtype=np.float32)
        self.avg_doc_length = float(np.mean(self.doc_lengths)) if len(self.doc_lengths) else 1.0
        document_frequency: Counter[str] = Counter()
        for tokens in self.doc_tokens:
            document_frequency.update(set(tokens))
        count = len(self.doc_tokens)
        self.idf = {
            token: math.log(1.0 + (count - freq + 0.5) / (freq + 0.5))
            for token, freq in document_frequency.items()
        }
        self.dense_model = None
        self.dense_matrix = None
        dense_manifest = self.index_dir / "dense_manifest.json"
        dense_matrix = self.index_dir / "dense_embeddings.npy"
        if (
            os.getenv("SOUND_SPEED_DENSE_ENABLED", "true").lower() not in {"0", "false", "no"}
            and dense_manifest.exists()
            and dense_matrix.exists()
        ):
            try:
                from sentence_transformers import SentenceTransformer

                dense_config = json.loads(dense_manifest.read_text(encoding="utf-8"))
                self.dense_model = SentenceTransformer(dense_config["model"])
                self.dense_matrix = np.load(dense_matrix, mmap_mode="r")
                if self.dense_matrix.shape[0] != len(self.chunks):
                    self.dense_model = None
                    self.dense_matrix = None
            except (ImportError, OSError, KeyError, ValueError):
                self.dense_model = None
                self.dense_matrix = None

    def _load_chunks(self) -> list[dict]:
        path = self.index_dir / "chunks.jsonl"
        if not path.exists():
            raise FileNotFoundError("知识库尚未构建，请先运行 ingest.py。")
        with path.open("r", encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def _bm25(self, query: str) -> np.ndarray:
        query_tokens = tokenize(query)
        scores = np.zeros(len(self.doc_tokens), dtype=np.float32)
        if not query_tokens:
            return scores
        k1 = 1.5
        b = 0.75
        for index, tokens in enumerate(self.doc_tokens):
            frequencies = Counter(tokens)
            length_norm = k1 * (1 - b + b * self.doc_lengths[index] / self.avg_doc_length)
            score = 0.0
            for token in query_tokens:
                frequency = frequencies.get(token, 0)
                if frequency:
                    score += self.idf.get(token, 0.0) * (
                        frequency * (k1 + 1) / (frequency + length_norm)
                    )
            scores[index] = score
        return scores

    @staticmethod
    def _normalize(scores: np.ndarray) -> np.ndarray:
        maximum = float(np.max(scores)) if len(scores) else 0.0
        return scores / maximum if maximum > 0 else scores

    def search(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        language: str | None = None,
        topic: str | None = None,
    ) -> list[SearchHit]:
        expanded_query = expand_query(query)
        query_vector = self.vectorizer.transform([expanded_query])
        vector_scores = (self.matrix @ query_vector.T).toarray().ravel().astype(np.float32)
        bm25_scores = self._bm25(expanded_query)
        if self.dense_model is not None and self.dense_matrix is not None:
            dense_query = self.dense_model.encode(
                [query], normalize_embeddings=True, show_progress_bar=False
            )[0]
            dense_scores = np.asarray(self.dense_matrix @ dense_query, dtype=np.float32)
            combined = (
                0.48 * self._normalize(dense_scores)
                + 0.34 * self._normalize(vector_scores)
                + 0.18 * self._normalize(bm25_scores)
            )
        else:
            combined = 0.68 * self._normalize(vector_scores) + 0.32 * self._normalize(bm25_scores)
        topic_hints = detect_query_topics(query)
        if topic_hints:
            topic_bonus = np.asarray(
                [0.14 if chunk.get("topic") in topic_hints else 0.0 for chunk in self.chunks],
                dtype=np.float32,
            )
            combined = combined + topic_bonus

        candidates = np.argsort(-combined)
        best_score = float(combined[candidates[0]]) if len(candidates) else 0.0
        minimum_score = best_score * MIN_RELATIVE_SCORE
        hits: list[SearchHit] = []
        source_counts: Counter[str] = Counter()
        seen_locations: set[tuple[str, int | None]] = set()
        for index in candidates:
            if combined[index] < minimum_score or combined[index] <= 0:
                break
            chunk = self.chunks[int(index)]
            if language and language != "全部" and chunk.get("language") != language:
                continue
            if topic and topic != "全部" and chunk.get("topic") != topic:
                continue
            source = chunk["source"]
            location = (source, chunk.get("page"))
            if source_counts[source] >= 1 or location in seen_locations:
                continue
            hits.append(
                SearchHit(
                    score=float(combined[index]),
                    vector_score=float(vector_scores[index]),
                    bm25_score=float(bm25_scores[index]),
                    chunk=chunk,
                )
            )
            source_counts[source] += 1
            seen_locations.add(location)
            if len(hits) >= top_k:
                break
        return hits

    def topics(self) -> list[str]:
        return sorted({chunk.get("topic", "未分类") for chunk in self.chunks})

    @staticmethod
    def format_context(hits: list[SearchHit], max_chars: int = 6200) -> str:
        sections = []
        used = 0
        for number, hit in enumerate(hits, start=1):
            text = hit.chunk["text"].strip()
            block = f"[S{number}] {hit.citation}\n{text}"
            if used + len(block) > max_chars:
                remaining = max_chars - used
                if remaining > 180:
                    sections.append(block[:remaining] + "...")
                break
            sections.append(block)
            used += len(block)
        return "\n\n---\n\n".join(sections)


def index_status(index_dir: Path = INDEX_DIR) -> dict:
    manifest_path = Path(index_dir) / "manifest.json"
    if not manifest_path.exists():
        return {"ready": False, "message": "知识库尚未构建"}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {"ready": True, **manifest}
