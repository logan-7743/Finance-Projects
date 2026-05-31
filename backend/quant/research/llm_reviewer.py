"""LLM research-reviewer interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel

from quant.research.artifacts import BacktestReviewArtifact

ReviewVerdict = Literal["reject", "research_more", "paper_trade_candidate", "disable"]


class LlmReviewResult(BaseModel):
    provider: str
    model: str
    verdict: ReviewVerdict
    report_markdown: str


class LlmReviewer(ABC):
    @abstractmethod
    def review_backtest(self, artifact: BacktestReviewArtifact) -> LlmReviewResult:
        """Review a structured backtest artifact."""
        ...
