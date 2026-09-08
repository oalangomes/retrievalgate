from pathlib import Path

from typer.testing import CliRunner

from retrievalgate.cli import app
from retrievalgate.evaluator import evaluate
from retrievalgate.models import AdapterResponse, Scenario
from retrievalgate.results import build_suite_result, write_result

runner = CliRunner()


def _suite(found: bool):
    scenario = Scenario.model_validate(
        {
            "schema_version": 1,
            "id": "compare-case",
            "query": "find foo",
            "top_k": 1,
            "ground_truth": {"relevant": ["foo"]},
            "gates": {"recall": {"min": 1.0}},
        }
    )
    result_id = "foo" if found else "noise"
    response = AdapterResponse.model_validate(
        {"protocol_version": 1, "results": [{"id": result_id}]}
    )
    return build_suite_result([evaluate(scenario, response)])


def test_compare_command_returns_one_when_current_contract_fails(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    write_result(baseline, _suite(True))
    write_result(current, _suite(False))

    result = runner.invoke(app, ["compare", str(baseline), str(current)])

    assert result.exit_code == 1
    assert "compare-case PASS -> FAIL" in result.stdout
    assert "Missing: foo (was rank 1)" in result.stdout
    assert "CURRENT FAIL" in result.stdout


def test_compare_command_returns_two_for_invalid_result(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    baseline.write_text("not-json", encoding="utf-8")
    write_result(current, _suite(True))

    result = runner.invoke(app, ["compare", str(baseline), str(current)])

    assert result.exit_code == 2
    assert "ERROR: invalid retrievalgate result" in result.stderr
