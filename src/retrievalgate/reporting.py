"""Human and CI report rendering for retrievalgate results."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree

from retrievalgate.models import ScenarioResult, SuiteResult


def _metric_rows(suite: SuiteResult, prefixes: tuple[str, ...]) -> list[str]:
    rows: list[str] = []
    for name, value in sorted(suite.summary.metrics.items()):
        if name.startswith(prefixes):
            count = suite.summary.metric_counts.get(name, suite.summary.scenarios)
            suffix = "" if count == suite.summary.scenarios else f" (n={count})"
            rows.append(f"  {name:<24} {value:.3f}{suffix}")
    return rows


def format_console_report(suite: SuiteResult) -> str:
    """Render a concise report optimized for local use and CI logs."""

    lines = [
        "RetrievalGate",
        "",
        f"RESULT: {suite.status.upper()}",
        (
            f"Scenarios: {suite.summary.scenarios} | "
            f"Passed: {suite.summary.passed} | Failed: {suite.summary.failed}"
        ),
        "",
        "QUALITY",
    ]
    quality = _metric_rows(
        suite,
        ("Recall@", "Success@", "MRR@", "nDCG@", "Precision@"),
    )
    lines.extend(quality or ["  no quality metrics"])

    lines.extend(["", "EFFICIENCY"])
    efficiency = _metric_rows(
        suite,
        ("EvidenceDensity@", "ResultCount@", "UnexpectedCount@"),
    )
    lines.extend(efficiency or ["  no efficiency metrics"])

    if suite.summary.telemetry:
        lines.extend(["", "PERFORMANCE / COST"])
        labels = {
            "duration_ms": "Latency mean (ms)",
            "candidates_examined": "Candidates examined mean",
            "candidates_returned": "Candidates returned mean",
            "returned_chars": "Returned chars mean",
        }
        for name, value in sorted(suite.summary.telemetry.items()):
            count = suite.summary.telemetry_counts.get(name, 0)
            lines.append(f"  {labels.get(name, name):<24} {value:.3f} (n={count})")

    lines.extend(["", "SCENARIOS"])
    for scenario in suite.scenarios:
        marker = "PASS" if scenario.status == "pass" else "FAIL"
        lines.append(f"  {marker} {scenario.id}")
        if scenario.status == "fail":
            for gate in scenario.gates:
                if not gate.passed:
                    lines.append(
                        f"    {gate.metric}={gate.value:.3f} "
                        f"(min={gate.min}, max={gate.max})"
                    )
            if scenario.expected.missing:
                lines.append(f"    missing: {', '.join(scenario.expected.missing)}")
    return "\n".join(lines)


def format_markdown_report(suite: SuiteResult) -> str:
    """Render a deterministic Markdown report for CI summaries and PR artifacts."""

    lines = [
        "# RetrievalGate report",
        "",
        f"**Result:** {suite.status.upper()}",
        "",
        (
            f"Scenarios: **{suite.summary.scenarios}** · "
            f"Passed: **{suite.summary.passed}** · Failed: **{suite.summary.failed}**"
        ),
        "",
        "## Quality",
        "",
        "| Metric | Value | Scenarios |",
        "|---|---:|---:|",
    ]
    for name, value in sorted(suite.summary.metrics.items()):
        if name.startswith(("Recall@", "Success@", "MRR@", "nDCG@", "Precision@")):
            lines.append(
                f"| {name} | {value:.3f} | {suite.summary.metric_counts.get(name, 0)} |"
            )

    lines.extend(
        [
            "",
            "## Efficiency",
            "",
            "| Metric | Value | Scenarios |",
            "|---|---:|---:|",
        ]
    )
    for name, value in sorted(suite.summary.metrics.items()):
        if name.startswith(("EvidenceDensity@", "ResultCount@", "UnexpectedCount@")):
            lines.append(
                f"| {name} | {value:.3f} | {suite.summary.metric_counts.get(name, 0)} |"
            )

    if suite.summary.telemetry:
        lines.extend(
            [
                "",
                "## Performance / cost",
                "",
                "| Observation | Mean | Scenarios |",
                "|---|---:|---:|",
            ]
        )
        for name, value in sorted(suite.summary.telemetry.items()):
            lines.append(
                f"| {name} | {value:.3f} | "
                f"{suite.summary.telemetry_counts.get(name, 0)} |"
            )

    lines.extend(["", "## Scenarios", ""])
    for scenario in suite.scenarios:
        marker = "PASS" if scenario.status == "pass" else "FAIL"
        lines.append(f"- **{marker}** {scenario.id}")
        if scenario.expected.missing:
            lines.append(f"  - Missing: {', '.join(scenario.expected.missing)}")

    return "\n".join(lines) + "\n"


def _failure_text(scenario: ScenarioResult) -> str:
    lines = [
        (
            f"{gate.metric}={gate.value:.6f} "
            f"(min={gate.min}, max={gate.max})"
        )
        for gate in scenario.gates
        if not gate.passed
    ]
    if scenario.expected.missing:
        lines.append("missing: " + ", ".join(scenario.expected.missing))
    return "\n".join(lines) or "retrieval contract failed"


def format_junit_report(suite: SuiteResult) -> str:
    """Render one JUnit XML testsuite with one testcase per retrieval scenario."""

    root = ElementTree.Element(
        "testsuite",
        {
            "name": "retrievalgate",
            "tests": str(suite.summary.scenarios),
            "failures": str(suite.summary.failed),
            "errors": "0",
        },
    )
    for scenario in suite.scenarios:
        case = ElementTree.SubElement(
            root,
            "testcase",
            {"classname": "retrievalgate", "name": scenario.id},
        )
        if scenario.status == "fail":
            failure = ElementTree.SubElement(
                case,
                "failure",
                {"message": "retrieval contract failed"},
            )
            failure.text = _failure_text(scenario)
    return ElementTree.tostring(root, encoding="unicode") + "\n"


def write_text_report(path: Path, content: str) -> None:
    """Write a UTF-8 text report, creating parent directories."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
