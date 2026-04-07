"""
간호사 근무표/희망근무 이미지를 2단계 파이프라인으로 테이블 복원.

Step 1: qwen-vl-ocr (table_parsing) — 이미지별 병렬 OCR → HTML 테이블
Step 2: qwen3.6-plus — OCR 오류 보정 + 테이블 병합 + 변경 보고
"""
import asyncio
import base64
import re
from dataclasses import dataclass, field
from pathlib import Path

import dashscope
from openai import AsyncOpenAI


# ── 데이터 구조 ────────────────────────────────────────────────────────────────

@dataclass
class OCRResult:
    image_index: int
    source: str       # 원본 소스 식별자 (경로, URL, "bytes", "data_uri")
    html_table: str   # table_parsing 결과 HTML
    raw_text: str     # 원본 OCR 텍스트 (html_table과 동일)


@dataclass
class RestorationResult:
    merged_table: str              # markdown 테이블 (최종)
    ocr_results: list[OCRResult]   # 이미지별 OCR 원본
    changes_report: str            # 어디를 어떻게 고쳤는지
    ambiguous_items: list[str]     # 모호/충돌 항목 목록
    merged_html: str = ""          # HTML 형식 최종 테이블 (파싱용, 선택)


# ── 이미지 소스 정규화 ─────────────────────────────────────────────────────────

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}
_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".webp": "image/webp",
}


def _normalize_image_source(source: str | bytes) -> tuple[str, str]:
    """모든 이미지 소스를 DashScope 허용 형식으로 변환.

    Returns:
        (normalized_source, label) — label은 로그/식별용 짧은 문자열
    """
    if isinstance(source, bytes):
        # bytes → base64 data URI (PNG 가정)
        b64 = base64.b64encode(source).decode()
        return f"data:image/png;base64,{b64}", "bytes"

    if source.startswith("data:image/"):
        return source, "data_uri"

    if source.startswith("http://") or source.startswith("https://"):
        return source, source

    # 파일 경로
    path = Path(source)
    ext = path.suffix.lower()
    if ext not in _IMAGE_EXTS:
        raise ValueError(f"지원하지 않는 이미지 확장자: {ext!r} ({source!r})")
    mime = _MIME[ext]
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode()
    return f"data:{mime};base64,{b64}", str(path)


# ── Step 1: OCR ────────────────────────────────────────────────────────────────

def _call_dashscope_sync(
    image_source: str,
    api_key: str,
    model: str,
    base_url: str,
    ocr_task: str,
) -> str:
    """동기 DashScope OCR 호출 (executor에서 실행)."""
    dashscope.base_http_api_url = base_url
    response = dashscope.MultiModalConversation.call(
        api_key=api_key,
        model=model,
        messages=[{"role": "user", "content": [{"image": image_source}]}],
        ocr_options={"task": ocr_task},
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"DashScope API error {response.status_code}: {response.message}"
        )
    return response.output.choices[0].message.content[0]["text"]


async def _ocr_single_image(
    image_source: str,
    label: str,
    api_key: str,
    model: str,
    base_url: str,
    ocr_task: str,
    idx: int,
    semaphore: asyncio.Semaphore,
) -> OCRResult:
    """단일 이미지 OCR. run_in_executor로 동기 dashscope 호출."""
    async with semaphore:
        loop = asyncio.get_running_loop()
        html_text = await loop.run_in_executor(
            None,
            _call_dashscope_sync,
            image_source,
            api_key,
            model,
            base_url,
            ocr_task,
        )
    return OCRResult(
        image_index=idx,
        source=label,
        html_table=html_text,
        raw_text=html_text,
    )


async def _ocr_all_images(
    sources: list[tuple[str, str]],  # [(normalized_source, label), ...]
    api_key: str,
    model: str,
    base_url: str,
    ocr_task: str,
    max_concurrent: int = 3,
) -> list[OCRResult]:
    """asyncio.gather로 병렬 OCR."""
    semaphore = asyncio.Semaphore(max_concurrent)
    tasks = [
        _ocr_single_image(src, label, api_key, model, base_url, ocr_task, i, semaphore)
        for i, (src, label) in enumerate(sources)
    ]
    return await asyncio.gather(*tasks)


# ── Step 2: 보정 및 병합 ───────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
당신은 간호사 근무표 전문가입니다.
여러 이미지에서 OCR로 추출된 HTML 테이블들이 주어집니다.
다음 작업을 수행하세요:
1. OCR 오류 수정 (예: 0↔O, 1↔l, 근무코드 오타 등)
2. 테이블 병합 (중복 행/열 처리, 날짜/이름 기준 정렬)
3. 수행한 모든 변경사항을 상세히 보고
4. 모호하거나 확신할 수 없는 항목 목록화

응답 형식 (반드시 준수):
## MERGED_TABLE
[markdown 테이블]

## CHANGES_REPORT
[변경사항 상세 목록]

## AMBIGUOUS_ITEMS
[모호 항목 목록, 없으면 "없음"]
"""


def _build_user_message(ocr_results: list[OCRResult]) -> str:
    n = len(ocr_results)
    parts = [f"다음은 {n}개의 이미지에서 추출된 HTML 테이블입니다:\n"]
    for r in ocr_results:
        parts.append(f"=== 이미지 {r.image_index + 1} ===")
        parts.append(r.html_table)
        parts.append("")
    return "\n".join(parts)


def _parse_llm_response(text: str) -> tuple[str, str, list[str]]:
    """LLM 응답에서 merged_table / changes_report / ambiguous_items 추출."""
    sections: dict[str, str] = {}
    pattern = re.compile(
        r"##\s+(MERGED_TABLE|CHANGES_REPORT|AMBIGUOUS_ITEMS)\s*\n(.*?)(?=\n##\s+|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    for m in pattern.finditer(text):
        key = m.group(1).upper()
        sections[key] = m.group(2).strip()

    merged_table = sections.get("MERGED_TABLE", "")
    changes_report = sections.get("CHANGES_REPORT", "")
    ambiguous_raw = sections.get("AMBIGUOUS_ITEMS", "없음")

    # 모호 항목: 줄 단위로 분리, "없음" 처리
    if ambiguous_raw.strip() in ("없음", "없음.", "None", "none", "-"):
        ambiguous_items: list[str] = []
    else:
        ambiguous_items = [
            line.lstrip("-•* ").strip()
            for line in ambiguous_raw.splitlines()
            if line.strip() and line.strip() not in ("없음", "-")
        ]

    # fallback: 섹션 헤더 미발견 시 전체 텍스트를 merged_table로
    if not merged_table:
        merged_table = text.strip()

    return merged_table, changes_report, ambiguous_items


async def _correct_and_merge(
    ocr_results: list[OCRResult],
    api_key: str,
    model: str,
    base_url: str,
) -> RestorationResult:
    """OpenAI 호환 엔드포인트로 qwen3.6-plus 호출하여 보정·병합."""
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    user_message = _build_user_message(ocr_results)

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    text = response.choices[0].message.content or ""
    merged_table, changes_report, ambiguous_items = _parse_llm_response(text)

    return RestorationResult(
        merged_table=merged_table,
        ocr_results=ocr_results,
        changes_report=changes_report,
        ambiguous_items=ambiguous_items,
    )


# ── 메인 함수 ──────────────────────────────────────────────────────────────────

async def restore_nurse_schedule(
    image_sources: list[str | bytes],
    *,
    api_key: str,
    ocr_model: str = "qwen-vl-ocr",
    llm_model: str = "qwen3.6-plus",
    ocr_base_url: str = "https://dashscope-intl.aliyuncs.com/api/v1",
    llm_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    ocr_task: str = "table_parsing",
    max_concurrent: int = 3,
) -> RestorationResult:
    """간호사 근무표/희망근무 이미지를 복원한다.

    Args:
        image_sources: 이미지 경로, URL, data URI, bytes 혼용 가능
        api_key: DashScope / OpenAI 호환 API 키 (동일 키 사용)
        ocr_model: OCR 모델 (기본: qwen-vl-ocr)
        llm_model: 보정/병합 모델 (기본: qwen3.6-plus)
        ocr_base_url: DashScope 네이티브 API URL
        llm_base_url: OpenAI 호환 API URL
        ocr_task: OCR 태스크 타입 (table_parsing / document_parsing 등)
        max_concurrent: 동시 OCR 요청 수 제한

    Returns:
        RestorationResult — merged_table(markdown), ocr_results, changes_report, ambiguous_items
    """
    if not image_sources:
        raise ValueError("image_sources는 1개 이상이어야 합니다.")

    # Step 1: 이미지 정규화
    normalized = [_normalize_image_source(s) for s in image_sources]

    # Step 2: 병렬 OCR
    ocr_results = await _ocr_all_images(
        normalized, api_key, ocr_model, ocr_base_url, ocr_task, max_concurrent
    )

    # Step 3: 보정 + 병합
    result = await _correct_and_merge(ocr_results, api_key, llm_model, llm_base_url)

    return result
