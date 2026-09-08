"""Public CLI for retrievalgate."""

from __future__ import annotations

from pathlib import Path

import typer

from retrievalgate.adapter import run_adapter
from retrievalgate.errors import RetrievalGateError
from retrievalgate.evaluator import evaluate
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
def validate(path: Path = typer.Argument(..., exists=False)) -> None:
    """Validate one scenario file or a directory of scenarios."""

    try:
        scenarios = load_scenarios(path)
    except RetrievalGateError as exc:
        _error(str(exc))
        raise typer.Exit(code=2) from exc

    typer.echo(f"Validated {len(scenarios)} scenario(s).")


@app.command()
def run(
    path: Path = typer.Argument(..., exists=False),
    adapter: str = typer.Option(..., "--adapter", help="External retriever command."),
    output: Path | None = typer.Option(None, "--output", help="Write structured JSON result."),
    timeout: float = typer.Option(30.0, "--timeout", min=0.001, help="Adapter timeout in seconds."),
) -> None:
    """Execute scenarios and fail when a retrieval contract fails."""

    try:
        scenarios = load_scenarios(path)
        scenario_results = []
        for scenario in scenarios:
            response = run_adapter(adapter, scenario, timeout)
            result = evaluate(scenario, response)
            scenario_results.append(result)

            marker = "PASS" if result.status == "pass" else "FAIL"
            metrics = result.metrics
            typer.echo(
                f"{marker} {result.id} | recall={metrics.recall:.3f} "
                f"rr={metrics.rr:.3f} results={metrics.result_count}"
            )
            if result.expected.missing:
                typer.echo(f"  missing: {', '.join(result.expected.missing)}")

        suite = build_suite_result(scenario_results)
        if output is not None:
            write_result(output, suite)

        typer.echo(
            f"{suite.status.upper()} {suite.summary.passed}/{suite.summary.scenarios} scenarios "
            f"| MRR={suite.summary.mrr:.3f}"
        )
        if suite.status == "fail":
            raise typer.Exit(code=1)
    except RetrievalGateError as exc:
        _error(str(exc))
        raise typer.Exit(code=2) from exc


if __name__ == "__main__":
    app()
