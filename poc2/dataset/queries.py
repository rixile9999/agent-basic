"""
코인 트레이딩 NL 쿼리 데이터셋 (100개)

설계 원칙:
- 모든 ground truth는 NL에서 명시적으로 읽을 수 있음 (암시적 추론 불필요)
- 한국어 코인 용어 자연스럽게 사용 (비트코인/BTC, 시장가/지정가 등)
- simple: 단일 함수, 명시적 파라미터
- medium: 지정가 주문, 알림, 단순 조건부 주문 (같은 코인)
- complex: 크로스애셋 조건부 주문, 복합 취소, 포트폴리오

난이도별 분류:
  simple  33개  (s01~s33)
  medium  33개  (m01~m33)
  complex 34개  (c01~c34)
"""
from poc2.models import FunctionCall, NLQuery

FC = FunctionCall

QUERIES: list[NLQuery] = [
    # ── Simple: get_price (s01~s10) ──────────────────────────────────────────
    NLQuery("s01", "비트코인 현재가 알려줘", "simple",
            FC("get_price", {"ticker": "BTC"})),
    NLQuery("s02", "이더리움 지금 얼마야", "simple",
            FC("get_price", {"ticker": "ETH"})),
    NLQuery("s03", "리플 현재가", "simple",
            FC("get_price", {"ticker": "XRP"})),
    NLQuery("s04", "솔라나 시세 알려줘", "simple",
            FC("get_price", {"ticker": "SOL"})),
    NLQuery("s05", "도지코인 얼마야", "simple",
            FC("get_price", {"ticker": "DOGE"})),
    NLQuery("s06", "에이다 가격 확인해줘", "simple",
            FC("get_price", {"ticker": "ADA"})),
    NLQuery("s07", "아발란체 현재가", "simple",
            FC("get_price", {"ticker": "AVAX"})),
    NLQuery("s08", "체인링크 시세 알려줘", "simple",
            FC("get_price", {"ticker": "LINK"})),
    NLQuery("s09", "폴리곤 가격 얼마야", "simple",
            FC("get_price", {"ticker": "MATIC"})),
    NLQuery("s10", "BNB 현재가", "simple",
            FC("get_price", {"ticker": "BNB"})),

    # ── Simple: place_order market (s11~s17) ─────────────────────────────────
    NLQuery("s11", "BTC 0.1개 시장가 매수해줘", "simple",
            FC("place_order", {"ticker": "BTC", "side": "buy", "qty": 0.1, "order_type": "market"})),
    NLQuery("s12", "ETH 1개 바로 사줘", "simple",
            FC("place_order", {"ticker": "ETH", "side": "buy", "qty": 1.0, "order_type": "market"})),
    NLQuery("s13", "SOL 5개 시장가 매도", "simple",
            FC("place_order", {"ticker": "SOL", "side": "sell", "qty": 5.0, "order_type": "market"})),
    NLQuery("s14", "XRP 500개 즉시 매수", "simple",
            FC("place_order", {"ticker": "XRP", "side": "buy", "qty": 500.0, "order_type": "market"})),
    NLQuery("s15", "도지코인 10000개 바로 팔아", "simple",
            FC("place_order", {"ticker": "DOGE", "side": "sell", "qty": 10000.0, "order_type": "market"})),
    NLQuery("s16", "ADA 100개 시장가 매수", "simple",
            FC("place_order", {"ticker": "ADA", "side": "buy", "qty": 100.0, "order_type": "market"})),
    NLQuery("s17", "BNB 2개 시장가로 팔아줘", "simple",
            FC("place_order", {"ticker": "BNB", "side": "sell", "qty": 2.0, "order_type": "market"})),

    # ── Simple: get_balance (s18~s22) ────────────────────────────────────────
    NLQuery("s18", "잔고 확인해줘", "simple",
            FC("get_balance", {"asset": None})),
    NLQuery("s19", "BTC 보유량 얼마야", "simple",
            FC("get_balance", {"asset": "BTC"})),
    NLQuery("s20", "ETH 잔고 알려줘", "simple",
            FC("get_balance", {"asset": "ETH"})),
    NLQuery("s21", "SOL 몇 개 있어", "simple",
            FC("get_balance", {"asset": "SOL"})),
    NLQuery("s22", "전체 보유 자산 확인", "simple",
            FC("get_balance", {"asset": None})),

    # ── Simple: get_portfolio (s23~s25) ──────────────────────────────────────
    NLQuery("s23", "내 포트폴리오 보여줘", "simple",
            FC("get_portfolio", {})),
    NLQuery("s24", "자산 현황 알려줘", "simple",
            FC("get_portfolio", {})),
    NLQuery("s25", "투자 현황 전체 보여줘", "simple",
            FC("get_portfolio", {})),

    # ── Simple: get_order_history (s26~s28) ──────────────────────────────────
    NLQuery("s26", "내 주문 내역 보여줘", "simple",
            FC("get_order_history", {"ticker": None, "limit": 10})),
    NLQuery("s27", "BTC 거래 내역 보여줘", "simple",
            FC("get_order_history", {"ticker": "BTC", "limit": 10})),
    NLQuery("s28", "최근 주문 내역", "simple",
            FC("get_order_history", {"ticker": None, "limit": 10})),

    # ── Simple: get_market_info (s29~s30) ────────────────────────────────────
    NLQuery("s29", "비트코인 시장 정보 알려줘", "simple",
            FC("get_market_info", {"ticker": "BTC"})),
    NLQuery("s30", "ETH 시장 정보", "simple",
            FC("get_market_info", {"ticker": "ETH"})),

    # ── Simple: cancel_order (s31~s32) ───────────────────────────────────────
    NLQuery("s31", "주문번호 ORD-001 취소해줘", "simple",
            FC("cancel_order", {"order_id": "ORD-001", "ticker": None, "side": None, "order_type": None})),
    NLQuery("s32", "ORD-999 주문 취소", "simple",
            FC("cancel_order", {"order_id": "ORD-999", "ticker": None, "side": None, "order_type": None})),

    # ── Simple: get_price 추가 (s33) ─────────────────────────────────────────
    NLQuery("s33", "트론 현재가", "simple",
            FC("get_price", {"ticker": "TRX"})),

    # ── Medium: place_order limit (m01~m10) ──────────────────────────────────
    NLQuery("m01", "BTC 5만달러에 0.1개 지정가 매수해줘", "medium",
            FC("place_order", {"ticker": "BTC", "side": "buy", "qty": 0.1, "order_type": "limit", "price": 50000.0})),
    NLQuery("m02", "ETH 3000달러에 1개 지정가 사줘", "medium",
            FC("place_order", {"ticker": "ETH", "side": "buy", "qty": 1.0, "order_type": "limit", "price": 3000.0})),
    NLQuery("m03", "SOL 150달러에 10개 지정가 매수", "medium",
            FC("place_order", {"ticker": "SOL", "side": "buy", "qty": 10.0, "order_type": "limit", "price": 150.0})),
    NLQuery("m04", "BTC 4만8천달러에 0.05개 지정가 매도", "medium",
            FC("place_order", {"ticker": "BTC", "side": "sell", "qty": 0.05, "order_type": "limit", "price": 48000.0})),
    NLQuery("m05", "XRP 0.8달러에 1000개 지정가 사줘", "medium",
            FC("place_order", {"ticker": "XRP", "side": "buy", "qty": 1000.0, "order_type": "limit", "price": 0.8})),
    NLQuery("m06", "ETH 3500달러에 0.5개 지정가 매도", "medium",
            FC("place_order", {"ticker": "ETH", "side": "sell", "qty": 0.5, "order_type": "limit", "price": 3500.0})),
    NLQuery("m07", "DOGE 0.15달러에 5000개 지정가 매수", "medium",
            FC("place_order", {"ticker": "DOGE", "side": "buy", "qty": 5000.0, "order_type": "limit", "price": 0.15})),
    NLQuery("m08", "AVAX 25달러에 20개 지정가 매도", "medium",
            FC("place_order", {"ticker": "AVAX", "side": "sell", "qty": 20.0, "order_type": "limit", "price": 25.0})),
    NLQuery("m09", "LINK 15달러에 50개 지정가 매수", "medium",
            FC("place_order", {"ticker": "LINK", "side": "buy", "qty": 50.0, "order_type": "limit", "price": 15.0})),
    NLQuery("m10", "BNB 250달러에 3개 지정가 사줘", "medium",
            FC("place_order", {"ticker": "BNB", "side": "buy", "qty": 3.0, "order_type": "limit", "price": 250.0})),

    # ── Medium: set_alert (m11~m20) ──────────────────────────────────────────
    NLQuery("m11", "BTC 6만달러 이상 되면 알려줘", "medium",
            FC("set_alert", {"ticker": "BTC", "condition": "gte", "threshold": 60000.0})),
    NLQuery("m12", "ETH 2500달러 밑으로 내려오면 알림 줘", "medium",
            FC("set_alert", {"ticker": "ETH", "condition": "lte", "threshold": 2500.0})),
    NLQuery("m13", "XRP 1달러 넘으면 알림 설정해줘", "medium",
            FC("set_alert", {"ticker": "XRP", "condition": "gte", "threshold": 1.0})),
    NLQuery("m14", "SOL 200달러 찍으면 알려줘", "medium",
            FC("set_alert", {"ticker": "SOL", "condition": "gte", "threshold": 200.0})),
    NLQuery("m15", "DOGE 0.1달러 이하로 떨어지면 알림", "medium",
            FC("set_alert", {"ticker": "DOGE", "condition": "lte", "threshold": 0.1})),
    NLQuery("m16", "BTC 4만달러 아래로 내려가면 알려줘", "medium",
            FC("set_alert", {"ticker": "BTC", "condition": "lte", "threshold": 40000.0})),
    NLQuery("m17", "AVAX 30달러 돌파하면 알림 줘", "medium",
            FC("set_alert", {"ticker": "AVAX", "condition": "gte", "threshold": 30.0})),
    NLQuery("m18", "LINK 20달러 이상이면 알려줘", "medium",
            FC("set_alert", {"ticker": "LINK", "condition": "gte", "threshold": 20.0})),
    NLQuery("m19", "BNB 300달러 넘으면 알림 설정", "medium",
            FC("set_alert", {"ticker": "BNB", "condition": "gte", "threshold": 300.0})),
    NLQuery("m20", "ETH 4000달러 돌파 알림 걸어줘", "medium",
            FC("set_alert", {"ticker": "ETH", "condition": "gte", "threshold": 4000.0})),

    # ── Medium: set_conditional_order 동일코인 (m21~m27) ─────────────────────
    NLQuery("m21", "BTC 7만달러 찍으면 BTC 0.1개 시장가 팔아", "medium",
            FC("set_conditional_order", {
                "trigger_ticker": "BTC", "trigger_condition": "gte", "trigger_price": 70000.0,
                "action_ticker": "BTC", "action_side": "sell", "action_qty": 0.1, "action_order_type": "market",
            })),
    NLQuery("m22", "ETH 2000달러 되면 ETH 1개 시장가 매수해줘", "medium",
            FC("set_conditional_order", {
                "trigger_ticker": "ETH", "trigger_condition": "lte", "trigger_price": 2000.0,
                "action_ticker": "ETH", "action_side": "buy", "action_qty": 1.0, "action_order_type": "market",
            })),
    NLQuery("m23", "SOL 100달러 이하로 내려오면 SOL 5개 시장가 매수", "medium",
            FC("set_conditional_order", {
                "trigger_ticker": "SOL", "trigger_condition": "lte", "trigger_price": 100.0,
                "action_ticker": "SOL", "action_side": "buy", "action_qty": 5.0, "action_order_type": "market",
            })),
    NLQuery("m24", "XRP 2달러 넘으면 XRP 500개 시장가 매도", "medium",
            FC("set_conditional_order", {
                "trigger_ticker": "XRP", "trigger_condition": "gte", "trigger_price": 2.0,
                "action_ticker": "XRP", "action_side": "sell", "action_qty": 500.0, "action_order_type": "market",
            })),
    NLQuery("m25", "DOGE 0.2달러 돌파하면 DOGE 10000개 시장가 팔아", "medium",
            FC("set_conditional_order", {
                "trigger_ticker": "DOGE", "trigger_condition": "gte", "trigger_price": 0.2,
                "action_ticker": "DOGE", "action_side": "sell", "action_qty": 10000.0, "action_order_type": "market",
            })),
    NLQuery("m26", "LINK 10달러 이하 되면 LINK 100개 시장가 매수", "medium",
            FC("set_conditional_order", {
                "trigger_ticker": "LINK", "trigger_condition": "lte", "trigger_price": 10.0,
                "action_ticker": "LINK", "action_side": "buy", "action_qty": 100.0, "action_order_type": "market",
            })),
    NLQuery("m27", "ADA 0.5달러 이하로 내려오면 ADA 1000개 시장가 사줘", "medium",
            FC("set_conditional_order", {
                "trigger_ticker": "ADA", "trigger_condition": "lte", "trigger_price": 0.5,
                "action_ticker": "ADA", "action_side": "buy", "action_qty": 1000.0, "action_order_type": "market",
            })),

    # ── Medium: get_order_history with params (m28~m30) ──────────────────────
    NLQuery("m28", "BTC 최근 주문 5건 보여줘", "medium",
            FC("get_order_history", {"ticker": "BTC", "limit": 5})),
    NLQuery("m29", "ETH 거래 내역 20건", "medium",
            FC("get_order_history", {"ticker": "ETH", "limit": 20})),
    NLQuery("m30", "최근 주문 50건 보여줘", "medium",
            FC("get_order_history", {"ticker": None, "limit": 50})),

    # ── Medium: cancel_order (m31~m33) ───────────────────────────────────────
    NLQuery("m31", "BTC 지정가 매수 주문 전부 취소해줘", "medium",
            FC("cancel_order", {"order_id": None, "ticker": "BTC", "side": "buy", "order_type": "limit"})),
    NLQuery("m32", "ETH 매도 주문 취소", "medium",
            FC("cancel_order", {"order_id": None, "ticker": "ETH", "side": "sell", "order_type": None})),
    NLQuery("m33", "SOL 오픈 주문 전부 취소", "medium",
            FC("cancel_order", {"order_id": None, "ticker": "SOL", "side": None, "order_type": None})),

    # ── Complex: set_conditional_order 크로스애셋 (c01~c15) ──────────────────
    NLQuery("c01", "BTC 6만달러 넘으면 ETH 1개 시장가 팔아", "complex",
            FC("set_conditional_order", {
                "trigger_ticker": "BTC", "trigger_condition": "gte", "trigger_price": 60000.0,
                "action_ticker": "ETH", "action_side": "sell", "action_qty": 1.0, "action_order_type": "market",
            })),
    NLQuery("c02", "ETH 3000달러 이상이면 SOL 10개 시장가 매수해줘", "complex",
            FC("set_conditional_order", {
                "trigger_ticker": "ETH", "trigger_condition": "gte", "trigger_price": 3000.0,
                "action_ticker": "SOL", "action_side": "buy", "action_qty": 10.0, "action_order_type": "market",
            })),
    NLQuery("c03", "BTC 4만달러 아래로 내려가면 XRP 1000개 시장가 팔아", "complex",
            FC("set_conditional_order", {
                "trigger_ticker": "BTC", "trigger_condition": "lte", "trigger_price": 40000.0,
                "action_ticker": "XRP", "action_side": "sell", "action_qty": 1000.0, "action_order_type": "market",
            })),
    NLQuery("c04", "SOL 200달러 돌파하면 BTC 0.05개 시장가 매수", "complex",
            FC("set_conditional_order", {
                "trigger_ticker": "SOL", "trigger_condition": "gte", "trigger_price": 200.0,
                "action_ticker": "BTC", "action_side": "buy", "action_qty": 0.05, "action_order_type": "market",
            })),
    NLQuery("c05", "XRP 1달러 넘으면 DOGE 50000개 시장가 팔아", "complex",
            FC("set_conditional_order", {
                "trigger_ticker": "XRP", "trigger_condition": "gte", "trigger_price": 1.0,
                "action_ticker": "DOGE", "action_side": "sell", "action_qty": 50000.0, "action_order_type": "market",
            })),
    NLQuery("c06", "ETH 2500달러 이하로 내려오면 LINK 200개 시장가 매수", "complex",
            FC("set_conditional_order", {
                "trigger_ticker": "ETH", "trigger_condition": "lte", "trigger_price": 2500.0,
                "action_ticker": "LINK", "action_side": "buy", "action_qty": 200.0, "action_order_type": "market",
            })),
    NLQuery("c07", "SOL 150달러 이하 되면 ADA 2000개 시장가 사줘", "complex",
            FC("set_conditional_order", {
                "trigger_ticker": "SOL", "trigger_condition": "lte", "trigger_price": 150.0,
                "action_ticker": "ADA", "action_side": "buy", "action_qty": 2000.0, "action_order_type": "market",
            })),
    NLQuery("c08", "AVAX 20달러 이하로 내려오면 AVAX 50개 시장가 추가 매수", "complex",
            FC("set_conditional_order", {
                "trigger_ticker": "AVAX", "trigger_condition": "lte", "trigger_price": 20.0,
                "action_ticker": "AVAX", "action_side": "buy", "action_qty": 50.0, "action_order_type": "market",
            })),
    NLQuery("c09", "BNB 200달러 이하로 내려오면 BTC 0.1개 시장가 팔아", "complex",
            FC("set_conditional_order", {
                "trigger_ticker": "BNB", "trigger_condition": "lte", "trigger_price": 200.0,
                "action_ticker": "BTC", "action_side": "sell", "action_qty": 0.1, "action_order_type": "market",
            })),
    NLQuery("c10", "LINK 20달러 돌파하면 LINK 500개 시장가 매도", "complex",
            FC("set_conditional_order", {
                "trigger_ticker": "LINK", "trigger_condition": "gte", "trigger_price": 20.0,
                "action_ticker": "LINK", "action_side": "sell", "action_qty": 500.0, "action_order_type": "market",
            })),
    NLQuery("c11", "XRP 2달러 넘으면 BTC 0.05개 시장가 매수", "complex",
            FC("set_conditional_order", {
                "trigger_ticker": "XRP", "trigger_condition": "gte", "trigger_price": 2.0,
                "action_ticker": "BTC", "action_side": "buy", "action_qty": 0.05, "action_order_type": "market",
            })),
    NLQuery("c12", "ETH 5000달러 찍으면 SOL 50개 시장가 팔아", "complex",
            FC("set_conditional_order", {
                "trigger_ticker": "ETH", "trigger_condition": "gte", "trigger_price": 5000.0,
                "action_ticker": "SOL", "action_side": "sell", "action_qty": 50.0, "action_order_type": "market",
            })),
    NLQuery("c13", "BTC 6만5천달러 돌파하면 ETH 0.5개 시장가 매수", "complex",
            FC("set_conditional_order", {
                "trigger_ticker": "BTC", "trigger_condition": "gte", "trigger_price": 65000.0,
                "action_ticker": "ETH", "action_side": "buy", "action_qty": 0.5, "action_order_type": "market",
            })),
    NLQuery("c14", "MATIC 1달러 이하로 내려오면 MATIC 3000개 시장가 매수", "complex",
            FC("set_conditional_order", {
                "trigger_ticker": "MATIC", "trigger_condition": "lte", "trigger_price": 1.0,
                "action_ticker": "MATIC", "action_side": "buy", "action_qty": 3000.0, "action_order_type": "market",
            })),
    NLQuery("c15", "SOL 250달러 되면 BNB 5개 시장가 팔아", "complex",
            FC("set_conditional_order", {
                "trigger_ticker": "SOL", "trigger_condition": "gte", "trigger_price": 250.0,
                "action_ticker": "BNB", "action_side": "sell", "action_qty": 5.0, "action_order_type": "market",
            })),

    # ── Complex: cancel_order 복합 조건 (c16~c20) ────────────────────────────
    NLQuery("c16", "BTC 관련 미체결 주문 전부 취소해줘", "complex",
            FC("cancel_order", {"order_id": None, "ticker": "BTC", "side": None, "order_type": None})),
    NLQuery("c17", "ETH 매수 주문 전부 취소", "complex",
            FC("cancel_order", {"order_id": None, "ticker": "ETH", "side": "buy", "order_type": None})),
    NLQuery("c18", "SOL 지정가 미체결 주문 취소", "complex",
            FC("cancel_order", {"order_id": None, "ticker": "SOL", "side": None, "order_type": "limit"})),
    NLQuery("c19", "전체 지정가 주문 다 취소해줘", "complex",
            FC("cancel_order", {"order_id": None, "ticker": None, "side": None, "order_type": "limit"})),
    NLQuery("c20", "XRP 매도 지정가 주문 취소", "complex",
            FC("cancel_order", {"order_id": None, "ticker": "XRP", "side": "sell", "order_type": "limit"})),

    # ── Complex: get_market_info (c21~c25) ───────────────────────────────────
    NLQuery("c21", "비트코인 오늘 고가 저가 거래량 알려줘", "complex",
            FC("get_market_info", {"ticker": "BTC"})),
    NLQuery("c22", "ETH 24시간 변동률 알려줘", "complex",
            FC("get_market_info", {"ticker": "ETH"})),
    NLQuery("c23", "SOL 시가총액 얼마야", "complex",
            FC("get_market_info", {"ticker": "SOL"})),
    NLQuery("c24", "BTC 오늘 시가 종가 알려줘", "complex",
            FC("get_market_info", {"ticker": "BTC"})),
    NLQuery("c25", "DOGE 24시간 거래량과 변동률 알려줘", "complex",
            FC("get_market_info", {"ticker": "DOGE"})),

    # ── Complex: get_order_history 상세 조건 (c26~c30) ───────────────────────
    NLQuery("c26", "BTC 거래 내역 최근 100건 보여줘", "complex",
            FC("get_order_history", {"ticker": "BTC", "limit": 100})),
    NLQuery("c27", "ETH 주문 내역 30건 알려줘", "complex",
            FC("get_order_history", {"ticker": "ETH", "limit": 30})),
    NLQuery("c28", "최근 주문 내역 100건", "complex",
            FC("get_order_history", {"ticker": None, "limit": 100})),
    NLQuery("c29", "SOL 거래 내역 15건 보여줘", "complex",
            FC("get_order_history", {"ticker": "SOL", "limit": 15})),
    NLQuery("c30", "LINK 주문 내역 25건", "complex",
            FC("get_order_history", {"ticker": "LINK", "limit": 25})),

    # ── Complex: get_portfolio + get_balance 복합 활용 (c31~c34) ─────────────
    NLQuery("c31", "내 전체 포트폴리오 수익률 포함해서 보여줘", "complex",
            FC("get_portfolio", {})),
    NLQuery("c32", "현재 보유 자산 비중 분석해줘", "complex",
            FC("get_portfolio", {})),
    NLQuery("c33", "내 평균 매수가 전체 확인", "complex",
            FC("get_portfolio", {})),
    NLQuery("c34", "전체 평가 손익 알려줘", "complex",
            FC("get_portfolio", {})),
]

QUERY_MAP = {q.id: q for q in QUERIES}
QUERIES_BY_DIFFICULTY = {
    "simple": [q for q in QUERIES if q.difficulty == "simple"],
    "medium": [q for q in QUERIES if q.difficulty == "medium"],
    "complex": [q for q in QUERIES if q.difficulty == "complex"],
}

assert len(QUERIES) == 100, f"Expected 100 queries, got {len(QUERIES)}"
assert len([q for q in QUERIES if q.difficulty == "simple"]) == 33
assert len([q for q in QUERIES if q.difficulty == "medium"]) == 33
assert len([q for q in QUERIES if q.difficulty == "complex"]) == 34
