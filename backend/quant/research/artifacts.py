"""Structured artifacts passed to LLM research reviewers."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ResearchMetric(BaseModel):
    name: str
    value: float | str
    description: str | None = None


class BacktestReviewArtifact(BaseModel):
    strategy_name: str
    symbol: str
    hypothesis: str
    data_range: str
    cost_assumptions: list[str] = Field(default_factory=list)
    validation_notes: list[str] = Field(default_factory=list)
    metrics: list[ResearchMetric] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)

    def to_prompt_context(self) -> str:
        metric_lines = "\n".join(
            f"- {metric.name}: {metric.value}"
            + (f" ({metric.description})" if metric.description else "")
            for metric in self.metrics
        )
        cost_lines = "\n".join(f"- {item}" for item in self.cost_assumptions) or "- Not provided"
        validation_lines = "\n".join(f"- {item}" for item in self.validation_notes) or "- Not provided"
        risk_lines = "\n".join(f"- {item}" for item in self.risks) or "- Not provided"
        return f"""Strategy: {self.strategy_name}
Symbol: {self.symbol}
Hypothesis: {self.hypothesis}
Data Range: {self.data_range}

Metrics:
{metric_lines or "- Not provided"}

Cost Assumptions:
{cost_lines}

Validation Notes:
{validation_lines}

Known Risks:
{risk_lines}
"""
