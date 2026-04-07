"""
DashScope native API client for MAF (Microsoft Agent Framework).
Supports qwen-vl-ocr with ocr_options (table_parsing, document_parsing, etc.)
"""
import asyncio
from collections.abc import AsyncGenerator, Sequence
from typing import Any, Mapping

import dashscope

from agent_framework import BaseChatClient, ChatResponse, ChatResponseUpdate, Content, Message
from agent_framework._types import ResponseStream


class DashScopeOCRClient(BaseChatClient):
    """MAF-compatible client wrapping DashScope native MultiModalConversation API.

    Enables use of ocr_options (e.g. table_parsing) which are only available
    via the DashScope native API, not the OpenAI-compatible endpoint.

    Args:
        api_key: DashScope API key (DASHSCOPE_API_KEY).
        model: Model name. Defaults to 'qwen-vl-ocr'.
        base_url: DashScope base URL. Defaults to international endpoint.
        ocr_task: OCR task type passed to ocr_options.
            One of: table_parsing, document_parsing, text_recognition,
                    advanced_recognition, formula_recognition, key_information_extraction
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "qwen-vl-ocr",
        base_url: str = "https://dashscope-intl.aliyuncs.com/api/v1",
        ocr_task: str = "table_parsing",
    ) -> None:
        super().__init__()
        self._api_key = api_key
        self._model = model
        self._ocr_task = ocr_task
        dashscope.base_http_api_url = base_url

    # ── 메시지 변환 ───────────────────────────────────────────────────────────

    def _to_dashscope_messages(self, messages: Sequence[Message]) -> list[dict]:
        """Convert MAF Message objects to DashScope MultiModalConversation format."""
        ds_messages = []
        for msg in messages:
            parts: list[dict] = []
            for c in msg.contents:
                if c.type == "text" and c.text:
                    parts.append({"text": c.text})
                elif (
                    c.type in ("data", "uri")
                    and c.uri
                    and c.media_type
                    and c.media_type.startswith("image/")
                ):
                    # data: URI (base64) or https:// URL — both accepted by DashScope
                    parts.append({"image": c.uri})
            if not parts:
                parts = [{"text": ""}]
            ds_messages.append({"role": msg.role, "content": parts})
        return ds_messages

    # ── DashScope 호출 (동기, executor에서 실행) ──────────────────────────────

    def _call_dashscope(self, ds_messages: list[dict]) -> str:
        response = dashscope.MultiModalConversation.call(
            api_key=self._api_key,
            model=self._model,
            messages=ds_messages,
            ocr_options={"task": self._ocr_task},
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"DashScope API error {response.status_code}: {response.message}"
            )
        return response.output.choices[0].message.content[0]["text"]

    # ── BaseChatClient 구현 ───────────────────────────────────────────────────

    def _inner_get_response(
        self,
        *,
        messages: Sequence[Message],
        stream: bool,
        options: Mapping[str, Any],
        **kwargs: Any,
    ):
        ds_messages = self._to_dashscope_messages(messages)

        if stream:
            return ResponseStream(
                self._stream_gen(ds_messages),
                finalizer=lambda updates: ChatResponse.from_updates(updates),
            )
        return self._async_response(ds_messages)

    async def _async_response(self, ds_messages: list[dict]) -> ChatResponse:
        """Non-streaming path: run DashScope call in thread pool."""
        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(None, self._call_dashscope, ds_messages)
        return ChatResponse(
            messages=[Message("assistant", [text])],
            model=self._model,
            finish_reason="stop",
        )

    async def _stream_gen(self, ds_messages: list[dict]) -> AsyncGenerator[ChatResponseUpdate, None]:
        """Streaming path: DashScope OCR doesn't stream meaningfully, yield as one chunk."""
        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(None, self._call_dashscope, ds_messages)
        yield ChatResponseUpdate(
            role="assistant",
            contents=[Content.from_text(text)],
            finish_reason="stop",
        )
