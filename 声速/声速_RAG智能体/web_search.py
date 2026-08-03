from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WebResult:
    title: str
    url: str
    summary: str


def search_web(query: str, max_results: int = 4) -> list[WebResult]:
    try:
        from ddgs import DDGS

        raw_results = DDGS(timeout=8).text(
            query,
            region="cn-zh",
            safesearch="moderate",
            max_results=max_results,
        )
    except Exception:
        return []

    results = []
    for item in raw_results or []:
        title = str(item.get("title") or "").strip()
        url = str(item.get("href") or item.get("url") or "").strip()
        summary = str(item.get("body") or item.get("description") or "").strip()
        if title and (summary or url):
            results.append(WebResult(title=title, url=url, summary=summary))
    return results[:max_results]


def format_web_context(results: list[WebResult]) -> str:
    if not results:
        return "本轮联网搜索未返回可用结果。"
    sections = []
    for number, result in enumerate(results, start=1):
        sections.append(
            f"[W{number}] {result.title}\n"
            f"网址：{result.url}\n"
            f"摘要：{result.summary}"
        )
    return "\n\n".join(sections)
