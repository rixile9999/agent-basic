"""
평가 메트릭 (poc1과 동일 구조, 코인 도메인 수치 허용 오차 조정)
"""
from poc2.models import EvalResult, MethodResult, NLQuery


def evaluate(result: MethodResult, query: NLQuery) -> EvalResult:
    gt = query.ground_truth
    pred = result.predicted

    if pred is None:
        return EvalResult(
            query_id=query.id, method=result.method, model=result.model,
            exact_match=False, function_name_match=False, argument_match_ratio=0.0,
            dsl_valid=result.dsl_valid, latency_ms=result.latency_ms,
            input_tokens=result.input_tokens, output_tokens=result.output_tokens,
            error=result.error, dsl_output=result.dsl_output,
        )

    fn_match = pred.name == gt.name
    gt_args = gt.arguments
    pred_args = pred.arguments or {}

    if not gt_args:
        arg_ratio = 1.0
    else:
        matched = sum(1 for k, v in gt_args.items() if _arg_equal(pred_args.get(k), v))
        arg_ratio = matched / len(gt_args)

    exact = fn_match and arg_ratio == 1.0

    return EvalResult(
        query_id=query.id, method=result.method, model=result.model,
        exact_match=exact, function_name_match=fn_match,
        argument_match_ratio=arg_ratio, dsl_valid=result.dsl_valid,
        latency_ms=result.latency_ms, input_tokens=result.input_tokens,
        output_tokens=result.output_tokens, error=result.error,
        dsl_output=result.dsl_output,
    )


def _arg_equal(pred_val, gt_val) -> bool:
    if pred_val is None and gt_val is None:
        return True
    if pred_val is None or gt_val is None:
        return False
    if isinstance(gt_val, bool):
        if isinstance(pred_val, bool):
            return pred_val == gt_val
        return str(pred_val).lower() in ("true", "1") if gt_val else str(pred_val).lower() in ("false", "0")
    # 수치 허용 오차: 가격은 0.1% 이내 (코인 가격 범위가 넓음)
    if isinstance(gt_val, (int, float)) and isinstance(pred_val, (int, float, str)):
        try:
            pf, gf = float(pred_val), float(gt_val)
            if gf == 0:
                return pf == 0
            return abs(pf - gf) / abs(gf) < 0.001  # 0.1% 허용
        except (ValueError, TypeError):
            return False
    return str(pred_val).lower() == str(gt_val).lower()


def aggregate(results: list[EvalResult]) -> dict:
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

    by_key: dict[tuple, list[EvalResult]] = defaultdict(list)
    for r in results:
        by_key[(r.method, r.model)].append(r)

    summary = {}
    for (method, model), items in by_key.items():
        key = f"{method}__{model}"
        summary[key] = _stats(items)
        from poc2.dataset.queries import QUERY_MAP
        for diff in ("simple", "medium", "complex"):
            sub = [r for r in items if QUERY_MAP.get(r.query_id) and
                   QUERY_MAP[r.query_id].difficulty == diff]
            if sub:
                summary[f"{key}__{diff}"] = _stats(sub)

    return summary
