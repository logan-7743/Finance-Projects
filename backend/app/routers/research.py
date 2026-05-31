"""Research report API routes."""

from fastapi import APIRouter, HTTPException

from app.config import settings
from quant.research import (
    BacktestReviewArtifact,
    GeminiResearchReviewer,
    LlmReviewResult,
    PerplexityResearchRequest,
    PerplexityResearchResult,
    PerplexityResearcher,
)

router = APIRouter()


@router.post("/review", response_model=LlmReviewResult)
async def review_backtest_artifact(artifact: BacktestReviewArtifact) -> LlmReviewResult:
    if not settings.gemini_api_key:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not configured.")

    reviewer = GeminiResearchReviewer(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
    )
    try:
        return reviewer.review_backtest(artifact)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/perplexity", response_model=PerplexityResearchResult)
async def run_perplexity_research(
    payload: PerplexityResearchRequest,
) -> PerplexityResearchResult:
    if not settings.perplexity_api_key:
        raise HTTPException(status_code=503, detail="PERPLEXITY_API_KEY is not configured.")

    researcher = PerplexityResearcher(
        api_key=settings.perplexity_api_key,
        model=settings.perplexity_model,
    )
    try:
        return researcher.research(payload)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Perplexity research failed: {exc}") from exc
