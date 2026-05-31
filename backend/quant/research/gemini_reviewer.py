"""Gemini-backed skeptical research reviewer."""

from __future__ import annotations

from quant.research.artifacts import BacktestReviewArtifact
from quant.research.llm_reviewer import LlmReviewResult, LlmReviewer, ReviewVerdict


class GeminiResearchReviewer(LlmReviewer):
    def __init__(self, *, api_key: str, model: str = "gemini-2.5-flash"):
        if not api_key:
            raise ValueError("Gemini API key is required.")
        self.api_key = api_key
        self.model = model

    def review_backtest(self, artifact: BacktestReviewArtifact) -> LlmReviewResult:
        try:
            from google import genai
        except ModuleNotFoundError as exc:
            raise RuntimeError("Install google-genai to use GeminiResearchReviewer.") from exc

        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(
            model=self.model,
            contents=_build_prompt(artifact),
        )
        report = (response.text or "").strip()
        return LlmReviewResult(
            provider="gemini",
            model=self.model,
            verdict=_infer_verdict(report),
            report_markdown=report,
        )


def _build_prompt(artifact: BacktestReviewArtifact) -> str:
    return f"""You are a skeptical quant research reviewer.

Review the structured backtest artifact below. Do not invent numbers. Cite only metrics that are present.
Focus on:
- look-ahead or leakage risk
- cost realism
- statistical weakness
- validation gaps
- regime/alpha-decay risk
- whether this is ready for paper trading

Return markdown with sections:
1. Executive Summary
2. Evidence Review
3. Main Risks
4. Missing Tests
5. Verdict

Allowed verdicts: reject, research_more, paper_trade_candidate, disable.

Artifact:
{artifact.to_prompt_context()}
"""


def _infer_verdict(report: str) -> ReviewVerdict:
    normalized = report.lower()
    if "paper_trade_candidate" in normalized or "paper trade candidate" in normalized:
        return "paper_trade_candidate"
    if "disable" in normalized:
        return "disable"
    if "reject" in normalized:
        return "reject"
    return "research_more"
