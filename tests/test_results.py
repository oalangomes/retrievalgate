from retrievalgate.evaluator import evaluate
from retrievalgate.models import AdapterResponse, Scenario
from retrievalgate.results import build_suite_result, serialize_result


def test_suite_serialization_is_deterministic() -> None:
    scenario = Scenario.model_validate(
        {
            "schema_version": 1,
            "id": "stable",
            "query": "find foo",
            "ground_truth": {"relevant": ["foo"]},
            "gates": {"recall": {"min": 1.0}},
        }
    )
    response = AdapterResponse.model_validate(
        {"protocol_version": 1, "results": [{"id": "foo"}]}
    )
    suite = build_suite_result([evaluate(scenario, response)])

    assert serialize_result(suite) == serialize_result(suite)
    assert '"schema_version": 1' in serialize_result(suite)
