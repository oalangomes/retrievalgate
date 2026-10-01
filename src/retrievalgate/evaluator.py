"""Deterministic retrieval metrics and gate evaluation."""

from __future__ import annotations

import math
from typing import Literal

from retrievalgate.models import (
    AdapterResponse,
    ExpectedResults,
    GateEvaluation,
    MetricValues,
    Scenario,
    ScenarioResult,
    canonical_metric_name,
)
from retrievalgate.scenarios import scenario_fingerprint


def _binary_ndcg(result_ids: list[str], relevant: set[str], cutoff: int) -> float:
    considered = result_ids[:cutoff]
    relevant_ranks = [
        rank
        for rank, result_id in enumerate(considered, start=1)
        if result_id in relevant
    ]
    dcg = sum(1.0 / math.log2(rank + 1) for rank in relevant_ranks)
    ideal_hits = min(len(relevant), cutoff)
    ideal_dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank in range(1, ideal_hits + 1)
    )
    return 0.0 if ideal_dcg == 0.0 else dcg / ideal_dcg


def _measure_at_cutoff(
    *,
    result_ids: list[str],
    relevant_ids: list[str],
    exhaustive: bool,
    cutoff: int,
) -> dict[str, float]:
    relevant = set(relevant_ids)
    considered = result_ids[:cutoff]
    found = [result_id for result_id in relevant_ids if result_id in considered]
    ranks = [considered.index(result_id) + 1 for result_id in found]

    recall = len(found) / len(relevant_ids)
    success = 1.0 if found else 0.0
    rr = 0.0 if not ranks else 1.0 / min(ranks)
    density = 0.0 if not considered else len(found) / len(considered)

    measures = {
        f"Recall@{cutoff}": recall,
        f"Success@{cutoff}": success,
        f"RR@{cutoff}": rr,
        f"nDCG@{cutoff}": _binary_ndcg(result_ids, relevant, cutoff),
        f"EvidenceDensity@{cutoff}": density,
        f"ResultCount@{cutoff}": float(len(considered)),
    }
    if exhaustive:
        measures[f"Precision@{cutoff}"] = len(found) / cutoff
        measures[f"UnexpectedCount@{cutoff}"] = float(
            sum(1 for result_id in considered if result_id not in relevant)
        )
    return measures


def evaluate(scenario: Scenario, response: AdapterResponse) -> ScenarioResult:
    """Evaluate one ranked retrieval response against one scenario contract."""

    result_ids = [item.id for item in response.results[: scenario.top_k]]
    relevant_ids = scenario.ground_truth.relevant

    ranks: dict[str, int | None] = {}
    for relevant_id in relevant_ids:
        try:
            ranks[relevant_id] = result_ids.index(relevant_id) + 1
        except ValueError:
            ranks[relevant_id] = None

    found_ids = [item for item in relevant_ids if ranks[item] is not None]
    missing = [item for item in relevant_ids if ranks[item] is None]
    found_count = len(found_ids)

    measures: dict[str, float] = {}
    for cutoff in scenario.cutoffs:
        measures.update(
            _measure_at_cutoff(
                result_ids=result_ids,
                relevant_ids=relevant_ids,
                exhaustive=scenario.ground_truth.exhaustive,
                cutoff=cutoff,
            )
        )

    top = scenario.top_k
    recall = measures[f"Recall@{top}"]
    rr = measures[f"RR@{top}"]
    result_count = int(measures[f"ResultCount@{top}"])
    precision = (
        measures[f"Precision@{top}"] if scenario.ground_truth.exhaustive else None
    )
    unexpected_count = (
        int(measures[f"UnexpectedCount@{top}"])
        if scenario.ground_truth.exhaustive
        else None
    )

    metrics = MetricValues(
        recall=recall,
        rr=rr,
        result_count=result_count,
        precision=precision,
        unexpected_count=unexpected_count,
        measures=measures,
        telemetry=response.telemetry,
    )

    gate_results: list[GateEvaluation] = []
    for configured_name in sorted(scenario.gates):
        canonical = canonical_metric_name(configured_name, top_k=scenario.top_k)
        bounds = scenario.gates[configured_name]
        value = measures[canonical]
        passed = True
        if bounds.min is not None and value < bounds.min:
            passed = False
        if bounds.max is not None and value > bounds.max:
            passed = False
        gate_results.append(
            GateEvaluation(
                metric=canonical,
                value=value,
                min=bounds.min,
                max=bounds.max,
                passed=passed,
            )
        )

    status: Literal["pass", "fail"] = (
        "pass" if all(gate.passed for gate in gate_results) else "fail"
    )
    regression_gates = {
        canonical_metric_name(name, top_k=scenario.top_k): bounds
        for name, bounds in scenario.regression_gates.items()
    }
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
        regression_gates=regression_gates,
    )
