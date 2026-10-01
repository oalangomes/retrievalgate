from pathlib import Path

from retrievalgate.evaluator import evaluate
from retrievalgate.models import AdapterResponse, Scenario
from retrievalgate.reporting import (
    format_console_report,
    format_junit_report,
    format_markdown_report,
    write_text_report,
)
from retrievalgate.results import build_suite_result


def _suite():
    scenario = Scenario.model_validate(
        {
            "schema_version": 1,
            "id": "report-case",
            "query": "find foo",
            "top_k": 2,
            "evaluation": {"cutoffs": [1, 2]},
            "ground_truth": {"relevant": ["foo"]},
            "gates": {"Recall@2": {"min": 1.0}},
        }
    )
    response = AdapterResponse.model_validate(
        {
            "protocol_version": 1,
            "results": [{"id": "foo"}, {"id": "noise"}],
            "telemetry": {
                "duration_ms": 10,
                "candidates_examined": 8,
                "candidates_returned": 2,
                "returned_chars": 400,
            },
        }
    )
    return build_suite_result([evaluate(scenario, response)])


def test_suite_aggregates_quality_and_operational_metrics() -> None:
    suite = _suite()

    assert suite.summary.metrics["Recall@2"] == 1.0
    assert suite.summary.metrics["MRR@2"] == 1.0
    assert suite.summary.metrics["EvidenceDensity@2"] == 0.5
    assert suite.summary.telemetry["duration_ms"] == 10.0
    assert suite.summary.telemetry_counts["duration_ms"] == 1


def test_console_markdown_and_junit_reports_are_clear(tmp_path: Path) -> None:
    suite = _suite()

    console = format_console_report(suite)
    markdown = format_markdown_report(suite)
    junit = format_junit_report(suite)

    assert "QUALITY" in console
    assert "EFFICIENCY" in console
    assert "PERFORMANCE / COST" in console
    assert "PASS report-case" in console
    assert "| Recall@2 | 1.000 | 1 |" in markdown
    assert '<testcase classname="retrievalgate" name="report-case"' in junit

    destination = tmp_path / "report.md"
    write_text_report(destination, markdown)
    assert destination.read_text(encoding="utf-8") == markdown
