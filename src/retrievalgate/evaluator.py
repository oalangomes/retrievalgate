"""Deterministic retrieval metrics and gate evaluation."""

from __future__ import annotations

from retrievalgate.models import (
    AdapterResponse,
    ExpectedResults,
    GateEvaluation,
    MetricValues,
    Scenario,
    ScenarioResult,
)
from retrievalgate.scenarios import scenario_fingerprint


def _metric_value(metrics: MetricValues, metric: str) -> float:
    value = getattr(metrics, metric)
    if value is None:
        raise ValueError(f"metric '{metric}' is unavailable for this scenario")
    return float(value)


def evaluate(scenario: Scenario, response: AdapterResponse) -> ScenarioResult:
    """Evaluate one ranked retrieval response against one scenario contract."""

    considered = response.results[: scenario.top_k]
    result_ids = [item.id for item in considered]
    relevant_ids = scenario.ground_truth.relevant
    relevant_set = set(relevant_ids)

    ranks: dict[str, int | None] = {}
    for relevant_id in relevant_ids:
        try:
            ranks[relevant_id] = result_ids.index(relevant_id) + 1
        except ValueError:
            ranks[relevant_id] = None

    found_ids = [item for item in relevant_ids if ranks[item] is not None]
    missing = [item for item in relevant_ids if ranks[item] is None]
    found_count = len(found_ids)

    recall = found_count / len(relevant_ids)
    found_ranks = [rank for rank in ranks.values() if rank is not None]
    rr = 0.0 if not found_ranks else 1.0 / min(found_ranks)

    precision: float | None = None
    unexpected_count: int | None = None
    if scenario.ground_truth.exhaustive:
        precision = found_count / scenario.top_k
        unexpected_count = sum(1 for result_id in result_ids if result_id not in relevant_set)

    metrics = MetricValues(
        recall=recall,
        rr=rr,
        result_count=len(considered),
        precision=precision,
        unexpected_count=unexpected_count,
    )

    gate_results: list[GateEvaluation] = []
    for metric_name in sorted(scenario.gates):
        bounds = scenario.gates[metric_name]
        value = _metric_value(metrics, metric_name)
        passed = True
        if bounds.min is not None and value < bounds.min:
            passed = False
        if bounds.max is not None and value > bounds.max:
            passed = False
        gate_results.append(
            GateEvaluation(
                metric=metric_name,
                value=value,
                min=bounds.min,
                max=bounds.max,
                passed=passed,
            )
        )

    status = "pass" if all(gate.passed for gate in gate_results) else "fail"
    return ScenarioResult(
        id=scenario.id,
        scenario_fingerprint=scenario_fingerprint(scenario),
        status=status,
        top_k=scenario.top_k,
        metrics=metrics,
        expected=ExpectedResults(
            total=len(relevant_ids),
            found=found_count,
            missing=missing,
            ranks=ranks,
        ),
        gates=gate_results,
    )
