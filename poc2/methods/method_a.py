"""Method A: NL → Function Call (직접 FC)"""
import asyncio
import json
import time
from openai import AsyncOpenAI

from poc2.config import DASHSCOPE_BASE_URL, MAX_RETRIES, RETRY_DELAY
from poc2.dataset.functions import FUNCTION_TOOLS
from poc2.models import FunctionCall, MethodResult, NLQuery

_SYSTEM_PROMPT = """\
당신은 코인 트레이딩 어시스턴트입니다. 사용자 요청을 분석하여 적절한 함수를 호출하세요.

지원 함수:
- place_order: 코인 매수/매도 주문 (ticker, side, qty, order_type, price)
- cancel_order: 주문 취소 (order_id, ticker, side, order_type)
- get_price: 현재가 조회 (ticker)
- get_balance: 잔고 조회 (asset)
- get_portfolio: 포트폴리오 조회 ()
- set_alert: 가격 알림 설정 (ticker, condition, threshold)
- set_conditional_order: 조건부 주문 (trigger_ticker, trigger_condition, trigger_price, action_ticker, action_side, action_qty, action_order_type)
- get_market_info: 시장 정보 조회 (ticker)
- get_order_history: 주문 내역 조회 (ticker, limit)

코인 심볼: BTC(비트코인), ETH(이더리움), XRP(리플), SOL(솔라나), DOGE(도지코인), ADA(에이다), AVAX(아발란체), LINK(체인링크), MATIC(폴리곤), BNB, TRX(트론)
조건: gte=이상/넘으면, lte=이하/내려오면, gt=초과, lt=미만
주문유형: market=시장가/즉시, limit=지정가
"""


async def run_method_a(
    query: NLQuery, *, model: str, api_key: str, semaphore: asyncio.Semaphore
) -> MethodResult:
    client = AsyncOpenAI(api_key=api_key, base_url=DASHSCOPE_BASE_URL)
    last_error = None

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
                    tools=FUNCTION_TOOLS,
                    tool_choice="required",
                )
                latency_ms = (time.perf_counter() - t0) * 1000

            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0

            choice = response.choices[0]
            tool_calls = getattr(choice.message, "tool_calls", None)
            if not tool_calls:
                return MethodResult(
                    query_id=query.id, method="A_direct", model=model,
                    predicted=None, dsl_output=None, dsl_valid=False,
                    latency_ms=latency_ms, input_tokens=input_tokens, output_tokens=output_tokens,
                    error="tool_calls 없음",
                )

            tc = tool_calls[0]
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError as e:
                return MethodResult(
                    query_id=query.id, method="A_direct", model=model,
                    predicted=None, dsl_output=None, dsl_valid=False,
                    latency_ms=latency_ms, input_tokens=input_tokens, output_tokens=output_tokens,
                    error=f"arguments JSON 파싱 실패: {e}",
                )

            return MethodResult(
                query_id=query.id, method="A_direct", model=model,
                predicted=FunctionCall(fn_name, fn_args),
                dsl_output=None, dsl_valid=False,
                latency_ms=latency_ms, input_tokens=input_tokens, output_tokens=output_tokens,
            )

        except Exception as e:
            last_error = str(e)
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))

    return MethodResult(
        query_id=query.id, method="A_direct", model=model,
        predicted=None, dsl_output=None, dsl_valid=False,
        latency_ms=0.0, input_tokens=0, output_tokens=0, error=last_error,
    )
