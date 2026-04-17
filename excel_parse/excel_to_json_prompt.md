주어진 간호사 희망근무표 테이블을 제시한 스키마에 맞게 변환해.
**희망 근무 신청 중요도 나누기**: 근무코드 및 신청사유를 분석하여 중요도를 5(반드시 지켜져야 함)와 3으로 지정해라.

**json schema**
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Nurse Shift Preference",
  "type": "object",
  "additionalProperties": false,
  "required": ["nurse_name", "shift_days", "shift_type", "importance", "note"],
  "properties": {
    "nurse_name": {
      "type": "string",
      "minLength": 1,
      "description": "간호사 이름"
    },
    "shift_days": {
      "type": "array",
      "description": "희망 또는 지정 근무 일자 목록",
      "items": {
        "type": "integer",
        "minimum": 1,
        "maximum": 31
      },
      "minItems": 1,
      "uniqueItems": true
    },
    "shift_type": {
      "type": "string",
      "description": "근무 유형",
      "enum": ["day", "evening", "night", "off"]
    },
    "importance": {
      "type": "integer",
      "description": "우선순위 또는 중요도",
      "enum": [3, 5]
    },
    "note": {
      "type": "string",
      "description": "추가 메모",
      "default": ""
    }
  }
}

