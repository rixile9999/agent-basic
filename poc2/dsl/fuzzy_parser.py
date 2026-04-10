"""
Crypto Fuzzy DSL Parser — Grammar-Extended Fallback Layer
poc1의 fuzzy_parser와 동일 구조, 코인 도메인 룰 적용.
"""
from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Any

from poc2.dsl.parser import parse_dsl, _TICKER_MAP, _CONDITION_MAP, _ORDER_TYPE_MAP
from poc2.models import FunctionCall

log = logging.getLogger(__name__)
GRAMMAR_FILE = Path(__file__).parent / "grammar_extensions.json"
_grammar_cache: dict | None = None


def reload_grammar() -> dict:
    global _grammar_cache
    _grammar_cache = json.loads(GRAMMAR_FILE.read_text(encoding="utf-8"))
    return _grammar_cache


def _get_grammar() -> dict:
    global _grammar_cache
    if _grammar_cache is None:
        _grammar_cache = json.loads(GRAMMAR_FILE.read_text(encoding="utf-8"))
    return _grammar_cache


def _rule_entries(section: dict) -> dict[str, Any]:
    return {k: v for k, v in section.items() if not k.startswith("_")}


def apply_grammar_rules(dsl: dict, width: str, rules: dict) -> tuple[dict, list[str]]:
    normalized = dict(dsl)
    applied: list[str] = []

    # field_renames
    renames = _rule_entries(rules.get("field_renames", {}).get(width, {}))
    for wrong, correct in renames.items():
        if wrong in normalized and correct not in normalized:
            normalized[correct] = normalized.pop(wrong)
            applied.append(f"field_rename[{width}]: {wrong!r} → {correct!r}")

    # ticker_aliases: asset, ticker, action_asset, target_asset 필드
    ticker_aliases = _rule_entries(rules.get("ticker_aliases", {}))
    for field in ("asset", "ticker", "action_asset", "trigger_ticker", "target_asset"):
        if field in normalized and isinstance(normalized[field], str):
            key = normalized[field].lower().strip()
            if key in ticker_aliases:
                entry = ticker_aliases[key]
                mapped = entry["maps_to"] if isinstance(entry, dict) else entry
                normalized[field] = mapped
                applied.append(f"ticker_alias[{field}]: {key!r} → {mapped!r}")

    # condition_aliases
    cond_aliases = _rule_entries(rules.get("condition_aliases", {}))
    for field in ("trigger_condition", "condition"):
        if field in normalized and isinstance(normalized[field], str):
            key = normalized[field].lower().strip()
            if key in cond_aliases:
                entry = cond_aliases[key]
                mapped = entry["maps_to"] if isinstance(entry, dict) else entry
                normalized[field] = mapped
                applied.append(f"condition_alias[{field}]: {key!r} → {mapped!r}")

    # order_type_aliases
    ot_aliases = _rule_entries(rules.get("order_type_aliases", {}))
    for field in ("price_type", "order_type", "action_order_type"):
        if field in normalized and isinstance(normalized[field], str):
            key = normalized[field].lower().strip()
            if key in ot_aliases:
                entry = ot_aliases[key]
                mapped = entry["maps_to"] if isinstance(entry, dict) else entry
                normalized[field] = mapped
                applied.append(f"order_type_alias[{field}]: {key!r} → {mapped!r}")

    # verb_aliases (medium)
    if width == "medium" and "verb" in normalized:
        verb_aliases = _rule_entries(rules.get("verb_aliases", {}))
        verb_key = str(normalized["verb"]).lower().strip()
        if verb_key in verb_aliases:
            entry = verb_aliases[verb_key]
            mapped = entry["maps_to"] if isinstance(entry, dict) else entry
            normalized["verb"] = mapped
            applied.append(f"verb_alias: {verb_key!r} → {mapped!r}")

    # value_aliases: amount, price, qty, trigger_price 필드
    val_aliases = _rule_entries(rules.get("value_aliases", {}))
    for field in ("amount", "price", "qty", "trigger_price", "action_qty", "target_amount"):
        if field in normalized and isinstance(normalized[field], str):
            key = normalized[field].lower().strip()
            if key in val_aliases:
                entry = val_aliases[key]
                mapped = entry["maps_to"] if isinstance(entry, dict) else entry
                normalized[field] = mapped
                applied.append(f"value_alias[{field}]: {key!r} → {mapped!r}")

    return normalized, applied


def parse_dsl_fuzzy(dsl: dict, width: str) -> tuple[FunctionCall, list[str]]:
    """
    2-pass 파서. strict 실패 시 grammar rules 적용 후 재시도.
    Returns: (FunctionCall, applied_rules)
    """
    try:
        return parse_dsl(dsl, width), []
    except Exception as strict_err:
        strict_msg = str(strict_err)

    grammar = _get_grammar()
    rules = grammar.get("rules", {})
    normalized, applied = apply_grammar_rules(dsl, width, rules)

    if not applied:
        raise ValueError(f"{strict_msg} (grammar 룰 없음)")

    try:
        result = parse_dsl(normalized, width)
        log.debug("[fuzzy] 적용된 룰: %s", applied)
        return result, applied
    except Exception as fuzzy_err:
        raise ValueError(
            f"strict 실패({strict_msg}) + fuzzy 실패({fuzzy_err}). 적용 시도 룰: {applied}"
        ) from fuzzy_err
