"""Suite result aggregation and deterministic serialization."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from retrievalgate import __version__
from retrievalgate.models import ScenarioResult, SuiteResult, SuiteSummary


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _aggregate_measures(
    results: list[ScenarioResult],
) -> tuple[dict[str, float], dict[str, int]]:
    values: dict[str, list[float]] = defaultdict(list)
    for result in results:
        for name, value in result.metrics.measures.items():
            aggregate_name = (
                f"MRR@{name.rsplit('@', 1)[1]}" if name.startswith("RR@") else name
            )
            values[aggregate_name].append(value)
    return (
        {name: _mean(items) for name, items in sorted(values.items())},
        {name: len(items) for name, items in sorted(values.items())},
    )


def _aggregate_telemetry(
    results: list[ScenarioResult],
) -> tuple[dict[str, float], dict[str, int]]:
    values: dict[str, list[float]] = defaultdict(list)
    for result in results:
        telemetry = result.metrics.telemetry
        if telemetry is None:
            continue
        for field in (
            "duration_ms",
            "candidates_examined",
            "candidates_returned",
            "returned_chars",
        ):
            value = getattr(telemetry, field)
            if value is not None:
                values[field].append(float(value))
    return (
        {name: _mean(items) for name, items in sorted(values.items())},
        {name: len(items) for name, items in sorted(values.items())},
    )


def build_suite_result(results: list[ScenarioResult]) -> SuiteResult:
    """Aggregate scenario results without timestamps or environment-specific fields."""

    passed = sum(result.status == "pass" for result in results)
    failed = len(results) - passed
    mrr = sum(result.metrics.rr for result in results) / len(results) if results else 0.0
    metrics, metric_counts = _aggregate_measures(results)
    telemetry, telemetry_counts = _aggregate_telemetry(results)
    return SuiteResult(
        tool={"name": "retrievalgate", "version": __version__},
        status="pass" if failed == 0 else "fail",
        summary=SuiteSummary(
            scenarios=len(results),
            passed=passed,
            failed=failed,
            mrr=mrr,
            metrics=metrics,
            metric_counts=metric_counts,
            telemetry=telemetry,
            telemetry_counts=telemetry_counts,
        ),
        scenarios=results,
    )


def serialize_result(result: SuiteResult) -> str:
    """Return stable, human-readable JSON."""

    return json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n"


def write_result(path: Path, result: SuiteResult) -> None:
    """Write one structured result as UTF-8 JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize_result(result), encoding="utf-8")
