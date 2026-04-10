"""
공통 타입 정의 (poc1과 동일 구조)
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FunctionSpec:
    name: str
    description: str
    parameters: dict[str, Any]

    def to_tool(self) -> dict:
        return {"type": "function", "function": {"name": self.name, "description": self.description, "parameters": self.parameters}}


@dataclass
class FunctionCall:
    name: str
    arguments: dict[str, Any]


@dataclass
class NLQuery:
    id: str
    nl: str
    difficulty: str          # simple / medium / complex
    ground_truth: FunctionCall
    domain: str = "crypto_trading"
    note: str = ""


@dataclass
class MethodResult:
    query_id: str
    method: str
    model: str
    predicted: FunctionCall | None
    dsl_output: dict | None
    dsl_valid: bool
    latency_ms: float
    input_tokens: int
    output_tokens: int
    error: str | None = None


@dataclass
class EvalResult:
    query_id: str
    method: str
    model: str
    exact_match: bool
    function_name_match: bool
    argument_match_ratio: float
    dsl_valid: bool
    latency_ms: float
    input_tokens: int
    output_tokens: int
    error: str | None = None
    dsl_output: dict | None = None


@dataclass
class ExperimentSummary:
    method: str
    model: str
    dsl_width: str | None
    difficulty: str | None
    exact_match_rate: float
    function_name_acc: float
    avg_argument_match: float
    dsl_valid_rate: float
    avg_latency_ms: float
    avg_input_tokens: float
    avg_output_tokens: float
    n: int
