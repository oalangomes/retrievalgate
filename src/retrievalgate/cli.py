"""Public CLI for retrievalgate."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from retrievalgate.adapter import run_adapter
from retrievalgate.comparison import compare_files, format_comparison
from retrievalgate.errors import RetrievalGateError
from retrievalgate.evaluator import evaluate
from retrievalgate.reporting import (
    format_console_report,
    format_junit_report,
    format_markdown_report,
    write_text_report,
)
from retrievalgate.results import build_suite_result, write_result
from retrievalgate.scenarios import load_scenarios

app = typer.Typer(
    no_args_is_help=True,
    help="Regression tests for retrieval.",
    add_completion=False,
)


def _error(message: str) -> None:
    typer.echo(f"ERROR: {message}", err=True)


@app.command()
def validate(path: Annotated[Path, typer.Argument()]) -> None:
    """Validate one scenario file or a directory of scenarios."""

    try:
        scenarios = load_scenarios(path)
    except RetrievalGateError as exc:
        _error(str(exc))
        raise typer.Exit(code=2) from exc

    typer.echo(f"Validated {len(scenarios)} scenario(s).")


@app.command()
def run(
    path: Annotated[Path, typer.Argument()],
    adapter: Annotated[str, typer.Option("--adapter", help="External retriever command.")],
    output: Annotated[
        Path | None, typer.Option("--output", help="Write canonical JSON result.")
    ] = None,
    markdown: Annotated[
        Path | None, typer.Option("--markdown", help="Write a Markdown report.")
    ] = None,
    junit: Annotated[
        Path | None, typer.Option("--junit", help="Write a JUnit XML report.")
    ] = None,
    timeout: Annotated[
        float, typer.Option("--timeout", min=0.001, help="Adapter timeout in seconds.")
    ] = 30.0,
) -> None:
    """Execute scenarios and fail when a retrieval contract fails."""

    try:
        scenarios = load_scenarios(path)
        scenario_results = []
        for scenario in scenarios:
            response = run_adapter(adapter, scenario, timeout)
            scenario_results.append(evaluate(scenario, response))

        suite = build_suite_result(scenario_results)
        if output is not None:
            write_result(output, suite)
        if markdown is not None:
            write_text_report(markdown, format_markdown_report(suite))
        if junit is not None:
            write_text_report(junit, format_junit_report(suite))

        typer.echo(format_console_report(suite))
        if suite.status == "fail":
            raise typer.Exit(code=1)
    except RetrievalGateError as exc:
        _error(str(exc))
        raise typer.Exit(code=2) from exc


@app.command()
def compare(
    baseline: Annotated[Path, typer.Argument(help="Baseline result JSON.")],
    current: Annotated[Path, typer.Argument(help="Current result JSON.")],
) -> None:
    """Compare two compatible structured result files."""

    try:
        comparison = compare_files(baseline, current)
    except RetrievalGateError as exc:
        _error(str(exc))
        raise typer.Exit(code=2) from exc

    typer.echo(format_comparison(comparison))
    if comparison.exit_code:
        raise typer.Exit(code=comparison.exit_code)


if __name__ == "__main__":
    app()
