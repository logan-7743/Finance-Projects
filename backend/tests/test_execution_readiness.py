"""Tests for execution readiness gates."""

from quant.execution import ExecutionStage, StageEvidence, assess_execution_readiness


def test_execution_readiness_requires_ordered_gates() -> None:
    report = assess_execution_readiness(
        [
            StageEvidence(stage=ExecutionStage.UNIT_TESTS, passed=True),
            StageEvidence(stage=ExecutionStage.HISTORICAL_REPLAY, passed=True),
        ]
    )

    assert report.approved_for_live is False
    assert report.next_required_stage == ExecutionStage.SHADOW_MODE


def test_execution_readiness_approves_when_all_required_stages_pass() -> None:
    report = assess_execution_readiness(
        [StageEvidence(stage=stage, passed=True) for stage in ExecutionStage]
    )

    assert report.approved_for_live is True
    assert report.next_required_stage is None
