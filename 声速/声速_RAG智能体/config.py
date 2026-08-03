from __future__ import annotations

import os
from pathlib import Path


PROJECT_DIR = Path(
    os.getenv("SOUND_SPEED_APP_DIR", Path(__file__).resolve().parent)
).resolve()
SOUND_SPEED_DIR = PROJECT_DIR.parent
WORKSPACE_DIR = SOUND_SPEED_DIR.parent
REFERENCE_DIR = SOUND_SPEED_DIR / "ref"
EXPERIMENT_DIR = SOUND_SPEED_DIR / "声速测量可视化实验说明"
INDEX_DIR = PROJECT_DIR / "data" / "index"
PROMPT_PATH = PROJECT_DIR / "prompts" / "system.md"

JULIA_DESKTOP_PROJECT_DIR = EXPERIMENT_DIR / "声速四种方法_Julia综合可视化方案"
JULIA_PROJECT_DIR = Path(
    os.getenv(
        "SOUND_SPEED_JULIA_PROJECT_DIR",
        JULIA_DESKTOP_PROJECT_DIR / "web",
    )
).resolve()
JULIA_RUN_PATH = JULIA_DESKTOP_PROJECT_DIR / "run.jl"
JULIA_WEB_PATH = JULIA_PROJECT_DIR / "web.jl"
JULIA_WEB_HOST = os.getenv("SOUND_SPEED_WEB_HOST", "127.0.0.1")
JULIA_WEB_PORT = int(os.getenv("SOUND_SPEED_WEB_PORT", "9385"))
JULIA_WEB_BROWSER_HOST = os.getenv("SOUND_SPEED_WEB_BROWSER_HOST", "127.0.0.1")
JULIA_WEB_URL = f"http://{JULIA_WEB_BROWSER_HOST}:{JULIA_WEB_PORT}"

DEFAULT_TOP_K = 6
DEFAULT_CHUNK_SIZE = 760
DEFAULT_CHUNK_OVERLAP = 120
TFIDF_MAX_FEATURES = 60_000

LLM_BASE_URL = os.getenv(
    "SOUND_SPEED_LLM_BASE_URL",
    "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/chat/completions",
)
LLM_MODEL = os.getenv("SOUND_SPEED_LLM_MODEL", "qwen3.7-plus")
LLM_API_KEY = os.getenv("SOUND_SPEED_LLM_API_KEY", "")


def ensure_directories() -> None:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
