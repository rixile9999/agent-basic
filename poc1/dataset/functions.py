"""
홈 자동화 도메인 함수 명세 (8개)
"""
from poc1.models import FunctionSpec

FUNCTIONS: list[FunctionSpec] = [
    FunctionSpec(
        name="control_light",
        description="조명을 켜거나 끄거나 밝기를 조절한다.",
        parameters={
            "type": "object",
            "properties": {
                "room": {
                    "type": "string",
                    "enum": ["living_room", "bedroom", "kitchen", "bathroom", "all"],
                    "description": "조명을 제어할 방",
                },
                "state": {
                    "type": "boolean",
                    "description": "true=켜기, false=끄기",
                },
                "brightness": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 100,
                    "description": "밝기 퍼센트 (생략 시 현재 값 유지)",
                },
            },
            "required": ["room", "state"],
        },
    ),
    FunctionSpec(
        name="set_temperature",
        description="에어컨·난방기의 온도를 설정한다.",
        parameters={
            "type": "object",
            "properties": {
                "zone": {
                    "type": "string",
                    "enum": ["living_room", "bedroom", "all"],
                    "description": "제어할 구역",
                },
                "value": {
                    "type": "number",
                    "description": "설정 온도",
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "default": "celsius",
                },
                "mode": {
                    "type": "string",
                    "enum": ["cool", "heat", "auto"],
                    "description": "냉방/난방/자동",
                },
            },
            "required": ["zone", "value"],
        },
    ),
    FunctionSpec(
        name="control_appliance",
        description="가전제품(TV, 세탁기, 에어컨 등)을 켜거나 끈다.",
        parameters={
            "type": "object",
            "properties": {
                "device": {
                    "type": "string",
                    "enum": ["tv", "washing_machine", "dishwasher", "air_purifier", "robot_vacuum"],
                    "description": "제어할 가전",
                },
                "room": {
                    "type": "string",
                    "enum": ["living_room", "bedroom", "kitchen", "all"],
                },
                "state": {
                    "type": "boolean",
                    "description": "true=켜기, false=끄기",
                },
            },
            "required": ["device", "state"],
        },
    ),
    FunctionSpec(
        name="set_timer",
        description="타이머 또는 알람을 설정한다.",
        parameters={
            "type": "object",
            "properties": {
                "duration_minutes": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "타이머 시간 (분 단위)",
                },
                "label": {
                    "type": "string",
                    "description": "타이머 이름/메모 (선택)",
                },
            },
            "required": ["duration_minutes"],
        },
    ),
    FunctionSpec(
        name="query_sensor",
        description="온도·습도·공기질 등 센서 값을 조회한다.",
        parameters={
            "type": "object",
            "properties": {
                "sensor_type": {
                    "type": "string",
                    "enum": ["temperature", "humidity", "air_quality", "co2", "motion"],
                    "description": "조회할 센서 종류",
                },
                "location": {
                    "type": "string",
                    "enum": ["living_room", "bedroom", "kitchen", "outdoor", "all"],
                },
            },
            "required": ["sensor_type", "location"],
        },
    ),
    FunctionSpec(
        name="play_media",
        description="TV나 스피커에서 음악·영상을 재생한다.",
        parameters={
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "재생할 콘텐츠명 또는 장르",
                },
                "device": {
                    "type": "string",
                    "enum": ["tv", "speaker", "bedroom_speaker"],
                    "description": "재생할 장치",
                },
                "volume": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 100,
                    "description": "볼륨 (0~100, 생략 시 현재 값 유지)",
                },
            },
            "required": ["content", "device"],
        },
    ),
    FunctionSpec(
        name="lock_door",
        description="현관문·방문을 잠그거나 연다.",
        parameters={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "enum": ["front_door", "back_door", "garage"],
                    "description": "잠금/해제할 문",
                },
                "locked": {
                    "type": "boolean",
                    "description": "true=잠금, false=열기",
                },
            },
            "required": ["location", "locked"],
        },
    ),
    FunctionSpec(
        name="set_scene",
        description="미리 정의된 씬(조명+온도+가전 프리셋)을 활성화한다.",
        parameters={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "enum": ["morning", "movie", "sleep", "away", "party", "reading"],
                    "description": "활성화할 씬 이름",
                },
            },
            "required": ["name"],
        },
    ),
]

# 빠른 조회용 dict
FUNCTION_MAP: dict[str, FunctionSpec] = {f.name: f for f in FUNCTIONS}
