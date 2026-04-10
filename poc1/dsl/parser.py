"""
DSL → FunctionCall 결정론적 파서

각 DSL 폭 (narrow/medium/wide) 별 매핑 규칙을 코드로 구현.
LLM 불필요 — 100% 재현 가능한 변환.
"""
from poc1.models import FunctionCall

# ── 공통 정규화 테이블 ─────────────────────────────────────────────────────────

_ROOM_MAP = {
    "living_room": "living_room", "거실": "living_room",
    "bedroom": "bedroom", "침실": "bedroom", "침방": "bedroom",
    "kitchen": "kitchen", "부엌": "kitchen", "주방": "kitchen",
    "bathroom": "bathroom", "화장실": "bathroom",
    "outdoor": "outdoor", "야외": "outdoor", "밖": "outdoor",
    "garage": "garage", "차고": "garage",
    "all": "all", "전체": "all", "집 전체": "all",
}

_DEVICE_MAP = {
    "tv": "tv", "텔레비전": "tv", "television": "tv",
    "washing_machine": "washing_machine", "세탁기": "washing_machine",
    "dishwasher": "dishwasher", "식기세척기": "dishwasher",
    "air_purifier": "air_purifier", "공기청정기": "air_purifier",
    "robot_vacuum": "robot_vacuum", "로봇청소기": "robot_vacuum", "청소기": "robot_vacuum",
}

_SCENE_MAP = {
    "morning": "morning", "아침": "morning",
    "movie": "movie", "영화": "movie",
    "sleep": "sleep", "취침": "sleep", "잠": "sleep",
    "away": "away", "외출": "away",
    "party": "party", "파티": "party",
    "reading": "reading", "독서": "reading",
}

_SENSOR_MAP = {
    "temperature": "temperature", "온도": "temperature",
    "humidity": "humidity", "습도": "humidity",
    "air_quality": "air_quality", "공기질": "air_quality",
    "co2": "co2",
    "motion": "motion", "동작": "motion",
}

_DOOR_MAP = {
    "front_door": "front_door", "현관문": "front_door", "현관": "front_door",
    "back_door": "back_door", "뒷문": "back_door",
    "garage": "garage", "차고문": "garage",
}

_ON_VERBS = {"turn_on", "on", "켜", "켜줘", "start", "activate", "enable", "open"}
_OFF_VERBS = {"turn_off", "off", "꺼", "꺼줘", "stop", "deactivate", "disable"}
_LOCK_VERBS = {"lock", "잠그다", "잠가", "잠금"}
_UNLOCK_VERBS = {"unlock", "열다", "열어", "해제"}

# ── 값 정규화 매핑 테이블 (LLM 이 숫자 대신 문자열을 출력하는 경우 대비) ─────────

_VALUE_STATE_MAP = {
    # 밝기 관련
    "어둡게": 30, "어둡게 해줘": 30, "어둡게 유지": 30, "낮은 밝기": 30,
    "밝게": 100, "밝게 해줘": 100, "밝히줘": 100, "최대 밝기": 100,
    "적당히": 50, "중간": 50, "기본값": 50,
    # 상태 관련 (on/off 를 숫자처럼 사용하는 경우)
    "on": 1, "켜": 1, "켜줘": 1, "turn_on": 1,
    "off": 0, "꺼": 0, "꺼줘": 0, "turn_off": 0,
    # 명령어/동사
    "줄여줘": -1, "낮춰줘": -1, "down": -1,
    "올려줘": 1, "높여줘": 1, "up": 1,
    "시켜줘": 1, "해줘": 1, "설정": 1,
    # 모드 관련
    "냉방": "cool", "난방": "heat", "자동": "auto",
    # 위치 관련 (value 로 잘못 들어온 경우)
    "실외": "outdoor", "야외": "outdoor", "outside": "outdoor",
    "실내": "living_room", "안": "living_room", "inside": "living_room",
    # 기타
    "차이": None, "타이머": None, "온도": None,
    "current": None,
    "low": 30, "high": 100,
    "energy_saving_mode": "away",
    "밥 짓는 시간": 40, "밥 짓는 동안": 40,
    "라면 끓이는 시간": 3,
    "몇 시간": 60,
    "적당한 온도": 24, "적정 온도": 22, "적정 수면 온도": 20,
    "춥다": 24, "덥다": 22,
    "아늑한": "reading", "편안한": "sleep", "안전하게": "away",
    "밝히기": 100, "꺼": 0, "켜": 1,
}


def _normalize_state_bool(val: str | bool | None, *, default: bool = True) -> bool:
    if isinstance(val, bool):
        return val
    if val is None:
        return default
    return str(val).lower() in ("on", "true", "1", "켜", "켜줘", "open", "unlock")


def _lookup(mapping: dict, key: str | None, default=None):
    if key is None:
        return default
    return mapping.get(str(key).lower(), mapping.get(str(key), default))


def _safe_float(value, default: float | None = None) -> float | None:
    """
    안전한 float 변환. 문자열, 불리언, 특수값 모두 처리.
    
    Args:
        value: 변환할 값
        default: 변환 실패 시 반환할 기본값 (None 이면 예외 발생)
    
    Returns:
        변환된 float 값 또는 default
    
    Raises:
        ValueError: default 가 None 이고 변환 불가능한 경우
    """
    if value is None:
        return default
    
    if isinstance(value, (int, float)):
        return float(value)
    
    if isinstance(value, bool):
        return float(value)
    
    str_val = str(value).lower().strip()
    
    # 매핑 테이블에서 검색
    if str_val in _VALUE_STATE_MAP:
        mapped = _VALUE_STATE_MAP[str_val]
        if mapped is None:
            return default
        if isinstance(mapped, (int, float)):
            return float(mapped)
        # 문자열 매핑 (mode 등) 은 별도 처리
        return mapped
    
    # 숫자 파싱 시도 - "24 도", "50%" 같은 경우 처리
    try:
        cleaned = str_val.replace("도", "").replace("%", "").replace("℃", "").replace("°f", "").strip()
        return float(cleaned)
    except ValueError:
        pass
    
    # 그래도 실패하면 default 반환
    if default is not None:
        return default
    
    # default 도 None 이면 예외 발생
    raise ValueError(f"Cannot convert '{value}' to float")


def _safe_int(value, default: int | None = None) -> int | None:
    """안전한 int 변환."""
    result = _safe_float(value, default)
    if result is None:
        return None
    return int(result)


# ── Narrow DSL 파서 ──────────────────────────────────────────────────────────

def parse_narrow(dsl: dict) -> FunctionCall:
    """
    Narrow DSL: {"function": "<name>", "args": {...}}
    function 이름이 실제 함수명과 동일 → args 만 그대로 전달.
    """
    fn = dsl.get("function", "")
    args: dict = dsl.get("args", {})

    # state 정규화 (문자열 → bool)
    if "state" in args and not isinstance(args["state"], bool):
        args = {**args, "state": _normalize_state_bool(args["state"])}
    if "locked" in args and not isinstance(args["locked"], bool):
        args = {**args, "locked": _normalize_state_bool(args["locked"])}

    # room/zone/location 정규화
    for key in ("room", "zone", "location"):
        if key in args:
            normalized = _lookup(_ROOM_MAP, args[key], args[key])
            args = {**args, key: normalized}

    return FunctionCall(name=fn, arguments=args)


# ── Medium DSL 파서 ──────────────────────────────────────────────────────────

def parse_medium(dsl: dict) -> FunctionCall:
    """
    Medium DSL: {"verb": ..., "target": ..., "location": ..., "value": ..., "state": ..., "params": {...}}
    verb + target 조합으로 함수 결정.
    """
    verb = str(dsl.get("verb", "")).lower()
    target = str(dsl.get("target", "")).lower()
    location = _lookup(_ROOM_MAP, dsl.get("location"), "living_room")
    value = dsl.get("value")
    state_str = dsl.get("state")
    params: dict = dsl.get("params", {}) or {}

    # ── 조명 ──────────────────────────────────────────────────────────────────
    if target in ("light", "lights", "조명", "불"):
        state = _normalize_state_bool(state_str, default=(verb not in _OFF_VERBS))
        args: dict = {"room": location, "state": state}
        brightness = params.get("brightness")
        if brightness is None and value is not None:
            brightness = _safe_int(value)
        if brightness is not None:
            args["brightness"] = int(brightness)
        return FunctionCall("control_light", args)

    # ── 온도 ──────────────────────────────────────────────────────────────────
    if target in ("temperature", "ac", "heater", "air_conditioner", "온도", "에어컨", "난방"):
        args = {"zone": location}
        if value is not None:
            temp = _safe_float(value, 24.0)
            if isinstance(temp, str):
                # mode 로 해석될 수 있는 경우
                args["value"] = 24.0
                if temp in ("cool", "heat", "auto"):
                    args["mode"] = temp
            else:
                args["value"] = temp
        else:
            args["value"] = 24.0
        mode = params.get("mode")
        if mode:
            args["mode"] = mode
        elif verb in ("increase", "올리다") or target in ("heater", "난방"):
            args["mode"] = "heat"
        elif verb in ("decrease", "낮추다") or target in ("ac", "air_conditioner", "에어컨"):
            args["mode"] = "cool"
        return FunctionCall("set_temperature", args)

    # ── 가전 ──────────────────────────────────────────────────────────────────
    device = _lookup(_DEVICE_MAP, target)
    if device:
        state = _normalize_state_bool(state_str, default=(verb not in _OFF_VERBS))
        args = {"device": device, "state": state}
        if location and location != "living_room":
            args["room"] = location
        return FunctionCall("control_appliance", args)

    # ── 타이머 ──────────────────────────────────────────────────────────────────
    if target in ("timer", "alarm", "타이머", "알람"):
        minutes = _safe_int(value, params.get("duration_minutes", 10))
        args = {"duration_minutes": int(minutes)}
        if "label" in params:
            args["label"] = params["label"]
        return FunctionCall("set_timer", args)

    # ── 센서 조회 ──────────────────────────────────────────────────────────────
    sensor = _lookup(_SENSOR_MAP, target)
    if sensor or verb in ("check", "get", "query"):
        sensor = sensor or "temperature"
        return FunctionCall("query_sensor", {"sensor_type": sensor, "location": location})

    # ── 미디어 ──────────────────────────────────────────────────────────────────
    if target in ("music", "video", "media", "음악", "영상", "영화", "라디오") or verb in ("play", "재생", "틀어"):
        device_out = params.get("device", "speaker")
        content = target if target not in ("speaker", "tv") else params.get("content", "music")
        args = {"content": content, "device": device_out}
        if value is not None:
            vol = _safe_int(value)
            if vol is not None:
                args["volume"] = vol
        return FunctionCall("play_media", args)

    # ── 문 ────────────────────────────────────────────────────────────────────
    door = _lookup(_DOOR_MAP, target, "front_door")
    if target in ("door", "front_door", "back_door", "garage", "문", "현관문", "뒷문"):
        locked = verb in _LOCK_VERBS or _normalize_state_bool(state_str, default=True)
        return FunctionCall("lock_door", {"location": door, "locked": locked})

    # ── 씬 ────────────────────────────────────────────────────────────────────
    if target in ("scene", "씬", "모드") or verb == "activate":
        scene = _lookup(_SCENE_MAP, params.get("name") or str(value or ""), "morning")
        return FunctionCall("set_scene", {"name": scene})

    raise ValueError(f"Medium DSL 파싱 실패: verb={verb!r}, target={target!r}")


# ── Wide DSL 파서 ───────────────────────────────────────────────────────────

_WIDE_INTENT_LIGHT = {"turn off light", "turn on light", "조명 끄기", "조명 켜기", "불 끄기", "불 켜기",
                      "dim", "brighten", "밝기 조절", "어둡게", "밝게"}
_WIDE_INTENT_TEMP = {"set temperature", "온도 설정", "냉방", "난방", "에어컨", "adjust temperature"}
_WIDE_INTENT_SCENE = {"set scene", "씬 설정", "모드 변경", "분위기 설정", "activate scene"}
_WIDE_INTENT_TIMER = {"set timer", "타이머", "알람 설정"}
_WIDE_INTENT_SENSOR = {"check", "query", "조회", "확인", "알려줘"}
_WIDE_INTENT_MEDIA = {"play", "재생", "음악", "영상"}
_WIDE_INTENT_DOOR = {"lock", "unlock", "잠금", "열기", "문 잠그기"}
_WIDE_INTENT_APPLIANCE = {"turn on appliance", "turn off appliance", "가전 제어"}


def parse_wide(dsl: dict) -> FunctionCall:
    """
    Wide DSL: {"intent": ..., "subject": ..., "location": ..., "value": ..., "modifiers": [...]}
    intent + subject 자유 문자열 → 키워드 매칭으로 함수 결정.
    """
    intent = str(dsl.get("intent", "")).lower()
    subject = str(dsl.get("subject", "")).lower()
    location_raw = dsl.get("location", "")
    location = _lookup(_ROOM_MAP, location_raw, "living_room")
    value = dsl.get("value")
    modifiers: list[str] = [m.lower() for m in (dsl.get("modifiers") or [])]

    combined = f"{intent} {subject}"

    # ── 조명 ──────────────────────────────────────────────────────────────────
    if any(k in combined for k in ("light", "불", "조명", "밝기", "dim", "bright")):
        state = not any(k in combined for k in ("off", "꺼", "끄", "어둡"))
        args: dict = {"room": location, "state": state}
        if value is not None:
            brightness = _safe_int(value)
            if brightness is not None:
                args["brightness"] = brightness
        elif "어둡" in combined or "dim" in combined:
            args["brightness"] = 30
        elif "밝게" in combined or "bright" in combined:
            args["brightness"] = 100
        return FunctionCall("control_light", args)

    # ── 씬 ────────────────────────────────────────────────────────────────────
    if any(k in combined for k in ("scene", "씬", "모드", "분위기", "준비", "세팅", "설정", "분위기")):
        scene_name = None
        for k, v in _SCENE_MAP.items():
            if k in combined:
                scene_name = v
                break
        if scene_name is None and value:
            mapped_value = _VALUE_STATE_MAP.get(str(value).lower())
            if isinstance(mapped_value, str) and mapped_value in _SCENE_MAP:
                scene_name = mapped_value
        scene_name = scene_name or "morning"
        return FunctionCall("set_scene", {"name": scene_name})

    # ── 온도 ──────────────────────────────────────────────────────────────────
    # 단, "check/query" 의도는 센서 조회로 처리
    if any(k in combined for k in ("temperature", "온도", "에어컨", "난방", "냉방", "ac", "heat", "cool")):
        # check/query 의도는 센서 조회로 처리
        if any(k in intent for k in ("check", "query", "조회", "확인", "알려줘")):
            sensor = _lookup(_SENSOR_MAP, subject, "temperature")
            return FunctionCall("query_sensor", {"sensor_type": sensor, "location": location})
        
        args = {"zone": location}
        if value is not None:
            temp = _safe_float(value, 24.0)
            if isinstance(temp, str):
                args["value"] = 24.0
                if temp in ("cool", "heat", "auto"):
                    args["mode"] = temp
            else:
                args["value"] = temp
        else:
            args["value"] = 24.0
        if any(k in combined for k in ("heat", "난방", "따뜻", "춥다")):
            args["mode"] = "heat"
        elif any(k in combined for k in ("cool", "냉방", "시원", "에어컨", "덥다")):
            args["mode"] = "cool"
        return FunctionCall("set_temperature", args)

    # ── 타이머 ────────────────────────────────────────────────────────────────
    if any(k in combined for k in ("timer", "타이머", "알람", "분 후", "시간 후")):
        minutes = _safe_int(value, 10)
        args = {"duration_minutes": int(minutes) if minutes else 10}
        if modifiers:
            args["label"] = " ".join(modifiers)
        return FunctionCall("set_timer", args)

    # ── 문 ────────────────────────────────────────────────────────────────────
    if any(k in combined for k in ("door", "문", "현관", "잠금", "lock", "unlock")):
        door_loc = _lookup(_DOOR_MAP, subject, "front_door")
        locked = not any(k in combined for k in ("열", "open", "unlock"))
        return FunctionCall("lock_door", {"location": door_loc, "locked": locked})

    # ── 가전 ──────────────────────────────────────────────────────────────────
    device = _lookup(_DEVICE_MAP, subject)
    if device:
        state = not any(k in combined for k in ("off", "꺼", "끄"))
        return FunctionCall("control_appliance", {"device": device, "state": state})

    # ── 미디어 ────────────────────────────────────────────────────────────────
    if any(k in combined for k in ("play", "music", "음악", "영상", "재생", "틀어")):
        dev = "tv" if "tv" in combined or "텔레비전" in combined else "speaker"
        return FunctionCall("play_media", {"content": subject or "music", "device": dev})

    # ── 센서 조회 (기본 fallback) ──────────────────────────────────────────────
    sensor = _lookup(_SENSOR_MAP, subject, "temperature")
    return FunctionCall("query_sensor", {"sensor_type": sensor, "location": location})


# ── 통합 진입점 ───────────────────────────────────────────────────────────────

def parse_dsl(dsl: dict, width: str) -> FunctionCall:
    """
    width 에 따라 적절한 파서로 위임.

    Args:
        dsl: 모델이 생성한 DSL dict
        width: "narrow" | "medium" | "wide"
    """
    if width == "narrow":
        return parse_narrow(dsl)
    elif width == "medium":
        return parse_medium(dsl)
    elif width == "wide":
        return parse_wide(dsl)
    else:
        raise ValueError(f"알 수 없는 DSL 폭: {width!r}")
