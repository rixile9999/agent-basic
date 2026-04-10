"""
POC 2 설정 — 코인 트레이딩 자연어 → DSL → Function Call 실험
"""
import os
from pathlib import Path

ROOT = Path(__file__).parent
DSL_SCHEMA_DIR = ROOT / "dsl" / "schemas"
RESULTS_DIR = ROOT / "results"

DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

MODELS = ["qwen-turbo", "qwen-plus", "qwen-max"]
DSL_WIDTHS = ["medium", "wide"]

MAX_CONCURRENT = 5
MAX_RETRIES = 3
RETRY_DELAY = 1.0
