"""
Method B: NL → DSL → Function Call (그물망 방식)
Step 1: response_format JSON Schema로 constrained DSL 생성
Step 2: 결정론적 파서로 Function Call 변환
"""
import asyncio
import json
import time
from pathlib import Path
from openai import AsyncOpenAI

from poc1.config import DASHSCOPE_BASE_URL, DSL_SCHEMA_DIR, MAX_RETRIES, RETRY_DELAY
from poc1.dsl.fuzzy_parser import parse_dsl_fuzzy
from poc1.models import FunctionCall, MethodResult, NLQuery


def _load_dsl_schema(width: str) -> dict:
    path = DSL_SCHEMA_DIR / f"{width}.json"
    return json.loads(path.read_text())


def _build_system_prompt(width: str) -> str:
    if width == "medium":
        return """\
당신은 스마트홈 제어 어시스턴트입니다. 사용자 요청을 분석하여 아래 DSL JSON으로 변환하세요.

[필드 선택 규칙]
- verb (필수): turn_on | turn_off | toggle | set | adjust | increase | decrease | lock | unlock | play | stop | pause | check | get | query | activate | start | cancel
- target (필수): light | lights | temperature | ac | heater | air_conditioner | tv | washing_machine | dishwasher | air_purifier | robot_vacuum | timer | alarm | temperature_sensor | humidity_sensor | air_quality | co2 | motion_sensor | music | video | media | door | front_door | back_door | garage | scene
- location: living_room | bedroom | kitchen | bathroom | outdoor | garage | all
- state: on | off | locked | unlocked
- value: 숫자값 (온도, 밝기, 볼륨 등)
- params: 추가 인자 (예: {"brightness": 50}, {"mode": "cool"}, {"label": "라면"})

[예시]
입력: "거실 불 꺼줘"
출력: {"verb": "turn_off", "target": "light", "location": "living_room"}

입력: "에어컨 24도로 설정해"
출력: {"verb": "set", "target": "ac", "location": "living_room", "value": 24, "params": {"mode": "cool"}}

입력: "취침 모드 켜줘"
출력: {"verb": "activate", "target": "scene", "params": {"name": "sleep"}}
"""

    if width == "wide":
        return """\
당신은 스마트홈 제어 어시스턴트입니다. 사용자 요청을 분석하여 아래 DSL JSON으로 변환하세요.

[필드 설명]
- intent (필수): 사용자의 의도를 짧은 동사구로 표현 (자유 문자열, 50자 이내)
- subject (필수): 제어하거나 조회할 대상 (자유 문자열, 80자 이내)
- location: 위치 정보 (예: 거실, 침실, 주방, 야외)
- value: 숫자 또는 문자열 설정값 (온도, 밝기 등)
- modifiers: 추가 수식어 배열 (예: ["전체", "조용히"])

[예시]
입력: "거실 불 꺼줘"
출력: {"intent": "turn off light", "subject": "거실 조명", "location": "거실"}

입력: "에어컨 24도로 설정해"
출력: {"intent": "set temperature", "subject": "에어컨", "location": "거실", "value": 24}

입력: "자려고 하는데 분위기 만들어줘"
출력: {"intent": "activate scene", "subject": "sleep scene", "modifiers": ["취침"]}
"""

    # fallback
    return "당신은 스마트홈 제어 어시스턴트입니다. 사용자 요청을 JSON DSL로 변환하세요."


async def run_method_b(
    query: NLQuery,
    *,
    width: str,
    model: str,
    api_key: str,
    semaphore: asyncio.Semaphore,
) -> MethodResult:
    """단일 쿼리에 대해 Method B 실행 (지정된 DSL 폭 사용)."""
    client = AsyncOpenAI(api_key=api_key, base_url=DASHSCOPE_BASE_URL)
    dsl_schema = _load_dsl_schema(width)
    method_name = f"B_dsl_{width}"

    last_error: str | None = None
    for attempt in range(MAX_RETRIES):
        try:
            # ── Step 1: NL → DSL ───────────────────────────────────────────────
            async with semaphore:
                t0 = time.perf_counter()
                response = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": _build_system_prompt(width)},
                        {"role": "user", "content": query.nl},
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": f"{width}_dsl",
                            "schema": dsl_schema,
                            "strict": True,
                        },
                    },
                )
                latency_ms = (time.perf_counter() - t0) * 1000

            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0

            raw_content = response.choices[0].message.content or ""

            # ── Step 2: DSL 파싱 ───────────────────────────────────────────────
            try:
                dsl_dict = json.loads(raw_content)
                dsl_valid = True
            except json.JSONDecodeError as e:
                return MethodResult(
                    query_id=query.id,
                    method=method_name,
                    model=model,
                    predicted=None,
                    dsl_output=None,
                    dsl_valid=False,
                    latency_ms=latency_ms,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    error=f"DSL JSON 파싱 실패: {e}",
                )

            # ── Step 3: DSL → FunctionCall (strict → fuzzy 2-pass) ────────────
            try:
                predicted, _ = parse_dsl_fuzzy(dsl_dict, width)
            except Exception as e:
                return MethodResult(
                    query_id=query.id,
                    method=method_name,
                    model=model,
                    predicted=None,
                    dsl_output=dsl_dict,
                    dsl_valid=dsl_valid,
                    latency_ms=latency_ms,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    error=f"DSL→Function 매핑 실패: {e}",
                )

            return MethodResult(
                query_id=query.id,
                method=method_name,
                model=model,
                predicted=predicted,
                dsl_output=dsl_dict,
                dsl_valid=dsl_valid,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

        except Exception as e:
            last_error = str(e)
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))

    return MethodResult(
        query_id=query.id,
        method=method_name,
        model=model,
        predicted=None,
        dsl_output=None,
        dsl_valid=False,
        latency_ms=0.0,
        input_tokens=0,
        output_tokens=0,
        error=last_error,
    )
