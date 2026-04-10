"""
Method A: NL → Function Call (직접 방식)
OpenAI tool calling format으로 DashScope 호출.
"""
import asyncio
import json
import time
from openai import AsyncOpenAI

from poc1.config import DASHSCOPE_BASE_URL, MAX_RETRIES, RETRY_DELAY
from poc1.dataset.functions import FUNCTIONS
from poc1.models import FunctionCall, MethodResult, NLQuery

_SYSTEM_PROMPT = (
    "당신은 스마트홈 제어 어시스턴트입니다. "
    "사용자의 요청을 분석하여 반드시 제공된 함수 중 하나를 호출하세요. "
    "함수를 반드시 호출해야 합니다."
)


async def run_method_a(
    query: NLQuery,
    *,
    model: str,
    api_key: str,
    semaphore: asyncio.Semaphore,
) -> MethodResult:
    """단일 쿼리에 대해 Method A 실행."""
    client = AsyncOpenAI(api_key=api_key, base_url=DASHSCOPE_BASE_URL)
    tools = [f.to_tool() for f in FUNCTIONS]

    last_error: str | None = None
    for attempt in range(MAX_RETRIES):
        try:
            async with semaphore:
                t0 = time.perf_counter()
                response = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": query.nl},
                    ],
                    tools=tools,
                    tool_choice="required",
                )
                latency_ms = (time.perf_counter() - t0) * 1000

            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0

            choice = response.choices[0]
            tool_calls = choice.message.tool_calls

            if not tool_calls:
                last_error = "tool_calls 없음"
                await asyncio.sleep(RETRY_DELAY)
                continue

            tc = tool_calls[0]
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError as e:
                last_error = f"arguments JSON 파싱 실패: {e}"
                await asyncio.sleep(RETRY_DELAY)
                continue

            return MethodResult(
                query_id=query.id,
                method="A_direct",
                model=model,
                predicted=FunctionCall(name=fn_name, arguments=fn_args),
                dsl_output=None,
                dsl_valid=False,
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
        method="A_direct",
        model=model,
        predicted=None,
        dsl_output=None,
        dsl_valid=False,
        latency_ms=0.0,
        input_tokens=0,
        output_tokens=0,
        error=last_error,
    )
