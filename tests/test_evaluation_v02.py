import math

import pytest

from retrievalgate.evaluator import evaluate
from retrievalgate.models import AdapterResponse, Scenario


def test_multiple_cutoffs_compute_canonical_metrics() -> None:
    scenario = Scenario.model_validate(
        {
            "schema_version": 1,
            "id": "cutoffs",
            "query": "find code",
            "top_k": 4,
            "evaluation": {"cutoffs": [1, 2, 4]},
            "ground_truth": {"relevant": ["a", "c"]},
            "gates": {
                "Success@1": {"min": 1.0},
                "Recall@4": {"min": 1.0},
                "nDCG@4": {"min": 0.9},
            },
        }
    )
    response = AdapterResponse.model_validate(
        {
            "protocol_version": 1,
            "results": [{"id": item} for item in ("a", "noise", "c", "other")],
        }
    )

    result = evaluate(scenario, response)

    assert result.metrics.measures["Success@1"] == 1.0
    assert result.metrics.measures["Recall@1"] == 0.5
    assert result.metrics.measures["Recall@2"] == 0.5
    assert result.metrics.measures["Recall@4"] == 1.0
    expected_ndcg = (1.0 + 1.0 / math.log2(4)) / (1.0 + 1.0 / math.log2(3))
    assert result.metrics.measures["nDCG@4"] == pytest.approx(expected_ndcg)
    assert result.metrics.measures["EvidenceDensity@4"] == 0.5
    assert result.status == "pass"


def test_adapter_telemetry_is_preserved_without_affecting_quality() -> None:
    scenario = Scenario.model_validate(
        {
            "schema_version": 1,
            "id": "telemetry",
            "query": "find code",
            "top_k": 2,
            "ground_truth": {"relevant": ["a"]},
        }
    )
    response = AdapterResponse.model_validate(
        {
            "protocol_version": 1,
            "results": [{"id": "a"}, {"id": "noise"}],
            "telemetry": {
                "duration_ms": 12.5,
                "candidates_examined": 80,
                "candidates_returned": 2,
                "returned_chars": 1200,
            },
        }
    )

    result = evaluate(scenario, response)

    assert result.metrics.recall == 1.0
    assert result.metrics.telemetry is not None
    assert result.metrics.telemetry.duration_ms == 12.5
    assert result.metrics.telemetry.candidates_examined == 80


def test_evidence_density_uses_returned_results_not_requested_cutoff() -> None:
    scenario = Scenario.model_validate(
        {
            "schema_version": 1,
            "id": "density",
            "query": "find code",
            "top_k": 5,
            "ground_truth": {"relevant": ["a", "b"]},
        }
    )
    response = AdapterResponse.model_validate(
        {
            "protocol_version": 1,
            "results": [{"id": "a"}, {"id": "noise"}],
        }
    )

    result = evaluate(scenario, response)

    assert result.metrics.measures["Recall@5"] == 0.5
    assert result.metrics.measures["EvidenceDensity@5"] == 0.5
    assert result.metrics.measures["ResultCount@5"] == 2.0
