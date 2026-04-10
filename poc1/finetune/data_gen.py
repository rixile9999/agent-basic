"""
파인튜닝 학습 데이터 생성

파이프라인:
1. 기존 100개 NL 쿼리를 qwen-plus로 10배 다양화 → ~1,000개
2. qwen-max로 각 NL의 Wide DSL 생성 (교사)
3. DSL 파서로 검증 — Function Call이 ground truth와 일치하는 것만 선별
4. DashScope SFT 포맷 JSONL 저장

사용법:
  uv run python -m poc1.finetune.data_gen
"""
import asyncio
import json
import logging
import os
from pathlib import Path

from openai import AsyncOpenAI

from poc1.config import DASHSCOPE_BASE_URL, MAX_CONCURRENT, RESULTS_DIR
from poc1.dataset.queries import QUERIES
from poc1.dsl.parser import parse_wide
from poc1.eval.metrics import _arg_equal
from poc1.methods.method_b import _build_system_prompt
from poc1.models import NLQuery

log = logging.getLogger(__name__)

OUTPUT_DIR = RESULTS_DIR.parent / "finetune"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TRAIN_FILE = OUTPUT_DIR / "train.jsonl"
STATS_FILE = OUTPUT_DIR / "data_stats.json"

DSL_SYSTEM_PROMPT = _build_system_prompt("wide")


# ── Step 1: NL 쿼리 다양화 ────────────────────────────────────────────────────

_PARAPHRASE_PROMPT = """\
아래 한국어 스마트홈 명령어를 {n}가지 다른 표현으로 바꿔줘.
같은 의미지만 다른 어휘·어순·존댓말·구어체를 사용해.
JSON 배열로만 답해: ["표현1", "표현2", ...]

원본: {nl}
"""


async def paraphrase(nl: str, n: int, client: AsyncOpenAI, semaphore: asyncio.Semaphore) -> list[str]:
    async with semaphore:
        try:
            resp = await client.chat.completions.create(
                model="qwen-plus",
                messages=[{"role": "user", "content": _PARAPHRASE_PROMPT.format(nl=nl, n=n)}],
                response_format={"type": "json_object"},
                temperature=0.9,
            )
            raw = resp.choices[0].message.content or "[]"
            # JSON 배열 또는 {"result": [...]} 형태 모두 처리
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(x) for x in parsed[:n]]
            # dict면 첫 번째 list 값 추출
            for v in parsed.values():
                if isinstance(v, list):
                    return [str(x) for x in v[:n]]
        except Exception as e:
            log.warning(f"paraphrase 실패 ({nl[:20]}...): {e}")
    return []


# ── Step 2: Wide DSL 생성 ─────────────────────────────────────────────────────

async def generate_dsl(nl: str, client: AsyncOpenAI, semaphore: asyncio.Semaphore) -> dict | None:
    from poc1.dsl.schemas.loader import load_schema
    schema = load_schema("wide")
    async with semaphore:
        try:
            resp = await client.chat.completions.create(
                model="qwen-max",
                messages=[
                    {"role": "system", "content": DSL_SYSTEM_PROMPT},
                    {"role": "user", "content": nl},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "wide_dsl", "schema": schema, "strict": True},
                },
            )
            raw = resp.choices[0].message.content or ""
            return json.loads(raw)
        except Exception as e:
            log.warning(f"DSL 생성 실패 ({nl[:20]}...): {e}")
    return None


# ── Step 3: 검증 ──────────────────────────────────────────────────────────────

def validate(dsl: dict, query: NLQuery) -> bool:
    """DSL → FunctionCall 변환 후 ground truth와 비교."""
    try:
        pred = parse_wide(dsl)
    except Exception:
        return False
    gt = query.ground_truth
    if pred.name != gt.name:
        return False
    # required 인자 모두 일치해야 통과
    for k, v in gt.arguments.items():
        if not _arg_equal(pred.arguments.get(k), v):
            return False
    return True


# ── Step 4: JSONL 생성 ────────────────────────────────────────────────────────

def to_jsonl_record(nl: str, dsl: dict) -> dict:
    """DashScope SFT JSONL 포맷으로 변환."""
    return {
        "messages": [
            {"role": "system", "content": DSL_SYSTEM_PROMPT},
            {"role": "user", "content": nl},
            {"role": "assistant", "content": json.dumps(dsl, ensure_ascii=False)},
        ]
    }


# ── 메인 ──────────────────────────────────────────────────────────────────────

async def run(
    api_key: str,
    paraphrase_n: int = 9,   # 원본 1개 + 변형 9개 = 쿼리당 10개
    max_concurrent: int = MAX_CONCURRENT,
) -> Path:
    client = AsyncOpenAI(api_key=api_key, base_url=DASHSCOPE_BASE_URL)
    sem = asyncio.Semaphore(max_concurrent)

    # ── 1. 다양화 ─────────────────────────────────────────────────────────────
    log.info(f"[1/3] NL 다양화 시작 ({len(QUERIES)}개 × {paraphrase_n}변형)")
    para_tasks = [paraphrase(q.nl, paraphrase_n, client, sem) for q in QUERIES]
    para_results = await asyncio.gather(*para_tasks)

    nl_query_pairs: list[tuple[str, NLQuery]] = []
    for query, variants in zip(QUERIES, para_results):
        nl_query_pairs.append((query.nl, query))          # 원본
        for v in variants:
            nl_query_pairs.append((v, query))             # 변형

    log.info(f"  → 총 {len(nl_query_pairs)}개 NL 생성")

    # ── 2. DSL 생성 ───────────────────────────────────────────────────────────
    log.info(f"[2/3] qwen-max 교사로 Wide DSL 생성 중...")
    from tqdm.asyncio import tqdm as atqdm
    dsl_results: list[dict | None] = await atqdm.gather(
        *[generate_dsl(nl, client, sem) for nl, _ in nl_query_pairs],
        desc="DSL 생성",
        unit="req",
    )
    log.info(f"  → DSL 생성 완료: {sum(1 for d in dsl_results if d)} / {len(dsl_results)}")

    # ── 3. 검증 + JSONL 저장 ─────────────────────────────────────────────────
    log.info("[3/3] 검증 및 JSONL 저장 중...")
    records = []
    stats = {"total": len(nl_query_pairs), "dsl_generated": 0, "validated": 0, "rejected": 0}

    for (nl, query), dsl in zip(nl_query_pairs, dsl_results):
        if dsl is None:
            stats["rejected"] += 1
            continue
        stats["dsl_generated"] += 1
        if validate(dsl, query):
            records.append(to_jsonl_record(nl, dsl))
            stats["validated"] += 1
        else:
            stats["rejected"] += 1

    TRAIN_FILE.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records),
        encoding="utf-8",
    )
    STATS_FILE.write_text(json.dumps(stats, indent=2, ensure_ascii=False))

    log.info(f"  → 검증 통과: {stats['validated']} / {stats['total']}")
    log.info(f"  → 저장 완료: {TRAIN_FILE}")
    return TRAIN_FILE


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not api_key:
        raise SystemExit("DASHSCOPE_API_KEY 환경변수 필요")
    asyncio.run(run(api_key))
