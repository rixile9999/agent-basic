"""실험 러너 — poc1과 동일 구조"""
import asyncio
import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from poc2.config import MAX_CONCURRENT, MODELS, DSL_WIDTHS, RESULTS_DIR
from poc2.dataset.queries import QUERIES
from poc2.eval.metrics import aggregate, evaluate
from poc2.methods.method_a import run_method_a
from poc2.methods.method_b import run_method_b
from poc2.models import EvalResult, MethodResult, NLQuery

log = logging.getLogger(__name__)


async def run_all(
    *,
    api_key: str,
    models: list[str] | None = None,
    dsl_widths: list[str] | None = None,
    queries: list[NLQuery] | None = None,
    include_method_a: bool = True,
    include_method_b: bool = True,
) -> dict:
    _models = models or MODELS
    _widths = dsl_widths or DSL_WIDTHS
    _queries = queries or QUERIES

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    tasks = []

    if include_method_a:
        for model in _models:
            for query in _queries:
                tasks.append(run_method_a(query, model=model, api_key=api_key, semaphore=semaphore))

    if include_method_b:
        for model in _models:
            for width in _widths:
                for query in _queries:
                    tasks.append(run_method_b(query, width=width, model=model, api_key=api_key, semaphore=semaphore))

    log.info(f"총 {len(tasks)}개 태스크 (모델: {_models}, 쿼리: {len(_queries)}개)")

    from tqdm.asyncio import tqdm as atqdm
    method_results: list[MethodResult] = []
    with atqdm(total=len(tasks), desc="실험 진행", unit="call") as bar:
        for coro in asyncio.as_completed(tasks):
            result = await coro
            method_results.append(result)
            bar.update(1)
            if result.error:
                bar.write(f"  [에러] {result.query_id}/{result.method}/{result.model}: {result.error[:60]}")

    from poc2.dataset.queries import QUERY_MAP
    eval_results: list[EvalResult] = []
    for mr in method_results:
        query = QUERY_MAP.get(mr.query_id)
        if query:
            eval_results.append(evaluate(mr, query))

    summary = aggregate(eval_results)

    return {
        "raw": [asdict(r) for r in eval_results],
        "summary": summary,
        "meta": {
            "models": _models,
            "dsl_widths": _widths,
            "n_queries": len(_queries),
            "n_tasks": len(tasks),
            "timestamp": datetime.now().isoformat(),
        },
    }


def save_results(data: dict, tag: str = "") -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"results_{ts}{'_' + tag if tag else ''}.json"
    path = RESULTS_DIR / fname
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    log.info(f"결과 저장: {path}")
    return path


def print_summary(summary: dict) -> None:
    header = f"{'조건':<40} {'EM%':>6} {'FN%':>6} {'ARG%':>6} {'토큰↓':>8} {'지연(ms)':>10}"
    print("\n" + "=" * len(header))
    print(header)
    print("-" * len(header))
    top_keys = [k for k in summary if k.count("__") == 1]
    for k in sorted(top_keys):
        s = summary[k]
        print(
            f"{k:<40} "
            f"{s['exact_match_rate']*100:>5.1f}% "
            f"{s['function_name_acc']*100:>5.1f}% "
            f"{s['avg_argument_match']*100:>5.1f}% "
            f"{s['avg_input_tokens']+s['avg_output_tokens']:>8.0f} "
            f"{s['avg_latency_ms']:>9.0f}ms"
        )
    print("=" * len(header))
