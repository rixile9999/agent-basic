from dotenv import load_dotenv
import os
load_dotenv()

import asyncio
from collections.abc import AsyncGenerator, Sequence
from typing import Any, Mapping

from agent_framework import Agent, InMemoryHistoryProvider
from agent_framework import BaseChatClient, ChatResponse, ChatResponseUpdate, Content, Message
from agent_framework._types import ResponseStream
from agent_framework.openai import OpenAIChatCompletionClient
from agent_framework.devui import serve
from dashscope_client import DashScopeOCRClient
from nurse_schedule_restorer import restore_nurse_schedule

# ── 툴 정의 ──────────────────────────────────────────────────────────────────

def get_weather(location: str) -> str:
    """Get current weather for a location."""
    return f"Weather in {location}: 72°F and sunny"


def calculate(expression: str) -> str:
    """Evaluate a simple math expression. Example: '2 + 3 * 4'"""
    try:
        result = eval(expression, {"__builtins__": {}})
        return f"{expression} = {result}"
    except Exception as e:
        return f"Error: {e}"


# ── NurseScheduleClient ───────────────────────────────────────────────────────

class NurseScheduleClient(BaseChatClient):
    """간호사 근무표 복원 파이프라인 클라이언트.

    메시지에서 이미지를 추출하여 restore_nurse_schedule 파이프라인을 실행하고
    결과를 마크다운으로 반환한다.
    """

    def __init__(self, *, api_key: str, ocr_base_url: str, llm_base_url: str) -> None:
        super().__init__()
        self._api_key = api_key
        self._ocr_base_url = ocr_base_url
        self._llm_base_url = llm_base_url

    def _extract_images(self, messages: Sequence[Message]) -> list[str]:
        """마지막 user 메시지에서 이미지 URI를 추출한다."""
        last_user = next((m for m in reversed(messages) if m.role == "user"), None)
        if last_user is None:
            return []
        return [
            c.uri
            for c in last_user.contents
            if (
                c.type in ("data", "uri")
                and c.uri
                and c.media_type
                and c.media_type.startswith("image/")
            )
        ]

    def _format_result(self, result) -> str:
        lines = ["# 간호사 근무표 복원 결과", ""]
        lines += ["## 복원된 테이블", "", result.merged_table, ""]
        lines += ["## 변경 보고", "", result.changes_report, ""]
        if result.ambiguous_items:
            lines += ["## 모호 항목", ""]
            lines += [f"- {item}" for item in result.ambiguous_items]
        else:
            lines += ["## 모호 항목", "", "없음"]
        lines += ["", f"---", f"*이미지 {len(result.ocr_results)}장 처리 완료*"]
        return "\n".join(lines)

    async def _run_pipeline(self, images: list[str]) -> str:
        result = await restore_nurse_schedule(
            images,
            api_key=self._api_key,
            ocr_base_url=self._ocr_base_url,
            llm_base_url=self._llm_base_url,
        )
        return self._format_result(result)

    def _inner_get_response(
        self,
        *,
        messages: Sequence[Message],
        stream: bool,
        options: Mapping[str, Any],
        **kwargs: Any,
    ):
        images = self._extract_images(messages)
        if not images:
            no_image_msg = (
                "이미지가 첨부되지 않았습니다. "
                "간호사 근무표 또는 희망근무 이미지를 업로드해 주세요."
            )
            if stream:
                return ResponseStream(
                    self._single_chunk_gen(no_image_msg),
                    finalizer=lambda updates: ChatResponse.from_updates(updates),
                )
            return self._immediate_response(no_image_msg)

        if stream:
            return ResponseStream(
                self._pipeline_stream_gen(images),
                finalizer=lambda updates: ChatResponse.from_updates(updates),
            )
        return self._pipeline_response(images)

    async def _pipeline_response(self, images: list[str]) -> ChatResponse:
        text = await self._run_pipeline(images)
        return ChatResponse(
            messages=[Message("assistant", [text])],
            model="nurse-schedule-pipeline",
            finish_reason="stop",
        )

    async def _pipeline_stream_gen(self, images: list[str]) -> AsyncGenerator[ChatResponseUpdate, None]:
        text = await self._run_pipeline(images)
        yield ChatResponseUpdate(
            role="assistant",
            contents=[Content.from_text(text)],
            finish_reason="stop",
        )

    async def _single_chunk_gen(self, text: str) -> AsyncGenerator[ChatResponseUpdate, None]:
        yield ChatResponseUpdate(
            role="assistant",
            contents=[Content.from_text(text)],
            finish_reason="stop",
        )

    async def _immediate_response(self, text: str) -> ChatResponse:
        return ChatResponse(
            messages=[Message("assistant", [text])],
            model="nurse-schedule-pipeline",
            finish_reason="stop",
        )


# ── 클라이언트 설정 ───────────────────────────────────────────────────────────

api_key = os.environ["OPENAI_API_KEY"]
base_url = os.environ["OPENAI_BASE_URL"]

text_client = OpenAIChatCompletionClient(
    model="qwen3.6-plus",
    api_key=api_key,
    base_url=base_url,
)

ocr_client = DashScopeOCRClient(
    model="qwen-vl-ocr",
    api_key=api_key,
    base_url="https://dashscope-intl.aliyuncs.com/api/v1",
    ocr_task="table_parsing",
)

nurse_client = NurseScheduleClient(
    api_key=api_key,
    ocr_base_url="https://dashscope-intl.aliyuncs.com/api/v1",
    llm_base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)

# ── 에이전트 정의 ─────────────────────────────────────────────────────────────

demo_agent = Agent(
    client=text_client,
    instructions="You are a helpful assistant. Answer concisely in the user's language.",
    name="DemoAgent",
    description="General-purpose assistant (Qwen3.6-plus)",
    tools=[get_weather, calculate],
    context_providers=[InMemoryHistoryProvider()],
)

ocr_agent = Agent(
    client=ocr_client,
    # instructions=(
    #     "You are an OCR specialist. "
    #     "When the user sends an image, extract all text from it accurately. "
    #     "Preserve the original layout and formatting as much as possible. "
    #     "If no image is provided, ask the user to upload one. "
    #     "Always respond in the user's language."
    # ),
    name="OCRAgent",
    description="Extracts text from images (Qwen-VL-OCR)",
    context_providers=[InMemoryHistoryProvider()],
)

# ── DevUI 실행 ────────────────────────────────────────────────────────────────
# http://localhost:8080

nurse_agent = Agent(
    client=nurse_client,
    name="NurseScheduleAgent",
    description="간호사 근무표/희망근무 이미지를 복원 (OCR + LLM 보정)",
    context_providers=[InMemoryHistoryProvider()],
)

# ── DevUI 실행 ────────────────────────────────────────────────────────────────
# http://localhost:8080

serve(entities=[demo_agent, ocr_agent, nurse_agent], auto_open=True)
