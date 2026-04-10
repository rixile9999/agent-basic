"""Method B: NL → DSL → Function Call"""
import asyncio
import json
import time
from pathlib import Path
from openai import AsyncOpenAI

from poc2.config import DASHSCOPE_BASE_URL, DSL_SCHEMA_DIR, MAX_RETRIES, RETRY_DELAY
from poc2.dsl.fuzzy_parser import parse_dsl_fuzzy
from poc2.models import FunctionCall, MethodResult, NLQuery


def _load_dsl_schema(width: str) -> dict:
    return json.loads((DSL_SCHEMA_DIR / f"{width}.json").read_text())


def _build_system_prompt(width: str) -> str:
    if width == "medium":
        return """\
당신은 코인 트레이딩 어시스턴트입니다. 사용자 요청을 아래 DSL JSON으로 변환하세요.

[verb 선택]
- buy: 매수 주문
- sell: 매도 주문
- cancel: 주문 취소
- get_price: 현재가 조회
- get_balance: 잔고 조회
- get_portfolio: 포트폴리오 조회
- get_history: 주문 내역 조회
- get_market: 시장 정보 조회
- set_alert: 가격 알림 설정
- set_condition: 조건부 주문

[필드]
- asset: 코인 심볼 (BTC, ETH, XRP, SOL, DOGE, ADA, AVAX, LINK, MATIC, BNB, TRX)
- qty: 수량 (숫자)
- price_type: market(시장가) | limit(지정가)
- price: 지정가 가격
- trigger_condition: gte(이상/넘으면) | lte(이하/내려오면) | gt(초과) | lt(미만)
- trigger_price: 조건 기준 가격
- action_asset: 조건부 주문에서 실제 매수/매도할 코인 (asset과 다를 때)
- action_side: buy | sell
- action_qty: 실행 수량
- order_id: 취소할 주문 ID
- side_filter: 취소 방향 필터 buy | sell
- order_type_filter: 취소 주문유형 필터 limit | market
- limit: get_history 조회 건수

[예시]
"BTC 0.1개 시장가 매수" → {"verb":"buy","asset":"BTC","qty":0.1,"price_type":"market"}
"ETH 3000달러 지정가 0.5개 매도" → {"verb":"sell","asset":"ETH","qty":0.5,"price_type":"limit","price":3000}
"BTC 6만달러 넘으면 알림" → {"verb":"set_alert","asset":"BTC","trigger_condition":"gte","trigger_price":60000}
"BTC 6만달러 넘으면 ETH 1개 시장가 팔아" → {"verb":"set_condition","asset":"BTC","trigger_condition":"gte","trigger_price":60000,"action_asset":"ETH","action_side":"sell","action_qty":1}
"BTC 지정가 매수 주문 취소" → {"verb":"cancel","asset":"BTC","side_filter":"buy","order_type_filter":"limit"}
"""

    if width == "wide":
        return """\
당신은 코인 트레이딩 어시스턴트입니다. 사용자 요청을 아래 DSL JSON으로 변환하세요.

[필드]
- intent (필수): 의도를 짧은 동사구로 (예: "buy", "sell", "get price", "set alert", "conditional sell", "cancel order", "check balance", "get history")
- asset (필수): 주요 코인 심볼 (BTC, ETH 등). 조건부 주문에서는 트리거 코인.
- amount: 주문 수량
- price: 지정가 가격
- trigger: 조건 표현 (예: "BTC >= 60000", "ETH <= 2500")
- target_asset: 크로스애셋 조건부 주문에서 실제 매수/매도할 코인
- target_amount: 조건부 주문 실행 수량
- modifiers: 추가 수식어 배열

[예시]
"BTC 0.1개 시장가 매수" → {"intent":"buy","asset":"BTC","amount":0.1}
"ETH 3000달러에 0.5개 지정가 매도" → {"intent":"sell","asset":"ETH","amount":0.5,"price":3000}
"BTC 6만달러 이상 되면 알림" → {"intent":"set alert","asset":"BTC","trigger":"BTC >= 60000"}
"BTC 6만달러 넘으면 ETH 1개 시장가 팔아" → {"intent":"conditional sell","asset":"BTC","trigger":"BTC >= 60000","target_asset":"ETH","target_amount":1}
"BTC 지정가 매수 주문 취소" → {"intent":"cancel order","asset":"BTC","modifiers":["지정가","매수"]}
"""

    return "당신은 코인 트레이딩 어시스턴트입니다. 요청을 JSON DSL로 변환하세요."


async def run_method_b(
    query: NLQuery, *, width: str, model: str, api_key: str, semaphore: asyncio.Semaphore
) -> MethodResult:
    client = AsyncOpenAI(api_key=api_key, base_url=DASHSCOPE_BASE_URL)
    dsl_schema = _load_dsl_schema(width)
    method_name = f"B_dsl_{width}"
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
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
                        "json_schema": {"name": f"{width}_dsl", "schema": dsl_schema, "strict": True},
                    },
                )
                latency_ms = (time.perf_counter() - t0) * 1000

            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0
            raw_content = response.choices[0].message.content or ""

            try:
                dsl_dict = json.loads(raw_content)
                dsl_valid = True
            except json.JSONDecodeError as e:
                return MethodResult(
                    query_id=query.id, method=method_name, model=model,
                    predicted=None, dsl_output=None, dsl_valid=False,
                    latency_ms=latency_ms, input_tokens=input_tokens, output_tokens=output_tokens,
                    error=f"DSL JSON 파싱 실패: {e}",
                )

            try:
                predicted, _ = parse_dsl_fuzzy(dsl_dict, width)
            except Exception as e:
                return MethodResult(
                    query_id=query.id, method=method_name, model=model,
                    predicted=None, dsl_output=dsl_dict, dsl_valid=dsl_valid,
                    latency_ms=latency_ms, input_tokens=input_tokens, output_tokens=output_tokens,
                    error=f"DSL→Function 매핑 실패: {e}",
                )

            return MethodResult(
                query_id=query.id, method=method_name, model=model,
                predicted=predicted, dsl_output=dsl_dict, dsl_valid=dsl_valid,
                latency_ms=latency_ms, input_tokens=input_tokens, output_tokens=output_tokens,
            )

        except Exception as e:
            last_error = str(e)
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))

    return MethodResult(
        query_id=query.id, method=method_name, model=model,
        predicted=None, dsl_output=None, dsl_valid=False,
        latency_ms=0.0, input_tokens=0, output_tokens=0, error=last_error,
    )
