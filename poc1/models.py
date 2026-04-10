"""
공통 타입 정의
"""
from dataclasses import dataclass, field
from typing import Any


# ── 함수 명세 ──────────────────────────────────────────────────────────────────

@dataclass
class FunctionSpec:
    """단일 함수 명세 (OpenAI tool calling 포맷 호환)."""
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema

    def to_tool(self) -> dict:
        """OpenAI tools[] 포맷으로 변환."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


# ── 데이터셋 ───────────────────────────────────────────────────────────────────

@dataclass
class FunctionCall:
    """함수 호출 결과."""
    name: str
    arguments: dict[str, Any]


@dataclass
class NLQuery:
    """NL 쿼리 + 정답."""
    id: str
    nl: str                        # 자연어 입력
    difficulty: str                # simple / medium / complex
    ground_truth: FunctionCall     # 정답 function call
    domain: str = "home_automation"
    note: str = ""                 # 추가 메모


# ── 실험 결과 ──────────────────────────────────────────────────────────────────

@dataclass
class MethodResult:
    """단일 쿼리에 대한 한 방식의 실행 결과."""
    query_id: str
    method: str                    # "A_direct" | "B_dsl_narrow" | "B_dsl_medium" | "B_dsl_wide"
    model: str
    predicted: FunctionCall | None
    dsl_output: dict | None        # Method B 전용: 중간 DSL 결과
    dsl_valid: bool                # DSL 스키마 유효성 (Method B)
    latency_ms: float
    input_tokens: int
    output_tokens: int
    error: str | None = None


@dataclass
class EvalResult:
    """단일 쿼리 평가 결과."""
    query_id: str
    method: str
    model: str
    exact_match: bool              # function name + 모든 arguments 완전 일치
    function_name_match: bool      # function name만 일치
    argument_match_ratio: float    # 일치한 argument 비율 (0.0~1.0)
    dsl_valid: bool
    latency_ms: float
    input_tokens: int
    output_tokens: int
    error: str | None = None
    dsl_output: dict | None = None  # Method B 전용: 실제 DSL 출력 (grammar_extender 분석용)


@dataclass
class ExperimentSummary:
    """실험 조건 하나의 집계 결과."""
    method: str
    model: str
    dsl_width: str | None          # Method B 전용
    difficulty: str | None         # None = 전체
    exact_match_rate: float
    function_name_acc: float
    avg_argument_match: float
    dsl_valid_rate: float
    avg_latency_ms: float
    avg_input_tokens: float
    avg_output_tokens: float
    n: int                         # 샘플 수
