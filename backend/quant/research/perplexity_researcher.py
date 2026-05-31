"""Perplexity-backed market research summaries."""

from __future__ import annotations

import httpx
from pydantic import BaseModel, Field


class PerplexitySearchResult(BaseModel):
    title: str
    url: str
    date: str | None = None


class PerplexityResearchRequest(BaseModel):
    question: str
    system_prompt: str = (
        "You are a concise quant research assistant. Ground claims in current sources, "
        "separate facts from speculation, and call out uncertainty."
    )
    search_mode: str = "web"
    max_tokens: int = Field(default=1_000, gt=0, le=4_000)
    temperature: float = Field(default=0.2, ge=0.0, lt=2.0)


class PerplexityResearchResult(BaseModel):
    provider: str = "perplexity"
    model: str
    answer_markdown: str
    citations: list[PerplexitySearchResult] = Field(default_factory=list)


class PerplexityResearcher:
    endpoint = "https://api.perplexity.ai/chat/completions"

    def __init__(self, *, api_key: str, model: str = "sonar-pro"):
        if not api_key:
            raise ValueError("Perplexity API key is required.")
        self.api_key = api_key
        self.model = model

    def research(self, request: PerplexityResearchRequest) -> PerplexityResearchResult:
        response = httpx.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.question},
                ],
                "search_mode": request.search_mode,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        citations = [
            PerplexitySearchResult(
                title=item.get("title", "Untitled"),
                url=item.get("url", ""),
                date=item.get("date"),
            )
            for item in payload.get("search_results", [])
            if item.get("url")
        ]
        return PerplexityResearchResult(
            model=self.model,
            answer_markdown=content,
            citations=citations,
        )
