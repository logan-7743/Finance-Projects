"""Execution readiness gates before paper/live trading."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ExecutionStage(StrEnum):
    UNIT_TESTS = "unit_tests"
    HISTORICAL_REPLAY = "historical_replay"
    SHADOW_MODE = "shadow_mode"
    COINBASE_SANDBOX = "coinbase_sandbox"
    EXTERNAL_PAPER = "external_paper"
    TINY_CAPITAL_CANARY = "tiny_capital_canary"


class StageEvidence(BaseModel):
    stage: ExecutionStage
    passed: bool
    notes: str = ""


class ExecutionReadinessReport(BaseModel):
    approved_for_live: bool
    next_required_stage: ExecutionStage | None
    missing_stages: list[ExecutionStage] = Field(default_factory=list)


REQUIRED_STAGE_ORDER = [
    ExecutionStage.UNIT_TESTS,
    ExecutionStage.HISTORICAL_REPLAY,
    ExecutionStage.SHADOW_MODE,
    ExecutionStage.COINBASE_SANDBOX,
    ExecutionStage.EXTERNAL_PAPER,
    ExecutionStage.TINY_CAPITAL_CANARY,
]


def assess_execution_readiness(evidence: list[StageEvidence]) -> ExecutionReadinessReport:
    passed = {item.stage for item in evidence if item.passed}
    missing = [stage for stage in REQUIRED_STAGE_ORDER if stage not in passed]
    return ExecutionReadinessReport(
        approved_for_live=not missing,
        next_required_stage=missing[0] if missing else None,
        missing_stages=missing,
    )
