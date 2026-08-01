from __future__ import annotations

import os
from pathlib import Path


PROJECT_DIR = Path(os.getenv("LISSAJOUS_APP_DIR", Path(__file__).resolve().parent)).resolve()
LISSAJOUS_DIR = PROJECT_DIR.parent
WORKSPACE_DIR = LISSAJOUS_DIR.parent
REFERENCE_DIR = LISSAJOUS_DIR / "ref"
EXPERIMENT_DIR = LISSAJOUS_DIR / "李萨如图形可视化实验说明"
INDEX_DIR = PROJECT_DIR / "data" / "index"
PROMPT_PATH = PROJECT_DIR / "prompts" / "system.md"

JULIA_PROJECT_DIR = Path(
    os.getenv(
        "LISSAJOUS_JULIA_PROJECT_DIR",
        EXPERIMENT_DIR / "实验一至四_Julia综合可视化方案",
    )
).resolve()
JULIA_RUN_PATH = JULIA_PROJECT_DIR / "run.jl"
JULIA_WEB_PATH = JULIA_PROJECT_DIR / "web.jl"
JULIA_WEB_HOST = os.getenv("LISSAJOUS_WEB_HOST", "127.0.0.1")
JULIA_WEB_PORT = int(os.getenv("LISSAJOUS_WEB_PORT", "9384"))
JULIA_WEB_URL = f"http://{JULIA_WEB_HOST}:{JULIA_WEB_PORT}"

DEFAULT_TOP_K = 6
DEFAULT_CHUNK_SIZE = 760
DEFAULT_CHUNK_OVERLAP = 120
TFIDF_MAX_FEATURES = 60_000

LLM_BASE_URL = os.getenv(
    "LISSAJOUS_LLM_BASE_URL",
    "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/chat/completions",
)
LLM_MODEL = os.getenv("LISSAJOUS_LLM_MODEL", "qwen3.7-plus")
LLM_API_KEY = os.getenv("LISSAJOUS_LLM_API_KEY", "")


def ensure_directories() -> None:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
