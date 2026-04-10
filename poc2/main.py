"""
POC 2 실험 CLI 진입점 — 코인 트레이딩 NL → DSL → Function Call

사용법:
  # 전체 실험 (모든 모델 × 모든 방식)
  python -m poc2.main

  # 빠른 smoke test (qwen-turbo, simple 쿼리만)
  python -m poc2.main --smoke

  # 특정 모델만
  python -m poc2.main --model qwen-turbo --model qwen-plus

  # Method A 만
  python -m poc2.main --method a

  # DSL 폭 지정
  python -m poc2.main --method b --width medium --width wide
"""
import argparse
import asyncio
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="POC 2: 코인 트레이딩 NL→DSL→Function vs NL→Function 비교")
    p.add_argument("--smoke", action="store_true",
                   help="빠른 smoke test: qwen-turbo + simple 쿼리 10 개")
    p.add_argument("--model", dest="models", action="append",
                   help="사용할 모델 (반복 가능). 기본: config.MODELS 전체")
    p.add_argument("--method", choices=["a", "b", "all"], default="all",
                   help="실행할 방식 (a=직접, b=DSL, all=둘 다)")
    p.add_argument("--width", dest="widths", action="append",
                   choices=["narrow", "medium", "wide"],
                   help="DSL 폭 (반복 가능). 기본: 전체")
    p.add_argument("--tag", default="", help="결과 파일명 태그")
    p.add_argument("--no-save", action="store_true", help="결과 파일 저장 안 함")
    return p.parse_args()


async def main() -> None:
    args = parse_args()

    api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not api_key:
        print("오류: DASHSCOPE_API_KEY 환경변수가 설정되지 않았습니다.")
        sys.exit(1)

    from poc2.config import MODELS, DSL_WIDTHS
    from poc2.dataset.queries import QUERIES, QUERIES_BY_DIFFICULTY
    from poc2.eval.runner import print_summary, run_all, save_results

    # 옵션 결정
    models = args.models or MODELS
    widths = args.widths or DSL_WIDTHS
    include_a = args.method in ("a", "all")
    include_b = args.method in ("b", "all")

    if args.smoke:
        # 4 방식 × 3 모델 × 10 쿼리 = 120 회
        queries = (
            QUERIES_BY_DIFFICULTY["simple"][:4]
            + QUERIES_BY_DIFFICULTY["medium"][:3]
            + QUERIES_BY_DIFFICULTY["complex"][:3]
        )
        print(f"[Smoke Test] 모델: {models}, 쿼리: {len(queries)}개 (s4/m3/c3), DSL 폭: {widths}")
    else:
        queries = QUERIES
        n_methods = (1 if include_a else 0) + (len(widths) if include_b else 0)
        total_calls = n_methods * len(models) * len(queries)
        print(f"[Full Experiment] 모델: {models}, 쿼리: {len(queries)}개, DSL 폭: {widths}")
        print(f"  → 총 API 호출 예정: {total_calls}회 ({n_methods}방식 × {len(models)}모델 × {len(queries)}쿼리)")

    data = await run_all(
        api_key=api_key,
        models=models,
        dsl_widths=widths,
        queries=queries,
        include_method_a=include_a,
        include_method_b=include_b,
    )

    print_summary(data["summary"])

    if not args.no_save:
        path = save_results(data, tag=args.tag or ("smoke" if args.smoke else ""))
        print(f"\n결과 저장됨: {path}")


if __name__ == "__main__":
    asyncio.run(main())
