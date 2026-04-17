주어진 간호사 행정코드의 의미를 잘 추론해서 제시한 스키마에 맞게 매핑해.
**힌트**: 행정코드 추출의 원본테이블인 전월근무표의 내용 및 패턴을 이용해보는 것도 방법임.

**json schema**
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Nurse Shift Codes",
  "type": "object",
  "additionalProperties": false,
  "required": "shift_code",
  "properties": {
    "shift_code": {
      "type": "string",
      "enum": ["", "D", "D4", "E", "E4", "N", "N4", "OF"],
      "description": "근무 코드
      (판단이 어려우면 빈 문자열,
      D=주간, D4=주간 4시간, E=저녁, E4=저녁 4시간, N=야간, N4=야간 4시간, OF=휴무)"
    },
    "note": {
      "type": "string", "description": "추론한 행정코드의 의미, 헷갈리면 비움"
    }
  }
}
