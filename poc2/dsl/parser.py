"""
Crypto DSL → FunctionCall 결정론적 파서

각 DSL 폭(narrow/medium/wide)별 매핑 규칙 코드로 구현.
LLM 불필요 — 100% 재현 가능한 변환.
"""
from __future__ import annotations
from poc2.models import FunctionCall

# ── 정규화 테이블 ──────────────────────────────────────────────────────────────

_TICKER_MAP: dict[str, str] = {
    # 한국어 이름
    "비트코인": "BTC", "bitcoin": "BTC",
    "이더리움": "ETH", "ethereum": "ETH",
    "리플": "XRP", "ripple": "XRP",
    "솔라나": "SOL", "solana": "SOL",
    "도지코인": "DOGE", "doge": "DOGE", "dogecoin": "DOGE",
    "에이다": "ADA", "카르다노": "ADA", "cardano": "ADA",
    "아발란체": "AVAX", "avalanche": "AVAX",
    "체인링크": "LINK", "chainlink": "LINK",
    "폴리곤": "MATIC", "매틱": "MATIC", "polygon": "MATIC",
    "바이낸스코인": "BNB", "binance": "BNB",
    "트론": "TRX", "tron": "TRX",
    "샌드박스": "SAND", "sandbox": "SAND",
    "슈이": "SUI", "sui": "SUI",
    "앱토스": "APT", "aptos": "APT",
    # 대문자 자기 자신 (그대로 통과)
    "BTC": "BTC", "ETH": "ETH", "XRP": "XRP", "SOL": "SOL",
    "DOGE": "DOGE", "ADA": "ADA", "AVAX": "AVAX", "LINK": "LINK",
    "MATIC": "MATIC", "BNB": "BNB", "TRX": "TRX", "SAND": "SAND",
    "SUI": "SUI", "APT": "APT",
}

_CONDITION_MAP: dict[str, str] = {
    # 이상/이하
    "gte": "gte", ">=": "gte",
    "이상": "gte", "이상이면": "gte", "이상일때": "gte",
    "넘으면": "gte", "넘을때": "gte", "넘었을때": "gte",
    "돌파": "gte", "돌파하면": "gte", "돌파시": "gte",
    "찍으면": "gte", "도달하면": "gte",
    "lte": "lte", "<=": "lte",
    "이하": "lte", "이하로": "lte", "이하면": "lte", "이하일때": "lte",
    "밑으로": "lte", "아래로": "lte", "아래로내려오면": "lte",
    "내려오면": "lte", "내려가면": "lte", "떨어지면": "lte",
    "하락하면": "lte",
    # 초과/미만
    "gt": "gt", ">": "gt", "초과": "gt",
    "lt": "lt", "<": "lt", "미만": "lt",
}

_ORDER_TYPE_MAP: dict[str, str] = {
    "market": "market", "시장가": "market", "즉시": "market",
    "바로": "market", "즉시체결": "market",
    "limit": "limit", "지정가": "limit",
    "stop_loss": "stop_loss", "손절": "stop_loss", "스탑": "stop_loss",
    "take_profit": "take_profit", "익절": "take_profit",
}

_SIDE_MAP: dict[str, str] = {
    "buy": "buy", "매수": "buy", "사다": "buy", "사줘": "buy",
    "매입": "buy", "구매": "buy",
    "sell": "sell", "매도": "sell", "팔다": "sell", "팔아": "sell",
    "판매": "sell",
}


def _ticker(val: str | None, default: str | None = None) -> str | None:
    if val is None:
        return default
    return _TICKER_MAP.get(str(val).strip(), str(val).strip().upper())


def _condition(val: str | None) -> str | None:
    if val is None:
        return None
    return _CONDITION_MAP.get(str(val).strip().lower(), str(val).strip())


def _order_type(val: str | None, default: str = "market") -> str:
    if val is None:
        return default
    return _ORDER_TYPE_MAP.get(str(val).strip().lower(), str(val).strip())


def _side(val: str | None) -> str | None:
    if val is None:
        return None
    return _SIDE_MAP.get(str(val).strip().lower(), str(val).strip())


def _safe_float(val, default: float | None = None) -> float | None:
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return default


def _safe_int(val, default: int = 10) -> int:
    f = _safe_float(val, float(default))
    return int(f) if f is not None else default


# ── Narrow 파서 ───────────────────────────────────────────────────────────────

def parse_narrow(dsl: dict) -> FunctionCall:
    """
    Narrow DSL: {"function": "<name>", "args": {...}}
    ticker/side/condition 정규화만 수행.
    """
    fn = dsl.get("function", "")
    args: dict = dict(dsl.get("args", {}) or {})

    # ticker 류 정규화
    for key in ("ticker", "asset", "action_ticker", "trigger_ticker"):
        if key in args and args[key]:
            args[key] = _ticker(args[key])

    # side 정규화
    for key in ("side", "action_side"):
        if key in args and args[key]:
            args[key] = _side(args[key]) or args[key]

    # condition 정규화
    for key in ("condition", "trigger_condition"):
        if key in args and args[key]:
            args[key] = _condition(args[key]) or args[key]

    # order_type 정규화
    for key in ("order_type", "action_order_type"):
        if key in args and args[key]:
            args[key] = _order_type(args[key])

    return FunctionCall(name=fn, arguments=args)


# ── Medium 파서 ───────────────────────────────────────────────────────────────

_MEDIUM_VERB_TO_FN = {
    "buy":           "place_order",
    "sell":          "place_order",
    "cancel":        "cancel_order",
    "get_price":     "get_price",
    "get_balance":   "get_balance",
    "get_portfolio": "get_portfolio",
    "get_history":   "get_order_history",
    "get_market":    "get_market_info",
    "set_alert":     "set_alert",
    "set_condition": "set_conditional_order",
}

def parse_medium(dsl: dict) -> FunctionCall:
    """
    Medium DSL: verb 기반 → function 결정.
    """
    verb = str(dsl.get("verb", "")).lower().strip()
    asset = _ticker(dsl.get("asset")) or "BTC"

    fn = _MEDIUM_VERB_TO_FN.get(verb)
    if fn is None:
        raise ValueError(f"Medium DSL 알 수 없는 verb: {verb!r}")

    # ── place_order ──────────────────────────────────────────────────────────
    if fn == "place_order":
        side = "buy" if verb == "buy" else "sell"
        qty = _safe_float(dsl.get("qty"))
        if qty is None:
            raise ValueError(f"place_order: qty 없음 (dsl={dsl})")
        ot = _order_type(dsl.get("price_type"), "market")
        price = _safe_float(dsl.get("price"))
        args: dict = {"ticker": asset, "side": side, "qty": qty, "order_type": ot}
        if ot != "market" and price is not None:
            args["price"] = price
        return FunctionCall("place_order", args)

    # ── cancel_order ─────────────────────────────────────────────────────────
    if fn == "cancel_order":
        args = {
            "order_id":   dsl.get("order_id") or None,
            "ticker":     _ticker(dsl.get("asset")) if dsl.get("asset") else None,
            "side":       _side(dsl.get("side_filter")),
            "order_type": _order_type(dsl.get("order_type_filter")) if dsl.get("order_type_filter") else None,
        }
        return FunctionCall("cancel_order", args)

    # ── get_price ─────────────────────────────────────────────────────────────
    if fn == "get_price":
        return FunctionCall("get_price", {"ticker": asset})

    # ── get_balance ───────────────────────────────────────────────────────────
    if fn == "get_balance":
        a = _ticker(dsl.get("asset")) if dsl.get("asset") else None
        return FunctionCall("get_balance", {"asset": a})

    # ── get_portfolio ─────────────────────────────────────────────────────────
    if fn == "get_portfolio":
        return FunctionCall("get_portfolio", {})

    # ── get_order_history ─────────────────────────────────────────────────────
    if fn == "get_order_history":
        ticker = _ticker(dsl.get("asset")) if dsl.get("asset") not in (None, "", "all") else None
        limit = _safe_int(dsl.get("limit"), 10)
        return FunctionCall("get_order_history", {"ticker": ticker, "limit": limit})

    # ── get_market_info ───────────────────────────────────────────────────────
    if fn == "get_market_info":
        return FunctionCall("get_market_info", {"ticker": asset})

    # ── set_alert ─────────────────────────────────────────────────────────────
    if fn == "set_alert":
        cond = _condition(dsl.get("trigger_condition"))
        threshold = _safe_float(dsl.get("trigger_price"))
        if cond is None or threshold is None:
            raise ValueError(f"set_alert: condition/threshold 없음 (dsl={dsl})")
        return FunctionCall("set_alert", {"ticker": asset, "condition": cond, "threshold": threshold})

    # ── set_conditional_order ─────────────────────────────────────────────────
    if fn == "set_conditional_order":
        cond = _condition(dsl.get("trigger_condition"))
        trigger_price = _safe_float(dsl.get("trigger_price"))
        action_asset = _ticker(dsl.get("action_asset")) or asset
        action_side = _side(dsl.get("action_side"))
        action_qty = _safe_float(dsl.get("action_qty"))
        if None in (cond, trigger_price, action_side, action_qty):
            raise ValueError(f"set_conditional_order: 필수 필드 누락 (dsl={dsl})")
        return FunctionCall("set_conditional_order", {
            "trigger_ticker":    asset,
            "trigger_condition": cond,
            "trigger_price":     trigger_price,
            "action_ticker":     action_asset,
            "action_side":       action_side,
            "action_qty":        action_qty,
            "action_order_type": "market",
        })

    raise ValueError(f"Medium 파서 미구현 fn: {fn!r}")


# ── Wide 파서 ─────────────────────────────────────────────────────────────────

_WIDE_BUY  = {"buy", "매수", "사다", "사줘", "구매", "purchase"}
_WIDE_SELL = {"sell", "매도", "팔다", "팔아", "판매"}
_WIDE_PRICE_INTENT  = {"get_price", "price", "시세", "현재가", "얼마", "가격"}
_WIDE_BALANCE_INTENT = {"get_balance", "balance", "잔고", "보유", "얼마나"}
_WIDE_PORTFOLIO_INTENT = {"get_portfolio", "portfolio", "포트폴리오", "자산현황", "투자현황", "수익률"}
_WIDE_HISTORY_INTENT = {"get_history", "history", "내역", "거래내역", "주문내역"}
_WIDE_MARKET_INTENT  = {"get_market", "market_info", "시장정보", "거래량", "변동률", "시가총액", "고가", "저가"}
_WIDE_ALERT_INTENT   = {"set_alert", "alert", "알림", "알려줘", "알림설정"}
_WIDE_CANCEL_INTENT  = {"cancel", "취소", "주문취소"}
_WIDE_COND_INTENT    = {"conditional", "조건부", "when", "이면", "되면", "넘으면", "내려오면", "돌파"}


def _intent_matches(intent_lower: str, keywords: set) -> bool:
    return any(k in intent_lower for k in keywords)


def _parse_trigger(trigger_str: str | None) -> tuple[str | None, str | None, float | None]:
    """
    trigger 문자열 파싱.
    예: "BTC >= 60000" → ("BTC", "gte", 60000.0)
        "ETH drops below 2500" → ("ETH", "lte", 2500.0)
    Returns: (ticker, condition, price)
    """
    if not trigger_str:
        return None, None, None

    import re
    s = trigger_str.strip()

    # "TICKER op PRICE" 패턴
    m = re.match(r"([A-Z가-힣]+)\s*(>=|<=|>|<|이상|이하|gte|lte|gt|lt)\s*([\d,.]+)", s, re.IGNORECASE)
    if m:
        tok, op, price_str = m.group(1), m.group(2), m.group(3)
        return (
            _ticker(tok),
            _condition(op),
            _safe_float(price_str.replace(",", "")),
        )

    # "TICKER rises above/drops below PRICE"
    m2 = re.search(r"([\d,.]+)", s)
    price = _safe_float(m2.group(1).replace(",", "")) if m2 else None

    # ticker 추출 (첫 단어 시도)
    tok_match = re.match(r"(\S+)", s)
    tok = _ticker(tok_match.group(1)) if tok_match else None

    # condition 추출
    sl = s.lower()
    if any(k in sl for k in ("above", ">=", "이상", "넘", "돌파", "gte")):
        cond = "gte"
    elif any(k in sl for k in ("below", "<=", "이하", "밑", "내려", "lte")):
        cond = "lte"
    elif ">" in sl:
        cond = "gt"
    elif "<" in sl:
        cond = "lt"
    else:
        cond = None

    return tok, cond, price


def parse_wide(dsl: dict) -> FunctionCall:
    """
    Wide DSL: intent 자유 문자열 → 함수 결정.
    """
    intent = str(dsl.get("intent", "")).lower().strip()
    asset_raw = dsl.get("asset", "")
    asset = _ticker(asset_raw) or "BTC"
    amount = _safe_float(dsl.get("amount"))
    price = _safe_float(dsl.get("price"))
    trigger_str = dsl.get("trigger", "")
    target_asset_raw = dsl.get("target_asset")
    target_asset = _ticker(target_asset_raw) if target_asset_raw else None
    target_amount = _safe_float(dsl.get("target_amount"))
    modifiers: list[str] = [m.lower() for m in (dsl.get("modifiers") or [])]

    # ── 포트폴리오 ──────────────────────────────────────────────────────────
    if _intent_matches(intent, _WIDE_PORTFOLIO_INTENT):
        return FunctionCall("get_portfolio", {})

    # ── 조건부 주문 (trigger 필드 있거나 intent에 조건 키워드) ────────────────
    has_trigger = bool(trigger_str)
    intent_is_conditional = _intent_matches(intent, _WIDE_COND_INTENT)

    if has_trigger or intent_is_conditional:
        trig_ticker, trig_cond, trig_price = _parse_trigger(trigger_str)

        # intent에서 트리거 정보 추론 (trigger 필드 없을 때)
        if trig_ticker is None:
            trig_ticker = asset
        if trig_price is None:
            trig_price = price

        # 알림만 (action 정보 없음)
        if not target_asset and amount is None and target_amount is None:
            if trig_cond and trig_price is not None:
                return FunctionCall("set_alert", {
                    "ticker": trig_ticker or asset,
                    "condition": trig_cond,
                    "threshold": trig_price,
                })

        # 조건부 주문
        action_tk = target_asset or asset
        action_qty = target_amount or amount
        action_side = "sell" if _intent_matches(intent, _WIDE_SELL) else "buy"

        if trig_cond and trig_price is not None and action_qty is not None:
            return FunctionCall("set_conditional_order", {
                "trigger_ticker":    trig_ticker or asset,
                "trigger_condition": trig_cond,
                "trigger_price":     trig_price,
                "action_ticker":     action_tk,
                "action_side":       action_side,
                "action_qty":        action_qty,
                "action_order_type": "market",
            })

    # ── 알림 설정 ─────────────────────────────────────────────────────────────
    if _intent_matches(intent, _WIDE_ALERT_INTENT):
        trig_ticker, trig_cond, trig_price = _parse_trigger(trigger_str)
        cond = trig_cond or ("gte" if price else None)
        threshold = trig_price or price
        if cond and threshold is not None:
            return FunctionCall("set_alert", {
                "ticker": trig_ticker or asset,
                "condition": cond,
                "threshold": threshold,
            })

    # ── 취소 ─────────────────────────────────────────────────────────────────
    if _intent_matches(intent, _WIDE_CANCEL_INTENT):
        order_id = next((m for m in modifiers if m.startswith("ord-")), None)
        ot = None
        if "지정가" in intent or "limit" in intent:
            ot = "limit"
        elif "시장가" in intent or "market" in intent:
            ot = "market"
        side_filter = None
        if _intent_matches(intent, _WIDE_BUY):
            side_filter = "buy"
        elif _intent_matches(intent, _WIDE_SELL):
            side_filter = "sell"
        ticker = asset if asset_raw else None
        return FunctionCall("cancel_order", {
            "order_id": order_id,
            "ticker":   ticker,
            "side":     side_filter,
            "order_type": ot,
        })

    # ── 주문 내역 ─────────────────────────────────────────────────────────────
    if _intent_matches(intent, _WIDE_HISTORY_INTENT):
        limit = _safe_int(amount or dsl.get("limit"), 10)
        ticker = asset if asset_raw else None
        return FunctionCall("get_order_history", {"ticker": ticker, "limit": limit})

    # ── 시장 정보 ─────────────────────────────────────────────────────────────
    if _intent_matches(intent, _WIDE_MARKET_INTENT):
        return FunctionCall("get_market_info", {"ticker": asset})

    # ── 잔고 조회 ─────────────────────────────────────────────────────────────
    if _intent_matches(intent, _WIDE_BALANCE_INTENT):
        a = asset if asset_raw else None
        return FunctionCall("get_balance", {"asset": a})

    # ── 현재가 조회 ───────────────────────────────────────────────────────────
    if _intent_matches(intent, _WIDE_PRICE_INTENT):
        return FunctionCall("get_price", {"ticker": asset})

    # ── 매수 ─────────────────────────────────────────────────────────────────
    if _intent_matches(intent, _WIDE_BUY):
        if amount is None:
            raise ValueError(f"Wide buy: amount 없음 (dsl={dsl})")
        ot = "limit" if price is not None else "market"
        args: dict = {"ticker": asset, "side": "buy", "qty": amount, "order_type": ot}
        if ot == "limit":
            args["price"] = price
        return FunctionCall("place_order", args)

    # ── 매도 ─────────────────────────────────────────────────────────────────
    if _intent_matches(intent, _WIDE_SELL):
        if amount is None:
            raise ValueError(f"Wide sell: amount 없음 (dsl={dsl})")
        ot = "limit" if price is not None else "market"
        args = {"ticker": asset, "side": "sell", "qty": amount, "order_type": ot}
        if ot == "limit":
            args["price"] = price
        return FunctionCall("place_order", args)

    raise ValueError(f"Wide DSL 파싱 실패: intent={intent!r}, asset={asset_raw!r}")


# ── 통합 진입점 ───────────────────────────────────────────────────────────────

def parse_dsl(dsl: dict, width: str) -> FunctionCall:
    if width == "narrow":
        return parse_narrow(dsl)
    elif width == "medium":
        return parse_medium(dsl)
    elif width == "wide":
        return parse_wide(dsl)
    else:
        raise ValueError(f"알 수 없는 DSL 폭: {width!r}")
