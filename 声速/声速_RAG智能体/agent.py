from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Iterator

import requests

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, PROMPT_PATH
from retrieval import HybridRetriever, SearchHit
from tools import format_calculation, parse_calculation_request
from web_search import format_web_context, search_web


@dataclass
class AgentResponse:
    answer: str
    sources: list[SearchHit]
    tool_result: str | None
    used_llm: bool


@dataclass
class PreparedAnswer:
    question: str
    messages: list[dict]
    hits: list[SearchHit]
    tool_result: str | None


class SoundSpeedAgent:
    def __init__(
        self,
        retriever: HybridRetriever,
        base_url: str = LLM_BASE_URL,
        model: str = LLM_MODEL,
        api_key: str = LLM_API_KEY,
    ):
        self.retriever = retriever
        self.base_url = base_url
        self.model = model
        self.api_key = api_key
        self.system_prompt = Path(PROMPT_PATH).read_text(encoding="utf-8")

    @staticmethod
    def _user_content(text: str, image_urls: list[str] | None = None) -> str | list[dict]:
        if not image_urls:
            return text
        content: list[dict] = [{"type": "text", "text": text}]
        content.extend(
            {"type": "image_url", "image_url": {"url": image_url}}
            for image_url in image_urls
        )
        return content

    def _messages(
        self,
        question: str,
        history: list[dict],
        hits: list[SearchHit],
        tool_result: str | None,
        web_context: str,
        image_urls: list[str] | None = None,
    ) -> list[dict]:
        context = self.retriever.format_context(hits)
        system = self.system_prompt + (
            "\n\n以下是本轮从本地知识库检索出的文献片段。它们是回答的主要依据，"
            "但不要向用户展示来源列表、文献编号、页码、链接或引用标记。"
            "不得把片段中没有出现的结论写成文献事实。\n\n"
            + context
            + "\n\n以下是本轮联网搜索摘要，仅用于补充和核对信息。"
            "不要在回答中展示搜索结果列表、网址或 [W] 编号；若与本地文献冲突，"
            "优先采用原始文献和权威来源，并清楚表达不确定性。\n\n"
            + web_context
        )
        if tool_result:
            system += f"\n\n确定性计算工具输出：\n{tool_result}"
        messages = [{"role": "system", "content": system}]
        for item in history[-6:]:
            if item.get("role") in {"user", "assistant"}:
                content = item.get("content", "")
                if item["role"] == "user":
                    content = self._user_content(content, item.get("image_urls"))
                messages.append({"role": item["role"], "content": content})
        messages.append(
            {"role": "user", "content": self._user_content(question, image_urls)}
        )
        return messages

    def _call_llm(self, messages: list[dict]) -> str:
        response = requests.post(
            self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 3000,
                "stream": False,
                "enable_thinking": False,
            },
            timeout=90,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    def _call_llm_stream(self, messages: list[dict]) -> Iterator[str]:
        with requests.post(
            self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 3000,
                "stream": True,
                "enable_thinking": False,
            },
            timeout=(15, 120),
            stream=True,
        ) as response:
            response.raise_for_status()
            for raw_line in response.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                line = raw_line.strip()
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                data = json.loads(payload)
                choices = data.get("choices") or []
                if not choices:
                    continue
                content = (choices[0].get("delta") or {}).get("content")
                if content:
                    yield content

    @staticmethod
    def _retrieval_fallback(
        question: str,
        hits: list[SearchHit],
        tool_result: str | None,
        model_error: str | None = None,
    ) -> str:
        sections = [model_error or "当前语言模型暂时无法完成回答，以下内容来自本地知识库检索。"]
        if tool_result:
            sections.append(tool_result)
        if not hits:
            sections.append("没有检索到足够相关的文献片段，请换用更具体的关键词。")
            return "\n\n".join(sections)
        sections.append(f"**问题**：{question}")
        for hit in hits[:3]:
            snippet = hit.chunk["text"].replace("\n", " ")[:420]
            sections.append(snippet)
        return "\n\n".join(sections)

    def prepare(
        self,
        question: str,
        history: list[dict] | None = None,
        top_k: int = 6,
        language: str | None = None,
        topic: str | None = None,
        image_urls: list[str] | None = None,
    ) -> PreparedAnswer:
        history = history or []
        hits = self.retriever.search(question, top_k=top_k, language=language, topic=topic)
        calculation = parse_calculation_request(question)
        tool_result = format_calculation(calculation) if calculation else None
        web_context = format_web_context(search_web(question, max_results=4))
        messages = self._messages(
            question,
            history,
            hits,
            tool_result,
            web_context,
            image_urls=image_urls,
        )
        return PreparedAnswer(question, messages, hits, tool_result)

    def stream(self, prepared: PreparedAnswer) -> Iterator[str]:
        emitted = False
        try:
            for content in self._call_llm_stream(prepared.messages):
                emitted = True
                yield content
        except (requests.RequestException, KeyError, IndexError, json.JSONDecodeError) as exc:
            if emitted:
                yield "\n\n回答生成中断，请重试。"
            else:
                model_error = None
                if isinstance(exc, requests.HTTPError) and exc.response is not None:
                    if exc.response.status_code == 401:
                        model_error = "模型服务鉴权失败，请检查 API 密钥和接口配置。"
                    elif exc.response.status_code == 429:
                        model_error = "模型服务的请求额度或速率已达到限制，请稍后重试。"
                yield self._retrieval_fallback(
                    prepared.question,
                    prepared.hits,
                    prepared.tool_result,
                    model_error=model_error,
                )

    def answer(
        self,
        question: str,
        history: list[dict] | None = None,
        top_k: int = 6,
        language: str | None = None,
        topic: str | None = None,
        image_urls: list[str] | None = None,
    ) -> AgentResponse:
        prepared = self.prepare(
            question,
            history,
            top_k,
            language,
            topic,
            image_urls=image_urls,
        )
        try:
            answer = self._call_llm(prepared.messages)
            used_llm = True
        except (requests.RequestException, KeyError, IndexError, json.JSONDecodeError):
            answer = self._retrieval_fallback(question, prepared.hits, prepared.tool_result)
            used_llm = False
        return AgentResponse(answer, prepared.hits, prepared.tool_result, used_llm)
