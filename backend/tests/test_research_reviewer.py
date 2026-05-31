"""Tests for structured LLM research review artifacts."""

from quant.research import BacktestReviewArtifact, ResearchMetric
from quant.research.gemini_reviewer import _infer_verdict


def test_backtest_review_artifact_prompt_context_contains_metrics() -> None:
    artifact = BacktestReviewArtifact(
        strategy_name="ema_crossover",
        symbol="BTC-USD",
        hypothesis="Momentum persists over short horizons.",
        data_range="2025-01-01 to 2025-12-31",
        metrics=[ResearchMetric(name="Sharpe", value=1.2)],
        cost_assumptions=["5 bps slippage"],
        validation_notes=["Final holdout not yet run"],
        risks=["Yahoo crypto data is research-grade only"],
    )

    context = artifact.to_prompt_context()

    assert "ema_crossover" in context
    assert "Sharpe: 1.2" in context
    assert "Final holdout not yet run" in context


def test_infer_verdict_defaults_to_research_more() -> None:
    assert _infer_verdict("More validation is needed.") == "research_more"
    assert _infer_verdict("Verdict: reject") == "reject"
