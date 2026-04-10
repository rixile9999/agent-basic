"""
평가 메트릭 계산
"""
from poc1.models import EvalResult, MethodResult, NLQuery


def evaluate(result: MethodResult, query: NLQuery) -> EvalResult:
    """MethodResult + ground truth → EvalResult."""
    gt = query.ground_truth
    pred = result.predicted

    if pred is None:
        return EvalResult(
            query_id=query.id,
            method=result.method,
            model=result.model,
            exact_match=False,
            function_name_match=False,
            argument_match_ratio=0.0,
            dsl_valid=result.dsl_valid,
            latency_ms=result.latency_ms,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            error=result.error,
            dsl_output=result.dsl_output,
        )

    fn_match = pred.name == gt.name

    # argument match ratio: gt의 required 인자 기준
    gt_args = gt.arguments
    pred_args = pred.arguments or {}
    if not gt_args:
        arg_ratio = 1.0
    else:
        matched = sum(
            1 for k, v in gt_args.items()
            if _arg_equal(pred_args.get(k), v)
        )
        arg_ratio = matched / len(gt_args)

    exact = fn_match and arg_ratio == 1.0

    return EvalResult(
        query_id=query.id,
        method=result.method,
        model=result.model,
        exact_match=exact,
        function_name_match=fn_match,
        argument_match_ratio=arg_ratio,
        dsl_valid=result.dsl_valid,
        latency_ms=result.latency_ms,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        error=result.error,
        dsl_output=result.dsl_output,
    )


def _arg_equal(pred_val, gt_val) -> bool:
    """인자 값 비교 — 타입 유연하게."""
    if pred_val is None:
        return False
    # bool vs string 처리
    if isinstance(gt_val, bool):
        if isinstance(pred_val, bool):
            return pred_val == gt_val
        return str(pred_val).lower() in ("true", "1") if gt_val else str(pred_val).lower() in ("false", "0")
    # 숫자 허용 오차 (온도, 밝기 등)
    if isinstance(gt_val, (int, float)) and isinstance(pred_val, (int, float, str)):
        try:
            return abs(float(pred_val) - float(gt_val)) < 1.0
        except (ValueError, TypeError):
            return False
    return str(pred_val).lower() == str(gt_val).lower()


def aggregate(results: list[EvalResult]) -> dict:
    """결과 집계 — method/model/difficulty별 통계 반환."""
    from collections import defaultdict
    import statistics

    def _stats(items: list[EvalResult]) -> dict:
        if not items:
            return {}
        n = len(items)
        return {
            "n": n,
            "exact_match_rate": sum(r.exact_match for r in items) / n,
            "function_name_acc": sum(r.function_name_match for r in items) / n,
            "avg_argument_match": statistics.mean(r.argument_match_ratio for r in items),
            "dsl_valid_rate": sum(r.dsl_valid for r in items) / n,
            "avg_latency_ms": statistics.mean(r.latency_ms for r in items),
            "avg_input_tokens": statistics.mean(r.input_tokens for r in items),
            "avg_output_tokens": statistics.mean(r.output_tokens for r in items),
            "error_rate": sum(r.error is not None for r in items) / n,
        }

    # 전체 / method+model별 / difficulty별 분류
    by_key: dict[tuple, list[EvalResult]] = defaultdict(list)
    for r in results:
        by_key[(r.method, r.model)].append(r)

    summary = {}
    for (method, model), items in by_key.items():
        key = f"{method}__{model}"
        summary[key] = _stats(items)

        # 난이도별 세분화
        from poc1.dataset.queries import QUERY_MAP
        for diff in ("simple", "medium", "complex"):
            sub = [r for r in items if QUERY_MAP.get(r.query_id, None) and
                   QUERY_MAP[r.query_id].difficulty == diff]
            if sub:
                summary[f"{key}__{diff}"] = _stats(sub)

    return summary
