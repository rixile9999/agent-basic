"""
코인 트레이딩 함수 명세 (9개)

설계 원칙:
- 함수 의미 경계 명확 (smart home과 달리 겹침 없음)
- 조건부 주문은 flat 구조 (nested 없음, DSL 스키마 단순화)
- 한국 코인 거래소 기준 (KRW 페어 가정, 24시간 거래)
"""
from poc2.models import FunctionSpec

FUNCTIONS: list[FunctionSpec] = [
    FunctionSpec(
        name="place_order",
        description="코인 매수/매도 주문 실행",
        parameters={
            "type": "object",
            "required": ["ticker", "side", "qty", "order_type"],
            "properties": {
                "ticker":     {"type": "string", "description": "코인 심볼 (BTC, ETH, XRP 등)"},
                "side":       {"type": "string", "enum": ["buy", "sell"]},
                "qty":        {"type": "number", "description": "주문 수량"},
                "order_type": {"type": "string", "enum": ["market", "limit", "stop_loss", "take_profit"]},
                "price":      {"type": ["number", "null"], "description": "지정가/손절가. market이면 null"},
            },
        },
    ),
    FunctionSpec(
        name="cancel_order",
        description="미체결 주문 취소. order_id 또는 ticker/side/order_type 필터 중 하나 이상 필요",
        parameters={
            "type": "object",
            "properties": {
                "order_id":   {"type": ["string", "null"], "description": "주문 ID (ORD-xxx)"},
                "ticker":     {"type": ["string", "null"], "description": "취소할 코인 심볼"},
                "side":       {"type": ["string", "null"], "enum": ["buy", "sell", None]},
                "order_type": {"type": ["string", "null"], "enum": ["market", "limit", "stop_loss", "take_profit", None]},
            },
        },
    ),
    FunctionSpec(
        name="get_price",
        description="코인 현재가 조회",
        parameters={
            "type": "object",
            "required": ["ticker"],
            "properties": {
                "ticker": {"type": "string"},
            },
        },
    ),
    FunctionSpec(
        name="get_balance",
        description="보유 코인 잔고 조회. asset 없으면 전체 조회",
        parameters={
            "type": "object",
            "properties": {
                "asset": {"type": ["string", "null"], "description": "코인 심볼. null이면 전체"},
            },
        },
    ),
    FunctionSpec(
        name="get_portfolio",
        description="전체 포트폴리오 조회 (보유량, 평가금액, 손익, 비중)",
        parameters={
            "type": "object",
            "properties": {},
        },
    ),
    FunctionSpec(
        name="set_alert",
        description="가격 알림 설정",
        parameters={
            "type": "object",
            "required": ["ticker", "condition", "threshold"],
            "properties": {
                "ticker":    {"type": "string"},
                "condition": {"type": "string", "enum": ["gte", "lte", "gt", "lt"],
                              "description": "gte=이상, lte=이하, gt=초과, lt=미만"},
                "threshold": {"type": "number", "description": "알림 기준 가격"},
            },
        },
    ),
    FunctionSpec(
        name="set_conditional_order",
        description="조건부 주문. 트리거 가격 조건 충족 시 자동 주문 실행",
        parameters={
            "type": "object",
            "required": [
                "trigger_ticker", "trigger_condition", "trigger_price",
                "action_ticker", "action_side", "action_qty", "action_order_type",
            ],
            "properties": {
                "trigger_ticker":     {"type": "string", "description": "조건 감시 코인"},
                "trigger_condition":  {"type": "string", "enum": ["gte", "lte", "gt", "lt"]},
                "trigger_price":      {"type": "number"},
                "action_ticker":      {"type": "string", "description": "실행할 주문 코인"},
                "action_side":        {"type": "string", "enum": ["buy", "sell"]},
                "action_qty":         {"type": "number"},
                "action_order_type":  {"type": "string", "enum": ["market", "limit"]},
                "action_price":       {"type": ["number", "null"], "description": "action이 limit일 때 가격"},
            },
        },
    ),
    FunctionSpec(
        name="get_market_info",
        description="코인 시장 정보 조회 (시가/고가/저가/종가, 24h 거래량, 변동률, 시가총액)",
        parameters={
            "type": "object",
            "required": ["ticker"],
            "properties": {
                "ticker": {"type": "string"},
            },
        },
    ),
    FunctionSpec(
        name="get_order_history",
        description="주문 내역 조회",
        parameters={
            "type": "object",
            "properties": {
                "ticker": {"type": ["string", "null"], "description": "특정 코인만 조회. null이면 전체"},
                "limit":  {"type": "integer", "default": 10, "description": "조회 건수"},
            },
        },
    ),
]

FUNCTION_MAP = {f.name: f for f in FUNCTIONS}
FUNCTION_TOOLS = [f.to_tool() for f in FUNCTIONS]
