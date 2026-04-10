"""
Grammar Extender — 반복적 DSL 문법 확장 도구

워크플로우 (수렴할 때까지 반복):
  Round N:
    1. 실험 실행: python -m poc1.main
    2. 실패 분석: python -m poc1.dsl.grammar_extender analyze [--results path]
       → poc1/dsl/proposed_round_N.json 생성
    3. 사람이 proposed_round_N.json 검토 (잘못된 항목 삭제)
    4. 룰 적용:  python -m poc1.dsl.grammar_extender apply --proposed proposed_round_N.json --round N
       → grammar_extensions.json 업데이트
    5. 재실험 → 개선 확인

서브커맨드:
  analyze  : 최신(또는 지정) 결과에서 실패 분류 + 룰 제안 → proposed_round_N.json
  apply    : proposed JSON의 룰을 grammar_extensions.json에 병합
  stats    : 현재 grammar_extensions.json 통계 출력

사용 예:
  python -m poc1.dsl.grammar_extender analyze
  python -m poc1.dsl.grammar_extender analyze --results poc1/results/results_XYZ.json
  python -m poc1.dsl.grammar_extender apply --proposed poc1/dsl/proposed_round_1.json --round 1
  python -m poc1.dsl.grammar_extender stats
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

# ── 경로 ──────────────────────────────────────────────────────────────────────

GRAMMAR_FILE = Path(__file__).parent / "grammar_extensions.json"
RESULTS_DIR = Path(__file__).parent.parent / "results"
DSL_DIR = Path(__file__).parent

# ── 알려진 동의어 사전 (자동 confidence=high 판정용) ──────────────────────────

_VERB_SYNONYMS: dict[str, str] = {
    # 켜다 계열
    "켜줘": "turn_on", "켜": "turn_on", "켜라": "turn_on", "켜주세요": "turn_on",
    "turn on": "turn_on", "on": "turn_on",
    "시작": "start", "시작해줘": "start", "시작해": "start",
    "활성화": "activate", "활성화해줘": "activate",
    # 끄다 계열
    "꺼줘": "turn_off", "꺼": "turn_off", "꺼라": "turn_off", "꺼주세요": "turn_off",
    "turn off": "turn_off", "off": "turn_off",
    "종료": "stop", "종료해줘": "stop", "그만해": "stop",
    # 올리다/내리다
    "높여줘": "increase", "올려줘": "increase", "올려": "increase", "높여": "increase",
    "높이다": "increase",
    "낮춰줘": "decrease", "줄여줘": "decrease", "낮춰": "decrease", "줄여": "decrease",
    "낮추다": "decrease",
    # 설정
    "설정해": "set", "설정해줘": "set", "바꿔줘": "set", "변경해줘": "set",
    # 잠금
    "잠궈": "lock", "잠가줘": "lock", "잠그다": "lock",
    "열어줘": "unlock", "열어": "unlock", "열다": "unlock",
    # 재생
    "틀어줘": "play", "재생해줘": "play", "틀어": "play",
    "멈춰": "stop", "정지": "stop",
    # 조회
    "알려줘": "query", "확인해줘": "check", "확인": "check",
    "취소해줘": "cancel",
}

_TARGET_SYNONYMS: dict[str, str] = {
    # 조명
    "불": "light", "전등": "light", "조명": "light", "전구": "light",
    "lights": "lights",
    # 온도
    "에어컨": "ac", "냉방기": "ac", "냉방": "ac",
    "보일러": "heater", "난방기": "heater", "히터": "heater",
    "에어컨 온도": "temperature", "실내 온도": "temperature",
    # 가전
    "로봇청소기": "robot_vacuum", "청소기": "robot_vacuum",
    "세탁기": "washing_machine",
    "식기세척기": "dishwasher",
    "공기청정기": "air_purifier",
    "텔레비전": "tv", "television": "tv",
    # 문
    "문": "door", "현관문": "front_door", "현관": "front_door",
    "뒷문": "back_door",
    "차고문": "garage",
    # 타이머
    "타이머": "timer", "알람": "alarm",
    # 센서
    "온도계": "temperature_sensor", "온도 센서": "temperature_sensor",
    "습도계": "humidity_sensor",
    "동작 감지": "motion_sensor", "모션 센서": "motion_sensor",
    # 미디어
    "음악": "music", "노래": "music",
    "영상": "video", "영화": "video",
    # 씬
    "씬": "scene", "모드": "scene",
}

# Medium DSL 스키마 enum — 이미 유효한 값은 alias 제안에서 제외
_MEDIUM_VERB_ENUM = {
    "turn_on", "turn_off", "toggle", "set", "adjust", "increase", "decrease",
    "lock", "unlock", "play", "stop", "pause", "check", "get", "query",
    "activate", "start", "cancel",
}
_MEDIUM_TARGET_ENUM = {
    "light", "lights", "temperature", "ac", "heater", "air_conditioner",
    "tv", "washing_machine", "dishwasher", "air_purifier", "robot_vacuum",
    "timer", "alarm", "temperature_sensor", "humidity_sensor", "air_quality",
    "co2", "motion_sensor", "music", "video", "media",
    "door", "front_door", "back_door", "garage", "scene",
}

_VALUE_SYNONYMS: dict[str, Any] = {
    # 밝기
    "어둡게": 30, "어둡게 해줘": 30, "어둡게 유지": 30, "낮은 밝기": 30,
    "밝게": 100, "밝게 해줘": 100, "밝히줘": 100, "최대 밝기": 100,
    "적당히": 50, "중간": 50, "기본값": 50,
    "low": 30, "high": 100,
    # 온/오프
    "on": 1, "켜": 1, "켜줘": 1, "turn_on": 1,
    "off": 0, "꺼": 0, "꺼줘": 0, "turn_off": 0,
    # 조작
    "줄여줘": -1, "낮춰줘": -1, "down": -1,
    "올려줘": 1, "높여줘": 1, "up": 1,
    # 모드
    "냉방": "cool", "난방": "heat", "자동": "auto",
    # 위치 (value에 잘못 들어온 경우)
    "실외": "outdoor", "야외": "outdoor", "outside": "outdoor",
    "실내": "living_room", "안": "living_room", "inside": "living_room",
    # 특수
    "current": None, "차이": None, "온도": None, "타이머": None,
    "energy_saving_mode": "away",
    "밥 짓는 시간": 40, "밥 짓는 동안": 40,
    "라면 끓이는 시간": 3,
    "몇 시간": 60,
    "적당한 온도": 24, "적정 온도": 22, "적정 수면 온도": 20,
    "춥다": 24, "덥다": 22,
    "아늑한": "reading", "편안한": "sleep", "안전하게": "away",
    "밝히기": 100,
}

_STATE_SYNONYMS: dict[str, bool | str] = {
    "켜": True, "켜줘": True, "on": True, "open": True, "true": True, "1": True,
    "꺼": False, "꺼줘": False, "off": False, "false": False, "0": False,
    "잠금": True, "잠가": True,
    "해제": False, "열음": False,
}

# ── 에러 패턴 분류 ─────────────────────────────────────────────────────────────

_RE_MEDIUM_FAIL = re.compile(r"verb='([^']*)', target='([^']*)'")
# _safe_float 두 가지 에러 포맷 모두 매칭:
#   "could not convert string to float: 'X'"
#   "Cannot convert 'X' to float"
_RE_FLOAT_FAIL = re.compile(r"(?:float: |Cannot convert )'([^']+)'")
_RE_FUZZY_FAIL = re.compile(r"strict 실패\((.+?)\) \+ fuzzy 실패")


def classify_failure(error: str, dsl_output: dict | None) -> dict:
    """
    에러 메시지와 DSL 출력을 분석해 실패 유형을 반환.

    Returns:
        {
            "type": str,           # 실패 유형
            "recoverable": bool,   # 문법 확장으로 복구 가능 여부
            "details": dict,       # 추출된 세부 정보
            "proposed_rule": dict | None  # 자동 제안 룰
        }
    """
    if not error:
        return {"type": "no_error", "recoverable": False, "details": {}, "proposed_rule": None}

    # ── Medium DSL 파싱 실패 (verb/target 조합 매핑 불가) ──────────────────
    m = _RE_MEDIUM_FAIL.search(error)
    if m:
        verb, target = m.group(1), m.group(2)
        proposed = {}

        # 이미 유효한 enum 값은 alias 불필요 — target/verb 각각 독립 판단
        if verb not in ("", "none") and verb not in _MEDIUM_VERB_ENUM:
            proposed["verb_aliases"] = {
                verb: {
                    "maps_to": _VERB_SYNONYMS.get(verb),
                    "confidence": "high" if verb in _VERB_SYNONYMS else "low",
                }
            }
        if target not in ("", "none") and target not in _MEDIUM_TARGET_ENUM:
            proposed["target_aliases"] = {
                target: {
                    "maps_to": _TARGET_SYNONYMS.get(target),
                    "confidence": "high" if target in _TARGET_SYNONYMS else "low",
                }
            }
        return {
            "type": "medium_unknown_verb_target",
            "recoverable": bool(proposed),
            "details": {"verb": verb, "target": target,
                        "note": "verb/target already in enum" if not proposed else ""},
            "proposed_rule": proposed if proposed else None,
        }

    # ── float 변환 실패 (value 필드에 문자열) ─────────────────────────────
    m = _RE_FLOAT_FAIL.search(error)
    if m:
        val = m.group(1)
        mapped = _VALUE_SYNONYMS.get(val.lower())
        confidence = "high" if val.lower() in _VALUE_SYNONYMS else "low"
        return {
            "type": "value_string_not_numeric",
            "recoverable": True,
            "details": {"value": val},
            "proposed_rule": {
                "value_aliases": {
                    val.lower(): {
                        "maps_to": mapped,
                        "confidence": confidence,
                    }
                }
            },
        }

    # ── JSON 파싱 실패 ─────────────────────────────────────────────────────
    if "JSON 파싱 실패" in error or "json" in error.lower():
        return {"type": "json_parse_error", "recoverable": False, "details": {"error": error}, "proposed_rule": None}

    # ── fuzzy도 실패한 경우 ────────────────────────────────────────────────
    m = _RE_FUZZY_FAIL.search(error)
    if m:
        inner = m.group(1)
        return {
            "type": "fuzzy_also_failed",
            "recoverable": False,
            "details": {"inner_error": inner, "dsl": dsl_output},
            "proposed_rule": None,
        }

    # ── DSL 구조 이상 (필드 누락 등) ──────────────────────────────────────
    if dsl_output is not None:
        # field_rename 후보 탐지
        medium_wrong_fields = _detect_field_renames(dsl_output)
        if medium_wrong_fields:
            return {
                "type": "wrong_field_names",
                "recoverable": True,
                "details": {"wrong_fields": medium_wrong_fields},
                "proposed_rule": {"field_renames": medium_wrong_fields},
            }

    return {
        "type": "other",
        "recoverable": False,
        "details": {"error": error[:200]},
        "proposed_rule": None,
    }


def _detect_field_renames(dsl: dict) -> dict:
    """DSL에서 잘못된 필드명을 탐지 (필드 리네임 후보)."""
    _MEDIUM_CANONICAL = {"verb", "target", "location", "value", "state", "params"}
    _MEDIUM_ALIASES = {
        "action": "verb", "command": "verb", "operation": "verb",
        "object": "target", "device": "target", "thing": "target",
        "room": "location", "place": "location", "where": "location",
        "amount": "value", "setting": "value", "level": "value",
    }
    _WIDE_CANONICAL = {"intent", "subject", "location", "value", "modifiers"}
    _WIDE_ALIASES = {
        "action": "intent", "purpose": "intent", "goal": "intent",
        "object": "subject", "target": "subject", "device": "subject",
        "room": "location", "place": "location",
        "params": "modifiers", "options": "modifiers",
    }

    result: dict[str, dict] = {}
    for wrong, correct in {**_MEDIUM_ALIASES, **_WIDE_ALIASES}.items():
        if wrong in dsl and correct not in dsl:
            # 어느 DSL 타입인지 판단 어려우므로 두 타입 모두에 제안
            for width in ("medium", "wide"):
                if width not in result:
                    result[width] = {}
                result[width][wrong] = correct
    return result


# ── analyze 서브커맨드 ─────────────────────────────────────────────────────────

def cmd_analyze(args: argparse.Namespace) -> None:
    """결과 파일에서 실패 분류 + 룰 제안."""
    # 결과 파일 선택
    if args.results:
        results_path = Path(args.results)
    else:
        json_files = sorted(RESULTS_DIR.glob("results_*.json"), reverse=True)
        if not json_files:
            print("결과 파일 없음. 실험을 먼저 실행하세요.")
            sys.exit(1)
        results_path = json_files[0]

    print(f"분석 대상: {results_path}")
    data = json.loads(results_path.read_text(encoding="utf-8"))
    raw: list[dict] = data.get("raw", [])

    # 에러가 있는 레코드만 추출
    failures = [r for r in raw if r.get("error")]
    if not failures:
        print("에러 없음! 문법 확장이 필요하지 않습니다.")
        return

    print(f"총 {len(raw)}건 중 실패 {len(failures)}건 ({len(failures)/len(raw)*100:.1f}%)")

    # 분류
    classified: list[dict] = []
    for rec in failures:
        cls = classify_failure(rec["error"], rec.get("dsl_output"))
        classified.append({
            "query_id": rec["query_id"],
            "method": rec["method"],
            "model": rec["model"],
            "error": rec["error"],
            "dsl_output": rec.get("dsl_output"),
            "classification": cls,
        })

    recoverable = [c for c in classified if c["classification"]["recoverable"]]
    unrecoverable = [c for c in classified if not c["classification"]["recoverable"]]

    print(f"  복구 가능: {len(recoverable)}건")
    print(f"  복구 불가: {len(unrecoverable)}건")

    # 제안 룰 수집 (타입별 집계)
    proposed_rules: dict[str, dict] = defaultdict(dict)

    for item in recoverable:
        rule = item["classification"].get("proposed_rule") or {}
        qid = item["query_id"]
        method = item["method"]

        for rule_type, entries in rule.items():
            for key, value in entries.items():
                if key not in proposed_rules[rule_type]:
                    proposed_rules[rule_type][key] = {
                        "maps_to": value.get("maps_to") if isinstance(value, dict) else value,
                        "confidence": value.get("confidence", "low") if isinstance(value, dict) else "low",
                        "occurrences": 0,
                        "evidence": [],
                    }
                proposed_rules[rule_type][key]["occurrences"] += 1
                proposed_rules[rule_type][key]["evidence"].append(f"{qid} / {method}")

    # 현재 grammar에 이미 있는 룰 제외
    grammar = json.loads(GRAMMAR_FILE.read_text(encoding="utf-8"))
    existing_rules = grammar.get("rules", {})
    for rule_type, entries in list(proposed_rules.items()):
        existing = existing_rules.get(rule_type, {})
        for key in list(entries.keys()):
            if key in existing and not key.startswith("_"):
                del entries[key]
    proposed_rules = {k: v for k, v in proposed_rules.items() if v}

    # 출력 저장
    round_n = grammar.get("rounds_completed", 0) + 1
    output = {
        "round": round_n,
        "source_results": str(results_path.name),
        "analyzed_at": datetime.now().isoformat(),
        "summary": {
            "total_failures": len(failures),
            "recoverable": len(recoverable),
            "unrecoverable": len(unrecoverable),
            "new_rules_proposed": sum(len(v) for v in proposed_rules.values()),
        },
        "proposed_rules": dict(proposed_rules),
        "unresolvable": [
            {
                "query_id": c["query_id"],
                "method": c["method"],
                "model": c["model"],
                "type": c["classification"]["type"],
                "error": c["error"][:200],
                "dsl_output": c["dsl_output"],
            }
            for c in unrecoverable
        ],
    }

    out_path = DSL_DIR / f"proposed_round_{round_n}.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"\n제안 파일 저장: {out_path}")
    print(f"제안된 새 룰: {output['summary']['new_rules_proposed']}개")

    if proposed_rules:
        print("\n[제안 룰 미리보기]")
        for rule_type, entries in proposed_rules.items():
            print(f"  {rule_type}:")
            for key, val in list(entries.items())[:5]:
                maps_to = val["maps_to"]
                conf = val["confidence"]
                occ = val["occurrences"]
                print(f"    {key!r} → {maps_to!r}  (confidence={conf}, 발생={occ}회)")
            if len(entries) > 5:
                print(f"    ... 외 {len(entries)-5}개")

    print(f"\n검토 후: python -m poc1.dsl.grammar_extender apply --proposed {out_path} --round {round_n}")


# ── apply 서브커맨드 ───────────────────────────────────────────────────────────

def cmd_apply(args: argparse.Namespace) -> None:
    """proposed JSON의 룰을 grammar_extensions.json에 병합."""
    proposed_path = Path(args.proposed)
    if not proposed_path.exists():
        print(f"파일 없음: {proposed_path}")
        sys.exit(1)

    proposed = json.loads(proposed_path.read_text(encoding="utf-8"))
    grammar = json.loads(GRAMMAR_FILE.read_text(encoding="utf-8"))

    rules = grammar.setdefault("rules", {})
    round_n = args.round or proposed.get("round", grammar.get("rounds_completed", 0) + 1)
    added_count = 0
    skipped_count = 0

    for rule_type, entries in proposed.get("proposed_rules", {}).items():
        if rule_type == "field_renames":
            # field_renames는 width별 중첩 구조
            for width, renames in entries.items():
                target_section = rules.setdefault("field_renames", {}).setdefault(width, {})
                for wrong, correct in renames.items():
                    if wrong.startswith("_"):
                        continue
                    if wrong in target_section:
                        skipped_count += 1
                        continue
                    target_section[wrong] = correct
                    added_count += 1
                    print(f"  [추가] field_renames[{width}]: {wrong!r} → {correct!r}")
        else:
            target_section = rules.setdefault(rule_type, {})
            for key, val in entries.items():
                if key.startswith("_"):
                    continue
                if key in target_section and not key.startswith("_"):
                    skipped_count += 1
                    continue
                maps_to = val["maps_to"] if isinstance(val, dict) else val
                target_section[key] = {
                    "maps_to": maps_to,
                    "round": round_n,
                    "confidence": val.get("confidence", "unknown") if isinstance(val, dict) else "unknown",
                    "occurrences": val.get("occurrences", 1) if isinstance(val, dict) else 1,
                }
                added_count += 1
                print(f"  [추가] {rule_type}: {key!r} → {maps_to!r}")

    # round_log 업데이트
    grammar["rounds_completed"] = round_n
    grammar.setdefault("round_log", []).append({
        "round": round_n,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "source_results": proposed.get("source_results"),
        "rules_added": added_count,
        "rules_skipped": skipped_count,
    })

    GRAMMAR_FILE.write_text(json.dumps(grammar, ensure_ascii=False, indent=2))
    print(f"\n완료: {added_count}개 추가, {skipped_count}개 중복 스킵")
    print(f"grammar_extensions.json 업데이트 (Round {round_n})")


# ── stats 서브커맨드 ───────────────────────────────────────────────────────────

def cmd_stats(args: argparse.Namespace) -> None:
    """현재 grammar_extensions.json 통계 출력."""
    grammar = json.loads(GRAMMAR_FILE.read_text(encoding="utf-8"))
    rules = grammar.get("rules", {})

    print(f"=== Grammar Extensions 현황 (Round {grammar.get('rounds_completed', 0)}) ===\n")

    rule_types = ["value_aliases", "verb_aliases", "target_aliases", "location_aliases", "state_aliases"]
    for rt in rule_types:
        entries = {k: v for k, v in rules.get(rt, {}).items() if not k.startswith("_")}
        print(f"{rt}: {len(entries)}개")
        for key, val in list(entries.items())[:3]:
            maps_to = val["maps_to"] if isinstance(val, dict) else val
            round_added = val.get("round", "?") if isinstance(val, dict) else "?"
            print(f"  {key!r} → {maps_to!r}  (R{round_added})")
        if len(entries) > 3:
            print(f"  ... 외 {len(entries)-3}개")

    # field_renames
    renames = rules.get("field_renames", {})
    total_renames = sum(
        len({k: v for k, v in w.items() if not k.startswith("_")})
        for w in renames.values()
        if isinstance(w, dict)
    )
    print(f"field_renames: {total_renames}개")

    print(f"\n[Round 히스토리]")
    for entry in grammar.get("round_log", []):
        print(f"  Round {entry['round']} ({entry['date']}): +{entry.get('rules_added', 0)}개")


# ── 진입점 ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="DSL Grammar Extender — 반복적 문법 확장 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # analyze
    p_analyze = sub.add_parser("analyze", help="실패 분석 + 룰 제안")
    p_analyze.add_argument("--results", help="분석할 결과 JSON 경로 (없으면 최신)")

    # apply
    p_apply = sub.add_parser("apply", help="제안 룰을 grammar_extensions.json에 병합")
    p_apply.add_argument("--proposed", required=True, help="proposed_round_N.json 경로")
    p_apply.add_argument("--round", type=int, help="라운드 번호 (없으면 자동)")

    # stats
    sub.add_parser("stats", help="현재 grammar_extensions.json 통계")

    args = parser.parse_args()

    if args.cmd == "analyze":
        cmd_analyze(args)
    elif args.cmd == "apply":
        cmd_apply(args)
    elif args.cmd == "stats":
        cmd_stats(args)


if __name__ == "__main__":
    main()
