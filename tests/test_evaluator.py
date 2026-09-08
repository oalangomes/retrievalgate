from retrievalgate.evaluator import evaluate
from retrievalgate.models import AdapterResponse, Scenario


def _response(*ids: str) -> AdapterResponse:
    return AdapterResponse.model_validate(
        {"protocol_version": 1, "results": [{"id": item} for item in ids]}
    )


def test_partial_ground_truth_computes_safe_metrics_only() -> None:
    scenario = Scenario.model_validate(
        {
            "schema_version": 1,
            "id": "partial",
            "query": "find medication history",
            "top_k": 3,
            "ground_truth": {"relevant": ["service", "controller"]},
            "gates": {"recall": {"min": 1.0}},
        }
    )

    result = evaluate(scenario, _response("service", "routes", "controller"))

    assert result.status == "pass"
    assert result.metrics.recall == 1.0
    assert result.metrics.rr == 1.0
    assert result.metrics.result_count == 3
    assert result.metrics.precision is None
    assert result.metrics.unexpected_count is None
    assert result.expected.ranks == {"service": 1, "controller": 3}


def test_missing_expected_item_fails_recall_gate() -> None:
    scenario = Scenario.model_validate(
        {
            "schema_version": 1,
            "id": "regression",
            "query": "find medication history",
            "top_k": 2,
            "ground_truth": {"relevant": ["service", "controller"]},
            "gates": {"recall": {"min": 1.0}},
        }
    )

    result = evaluate(scenario, _response("service", "routes"))

    assert result.status == "fail"
    assert result.metrics.recall == 0.5
    assert result.expected.missing == ["controller"]
    assert result.gates[0].passed is False


def test_exhaustive_ground_truth_enables_precision_and_unexpected_count() -> None:
    scenario = Scenario.model_validate(
        {
            "schema_version": 1,
            "id": "exhaustive",
            "query": "find foo",
            "top_k": 4,
            "ground_truth": {"relevant": ["a", "b"], "exhaustive": True},
            "gates": {
                "precision": {"min": 0.5},
                "unexpected_count": {"max": 2},
            },
        }
    )

    result = evaluate(scenario, _response("a", "noise", "b", "other", "ignored"))

    assert result.metrics.precision == 0.5
    assert result.metrics.unexpected_count == 2
    assert result.status == "pass"
