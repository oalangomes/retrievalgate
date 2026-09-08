"""Suite result aggregation and deterministic serialization."""

from __future__ import annotations

import json
from pathlib import Path

from retrievalgate import __version__
from retrievalgate.models import ScenarioResult, SuiteResult, SuiteSummary


def build_suite_result(results: list[ScenarioResult]) -> SuiteResult:
    """Aggregate scenario results without timestamps or environment-specific fields."""

    passed = sum(result.status == "pass" for result in results)
    failed = len(results) - passed
    mrr = sum(result.metrics.rr for result in results) / len(results) if results else 0.0
    return SuiteResult(
        tool={"name": "retrievalgate", "version": __version__},
        status="pass" if failed == 0 else "fail",
        summary=SuiteSummary(
            scenarios=len(results),
            passed=passed,
            failed=failed,
            mrr=mrr,
        ),
        scenarios=results,
    )


def serialize_result(result: SuiteResult) -> str:
    """Return stable, human-readable JSON."""

    return json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n"


def write_result(path: Path, result: SuiteResult) -> None:
    """Write a structured result as UTF-8 JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize_result(result), encoding="utf-8")
