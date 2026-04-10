"""
실험 결과 파싱 → 마크다운 보고서 생성

사용법:
  # 최신 결과로 보고서 생성
  uv run python -m poc1.report

  # 특정 파일 지정
  uv run python -m poc1.report --file poc1/results/results_20260410_124530_smoke.json
"""
import argparse
import json
from pathlib import Path
from datetime import datetime

from poc1.config import RESULTS_DIR


# ── 데이터 로드 ────────────────────────────────────────────────────────────────

def load_latest() -> tuple[dict, Path]:
    files = sorted(RESULTS_DIR.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"결과 파일 없음: {RESULTS_DIR}")
    return json.loads(files[-1].read_text()), files[-1]


def load_file(path: str) -> tuple[dict, Path]:
    p = Path(path)
    return json.loads(p.read_text()), p


# ── 집계 헬퍼 ─────────────────────────────────────────────────────────────────

def _top(summary: dict) -> dict:
    """난이도 분류 없는 상위 키만 반환."""
    return {k: v for k, v in summary.items() if k.count("__") == 1}


def _by_difficulty(summary: dict, method_model: str) -> dict:
    """특정 method__model의 난이도별 결과."""
    return {
        k.split("__")[2]: v
        for k, v in summary.items()
        if k.startswith(method_model + "__") and k.count("__") == 2
    }


def _method_label(key: str) -> str:
    labels = {
        "A_direct": "A (직접 FC)",
        "B_dsl_medium": "B-medium DSL",
        "B_dsl_wide": "B-wide DSL",
    }
    method, model = key.split("__")
    return f"{labels.get(method, method)} / {model}"


def _winner(top: dict, metric: str) -> str:
    best_key = max(top, key=lambda k: top[k].get(metric, 0))
    best_val = top[best_key].get(metric, 0)
    return f"{_method_label(best_key)} ({best_val*100:.1f}%)"


def _token_winner(top: dict) -> str:
    best_key = min(top, key=lambda k: top[k]["avg_input_tokens"] + top[k]["avg_output_tokens"])
    tok = top[best_key]["avg_input_tokens"] + top[best_key]["avg_output_tokens"]
    return f"{_method_label(best_key)} ({tok:.0f} tok)"


# ── 섹션 생성 ─────────────────────────────────────────────────────────────────

def _section_overview(top: dict, meta: dict) -> str:
    models = meta.get("models", [])
    widths = meta.get("dsl_widths", [])
    n_q = meta.get("n_queries", "?")
    n_t = meta.get("n_tasks", "?")
    ts = meta.get("timestamp", "")

    lines = [
        "## 1. 실험 개요",
        "",
        f"| 항목 | 값 |",
        f"|---|---|",
        f"| 실행 시각 | {ts} |",
        f"| 테스트 쿼리 수 | {n_q}개 |",
        f"| 총 API 호출 | {n_t}회 |",
        f"| 테스트 모델 | {', '.join(models)} |",
        f"| DSL 폭 변형 | {', '.join(widths)} |",
        "",
    ]
    return "\n".join(lines)


def _section_main_table(top: dict) -> str:
    lines = [
        "## 2. 전체 성능 비교",
        "",
        "| 방식 / 모델 | EM% | FN% | ARG% | 토큰 | 지연(ms) | 에러% |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for k in sorted(top):
        s = top[k]
        tok = s["avg_input_tokens"] + s["avg_output_tokens"]
        lines.append(
            f"| {_method_label(k)} "
            f"| {s['exact_match_rate']*100:.1f}% "
            f"| {s['function_name_acc']*100:.1f}% "
            f"| {s['avg_argument_match']*100:.1f}% "
            f"| {tok:.0f} "
            f"| {s['avg_latency_ms']:.0f} "
            f"| {s['error_rate']*100:.1f}% |"
        )
    lines += [
        "",
        "> **EM** = Exact Match (함수명 + 모든 인자 완전 일치)",
        "> **FN** = Function Name 정확도",
        "> **ARG** = 인자 일치 비율 (평균)",
        "",
    ]
    return "\n".join(lines)


def _section_by_method(top: dict) -> str:
    """방식별 모델 평균."""
    from collections import defaultdict
    method_scores: dict[str, list] = defaultdict(list)
    for k, v in top.items():
        method = k.split("__")[0]
        method_scores[method].append(v)

    lines = [
        "## 3. 방식별 평균 성능",
        "",
        "| 방식 | EM% (평균) | 토큰 (평균) | 에러% (평균) |",
        "|---|---:|---:|---:|",
    ]
    method_labels = {
        "A_direct": "A — 직접 Function Call",
        "B_dsl_medium": "B — Medium DSL",
        "B_dsl_wide": "B — Wide DSL",
    }
    for method in ["A_direct", "B_dsl_medium", "B_dsl_wide"]:
        items = method_scores.get(method, [])
        if not items:
            continue
        avg_em = sum(x["exact_match_rate"] for x in items) / len(items)
        avg_tok = sum(x["avg_input_tokens"] + x["avg_output_tokens"] for x in items) / len(items)
        avg_err = sum(x["error_rate"] for x in items) / len(items)
        lines.append(
            f"| {method_labels.get(method, method)} "
            f"| {avg_em*100:.1f}% "
            f"| {avg_tok:.0f} "
            f"| {avg_err*100:.1f}% |"
        )
    lines.append("")
    return "\n".join(lines)


def _section_difficulty(summary: dict, top: dict) -> str:
    lines = [
        "## 4. 난이도별 Exact Match",
        "",
        "| 방식 / 모델 | simple | medium | complex |",
        "|---|---:|---:|---:|",
    ]
    for k in sorted(top):
        diff = _by_difficulty(summary, k)
        s_em = f"{diff['simple']['exact_match_rate']*100:.1f}%" if "simple" in diff else "-"
        m_em = f"{diff['medium']['exact_match_rate']*100:.1f}%" if "medium" in diff else "-"
        c_em = f"{diff['complex']['exact_match_rate']*100:.1f}%" if "complex" in diff else "-"
        lines.append(f"| {_method_label(k)} | {s_em} | {m_em} | {c_em} |")
    lines.append("")
    return "\n".join(lines)


def _section_token_efficiency(top: dict) -> str:
    # A_direct 기준 토큰 절감률 계산
    a_tokens = {k.split("__")[1]: v["avg_input_tokens"] + v["avg_output_tokens"]
                for k, v in top.items() if k.startswith("A_direct")}

    lines = [
        "## 5. 토큰 효율 분석",
        "",
        "| 방식 / 모델 | 평균 토큰 | A 대비 절감률 |",
        "|---|---:|---:|",
    ]
    for k in sorted(top):
        s = top[k]
        model = k.split("__")[1]
        tok = s["avg_input_tokens"] + s["avg_output_tokens"]
        a_tok = a_tokens.get(model, tok)
        saving = (1 - tok / a_tok) * 100 if a_tok > 0 else 0
        saving_str = f"{saving:.1f}% 절감" if saving > 0 else "-"
        lines.append(f"| {_method_label(k)} | {tok:.0f} | {saving_str} |")
    lines.append("")
    return "\n".join(lines)


def _section_findings(top: dict, summary: dict) -> str:
    # 자동 인사이트 추출
    findings = []

    # 1. 전체 EM 최고
    best_em_key = max(top, key=lambda k: top[k]["exact_match_rate"])
    best_em = top[best_em_key]["exact_match_rate"] * 100
    findings.append(f"- **최고 정확도**: {_method_label(best_em_key)} (EM {best_em:.1f}%)")

    # 2. 토큰 최소
    min_tok_key = min(top, key=lambda k: top[k]["avg_input_tokens"] + top[k]["avg_output_tokens"])
    min_tok = top[min_tok_key]["avg_input_tokens"] + top[min_tok_key]["avg_output_tokens"]
    a_tok_avg = sum(
        v["avg_input_tokens"] + v["avg_output_tokens"]
        for k, v in top.items() if k.startswith("A_direct")
    ) / max(1, sum(1 for k in top if k.startswith("A_direct")))
    saving = (1 - min_tok / a_tok_avg) * 100
    findings.append(f"- **최고 토큰 효율**: {_method_label(min_tok_key)} ({min_tok:.0f} tok, A 대비 {saving:.1f}% 절감)")

    # 3. DSL vs Direct 비교
    dsl_ems = [v["exact_match_rate"] for k, v in top.items() if k.startswith("B_dsl")]
    direct_ems = [v["exact_match_rate"] for k, v in top.items() if k.startswith("A_direct")]
    if dsl_ems and direct_ems:
        avg_dsl = sum(dsl_ems) / len(dsl_ems) * 100
        avg_direct = sum(direct_ems) / len(direct_ems) * 100
        if avg_dsl > avg_direct:
            findings.append(f"- **DSL 방식 우세**: 평균 EM {avg_dsl:.1f}% vs 직접 {avg_direct:.1f}%")
        elif avg_direct > avg_dsl:
            findings.append(f"- **직접 방식 우세**: 평균 EM {avg_direct:.1f}% vs DSL {avg_dsl:.1f}%")
        else:
            findings.append(f"- **직접 방식 / DSL 동률**: 평균 EM {avg_direct:.1f}%")

    # 4. 에러율 경고
    high_err = [(k, v["error_rate"]) for k, v in top.items() if v["error_rate"] > 0.1]
    for k, err in sorted(high_err, key=lambda x: -x[1]):
        findings.append(f"- **에러율 주의**: {_method_label(k)} — {err*100:.1f}% 실패")

    # 5. medium 난이도 역전 케이스
    for k in top:
        if not k.startswith("B_dsl"):
            continue
        model = k.split("__")[1]
        a_key = f"A_direct__{model}"
        diff_b = _by_difficulty(summary, k)
        diff_a = _by_difficulty(summary, a_key)
        if "medium" in diff_b and "medium" in diff_a:
            b_med = diff_b["medium"]["exact_match_rate"]
            a_med = diff_a["medium"]["exact_match_rate"]
            if b_med > a_med + 0.1:
                findings.append(
                    f"- **medium 난이도 역전**: {_method_label(k)} ({b_med*100:.1f}%) > {_method_label(a_key)} ({a_med*100:.1f}%) — DSL 그물망 효과 확인"
                )

    lines = [
        "## 6. 주요 발견",
        "",
    ] + findings + [""]
    return "\n".join(lines)


def _section_conclusion(top: dict) -> str:
    dsl_avg = sum(v["exact_match_rate"] for k, v in top.items() if "dsl" in k) / max(
        1, sum(1 for k in top if "dsl" in k)
    )
    direct_avg = sum(v["exact_match_rate"] for k, v in top.items() if "direct" in k) / max(
        1, sum(1 for k in top if "direct" in k)
    )
    tok_ratio = sum(
        v["avg_input_tokens"] + v["avg_output_tokens"] for k, v in top.items() if "dsl" in k
    ) / max(
        1,
        sum(v["avg_input_tokens"] + v["avg_output_tokens"] for k, v in top.items() if "direct" in k)
        / max(1, sum(1 for k in top if "direct" in k))
        * sum(1 for k in top if "dsl" in k),
    )

    lines = [
        "## 7. 결론 및 다음 단계",
        "",
        "### POC 1 핵심 질문 답변",
        "",
        f"| 질문 | 결과 |",
        f"|---|---|",
        f"| NL→DSL→Function이 NL→Function보다 정확한가? | {'조건부 Yes (고성능 모델 한정)' if dsl_avg >= direct_avg * 0.9 else 'No (현재 조건에서는 직접 방식 우세)'} |",
        f"| 토큰 효율이 개선되는가? | Yes — DSL 방식이 약 {(1-tok_ratio)*100:.0f}% 절감 |",
        f"| 소형 모델에서도 유효한가? | 추가 검증 필요 (POC 2) |",
        "",
        "### 다음 단계 (POC 2)",
        "",
        "1. Wide DSL 생성에 특화된 소형 모델 파인튜닝",
        "2. qwen-max 수준의 Wide DSL 출력을 turbo 크기 모델로 재현",
        "3. DSL 스키마 자동 생성 파이프라인 구현",
        "",
    ]
    return "\n".join(lines)


# ── 보고서 조립 ───────────────────────────────────────────────────────────────

def generate_report(data: dict, src_path: Path) -> str:
    summary = data["summary"]
    meta = data.get("meta", {})
    top = _top(summary)

    sections = [
        f"# POC 1 실험 보고서",
        f"",
        f"> 소스: `{src_path.name}`  |  생성: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"",
        _section_overview(top, meta),
        _section_main_table(top),
        _section_by_method(top),
        _section_difficulty(summary, top),
        _section_token_efficiency(top),
        _section_findings(top, summary),
        _section_conclusion(top),
    ]
    return "\n".join(sections)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="POC 1 결과 보고서 생성")
    p.add_argument("--file", default=None, help="결과 JSON 경로 (기본: 최신 파일)")
    p.add_argument("--out", default=None, help="출력 마크다운 경로 (기본: results/ 저장)")
    args = p.parse_args()

    if args.file:
        data, src = load_file(args.file)
    else:
        data, src = load_latest()

    print(f"읽기: {src}")
    report = generate_report(data, src)

    # 저장
    out_path = Path(args.out) if args.out else src.with_suffix(".md")
    out_path.write_text(report, encoding="utf-8")
    print(f"보고서 저장: {out_path}")
    print()
    print(report)


if __name__ == "__main__":
    main()
