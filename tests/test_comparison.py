import pytest

from retrievalgate.comparison import compare_results, format_comparison
from retrievalgate.errors import ComparisonError
from retrievalgate.evaluator import evaluate
from retrievalgate.models import AdapterResponse, Scenario
from retrievalgate.results import build_suite_result


def _scenario(scenario_id: str = "case") -> Scenario:
    return Scenario.model_validate(
        {
            "schema_version": 1,
            "id": scenario_id,
            "query": "find relevant context",
            "top_k": 3,
            "ground_truth": {"relevant": ["a", "b", "c"]},
            "gates": {"recall": {"min": 0.5}},
        }
    )


def _response(*ids: str) -> AdapterResponse:
    return AdapterResponse.model_validate(
        {"protocol_version": 1, "results": [{"id": item} for item in ids]}
    )


def test_compare_reports_missing_recovered_rank_and_metric_deltas() -> None:
    scenario = _scenario()
    baseline = build_suite_result([evaluate(scenario, _response("a", "noise", "c"))])
    current = build_suite_result([evaluate(scenario, _response("c", "noise", "b"))])

    comparison = compare_results(baseline, current)
    result = comparison.scenarios[0]

    assert result.missing == (("a", 1),)
    assert result.recovered == (("b", 3),)
    assert [(item.id, item.baseline, item.current) for item in result.rank_changes] == [
        ("c", 3, 1)
    ]
    recall = next(metric for metric in result.metrics if metric.name == "recall")
    assert recall.delta == 0.0

    output = format_comparison(comparison)
    assert "Missing: a (was rank 1)" in output
    assert "Recovered: b (now rank 3)" in output
    assert "Rank: c 3 -> 1" in output


def test_compare_rejects_changed_scenario_contract() -> None:
    baseline_scenario = _scenario()
    current_scenario = Scenario.model_validate(
        {
            **baseline_scenario.model_dump(mode="python"),
            "query": "changed query",
        }
    )
    baseline = build_suite_result(
        [evaluate(baseline_scenario, _response("a", "b", "c"))]
    )
    current = build_suite_result(
        [evaluate(current_scenario, _response("a", "b", "c"))]
    )

    with pytest.raises(ComparisonError, match="fingerprints differ"):
        compare_results(baseline, current)


def test_compare_rejects_different_scenario_sets() -> None:
    baseline_scenario = _scenario("baseline-only")
    current_scenario = _scenario("current-only")
    baseline = build_suite_result([evaluate(baseline_scenario, _response("a"))])
    current = build_suite_result([evaluate(current_scenario, _response("a"))])

    with pytest.raises(ComparisonError, match="scenario sets differ"):
        compare_results(baseline, current)


def test_compare_orders_scenarios_deterministically() -> None:
    a = _scenario("a-case")
    z = _scenario("z-case")
    baseline = build_suite_result(
        [
            evaluate(z, _response("a", "b")),
            evaluate(a, _response("a", "b")),
        ]
    )
    current = build_suite_result(
        [
            evaluate(a, _response("a", "b")),
            evaluate(z, _response("a", "b")),
        ]
    )

    comparison = compare_results(baseline, current)

    assert [scenario.id for scenario in comparison.scenarios] == ["a-case", "z-case"]


def test_compare_exit_code_tracks_current_absolute_gates() -> None:
    scenario = _scenario()
    baseline = build_suite_result([evaluate(scenario, _response("a", "b", "c"))])
    current = build_suite_result([evaluate(scenario, _response("noise"))])

    comparison = compare_results(baseline, current)

    assert comparison.baseline_status == "pass"
    assert comparison.current_status == "fail"
    assert comparison.exit_code == 1
    assert "REGRESSION: PASS -> FAIL" in format_comparison(comparison)
