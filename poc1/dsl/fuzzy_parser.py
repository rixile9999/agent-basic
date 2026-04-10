"""
Fuzzy DSL Parser — Grammar-Extended Fallback Layer

아키텍처:
  NL → LLM → DSL (모델 출력, 스키마 위반 가능)
                 ↓
         [Pass 1: Strict Parser] ──성공──→ FunctionCall
                 ↓ 실패
         [grammar_extensions.json 룰 적용]
                 ↓
         [Pass 2: Strict Parser] ──성공──→ FunctionCall
                 ↓ 실패
         ValueError (grammar_extender로 분석 대상)

grammar_extensions.json은 라운드마다 grammar_extender.py로 확장.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from poc1.dsl.parser import parse_dsl
from poc1.models import FunctionCall

log = logging.getLogger(__name__)

GRAMMAR_FILE = Path(__file__).parent / "grammar_extensions.json"

_grammar_cache: dict | None = None


def reload_grammar() -> dict:
    """grammar_extensions.json을 강제 재로드."""
    global _grammar_cache
    _grammar_cache = json.loads(GRAMMAR_FILE.read_text(encoding="utf-8"))
    return _grammar_cache


def _get_grammar() -> dict:
    global _grammar_cache
    if _grammar_cache is None:
        _grammar_cache = json.loads(GRAMMAR_FILE.read_text(encoding="utf-8"))
    return _grammar_cache


def _rule_entries(section: dict) -> dict[str, Any]:
    """_comment, _ebnf 키를 제외한 실제 룰만 반환."""
    return {k: v for k, v in section.items() if not k.startswith("_")}


def apply_grammar_rules(dsl: dict, width: str, rules: dict) -> tuple[dict, list[str]]:
    """
    grammar_extensions.json 룰을 DSL dict에 적용.

    Returns:
        (normalized_dsl, applied_rules)
        applied_rules: 적용된 룰 설명 목록 (빈 리스트 = 변경 없음)
    """
    normalized = dict(dsl)
    applied: list[str] = []

    # ── field_renames: 모델이 잘못된 필드명 사용 ─────────────────────────────
    renames = _rule_entries(rules.get("field_renames", {}).get(width, {}))
    for wrong, correct in renames.items():
        if wrong in normalized and correct not in normalized:
            normalized[correct] = normalized.pop(wrong)
            applied.append(f"field_rename[{width}]: {wrong!r} → {correct!r}")

    # ── value_aliases: value 필드에 문자열이 온 경우 ─────────────────────────
    if "value" in normalized and isinstance(normalized["value"], str):
        val_key = normalized["value"].lower().strip()
        aliases = _rule_entries(rules.get("value_aliases", {}))
        if val_key in aliases:
            entry = aliases[val_key]
            mapped = entry["maps_to"] if isinstance(entry, dict) else entry
            normalized["value"] = mapped
            applied.append(f"value_alias: {val_key!r} → {mapped!r}")

    # ── state_aliases: state 필드 비표준 문자열 ──────────────────────────────
    if "state" in normalized and isinstance(normalized["state"], str):
        st_key = normalized["state"].lower().strip()
        aliases = _rule_entries(rules.get("state_aliases", {}))
        if st_key in aliases:
            entry = aliases[st_key]
            mapped = entry["maps_to"] if isinstance(entry, dict) else entry
            normalized["state"] = mapped
            applied.append(f"state_alias: {st_key!r} → {mapped!r}")

    # ── verb_aliases: medium DSL verb enum 외 값 ────────────────────────────
    if width == "medium" and "verb" in normalized:
        verb_key = str(normalized["verb"]).lower().strip()
        aliases = _rule_entries(rules.get("verb_aliases", {}))
        if verb_key in aliases:
            entry = aliases[verb_key]
            mapped = entry["maps_to"] if isinstance(entry, dict) else entry
            normalized["verb"] = mapped
            applied.append(f"verb_alias: {verb_key!r} → {mapped!r}")

    # ── target_aliases: medium DSL target enum 외 값 ────────────────────────
    if width == "medium" and "target" in normalized:
        target_key = str(normalized["target"]).lower().strip()
        aliases = _rule_entries(rules.get("target_aliases", {}))
        if target_key in aliases:
            entry = aliases[target_key]
            mapped = entry["maps_to"] if isinstance(entry, dict) else entry
            normalized["target"] = mapped
            applied.append(f"target_alias: {target_key!r} → {mapped!r}")

    # ── location_aliases: 위치 표현 추가 정규화 ─────────────────────────────
    for loc_field in ("location", "zone", "room"):
        if loc_field in normalized and isinstance(normalized[loc_field], str):
            loc_key = normalized[loc_field].lower().strip()
            aliases = _rule_entries(rules.get("location_aliases", {}))
            if loc_key in aliases:
                entry = aliases[loc_key]
                mapped = entry["maps_to"] if isinstance(entry, dict) else entry
                normalized[loc_field] = mapped
                applied.append(f"location_alias[{loc_field}]: {loc_key!r} → {mapped!r}")

    return normalized, applied


def parse_dsl_fuzzy(
    dsl: dict,
    width: str,
) -> tuple[FunctionCall, list[str]]:
    """
    Grammar-extended DSL 파서 (2-pass).

    Pass 1: 기존 strict 파서로 시도.
    Pass 2: grammar_extensions.json 룰 적용 후 재시도.
    두 pass 모두 실패하면 ValueError.

    Returns:
        (FunctionCall, applied_rules)
        applied_rules == [] → strict 파싱 성공 (룰 미적용)
        applied_rules != [] → fuzzy 파싱 성공 (적용된 룰 목록)

    Raises:
        ValueError: 두 pass 모두 실패
    """
    # Pass 1: strict
    try:
        return parse_dsl(dsl, width), []
    except Exception as strict_err:
        strict_msg = str(strict_err)

    # Pass 2: grammar 룰 적용
    grammar = _get_grammar()
    rules = grammar.get("rules", {})
    normalized, applied = apply_grammar_rules(dsl, width, rules)

    if not applied:
        # 룰이 아무것도 적용되지 않음 → strict 에러 그대로
        raise ValueError(f"{strict_msg} (grammar 룰 없음)")

    try:
        result = parse_dsl(normalized, width)
        log.debug("[fuzzy] 적용된 룰: %s", applied)
        return result, applied
    except Exception as fuzzy_err:
        raise ValueError(
            f"strict 실패({strict_msg}) + fuzzy 실패({fuzzy_err}). "
            f"적용 시도 룰: {applied}"
        ) from fuzzy_err
