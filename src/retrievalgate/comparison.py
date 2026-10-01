"""Deterministic comparison of retrievalgate structured results."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from retrievalgate.errors import ComparisonError
from retrievalgate.models import RegressionGateBounds, ScenarioResult, SuiteResult

_LEGACY_METRIC_NAMES = ("recall", "rr", "result_count", "precision", "unexpected_count")


@dataclass(frozen=True)
class MetricDelta:
    """One metric before/after delta."""

    name: str
    baseline: float | int
    current: float | int

    @property
    def delta(self) -> float:
        return float(self.current) - float(self.baseline)


@dataclass(frozen=True)
class RankDelta:
    """Rank change for one expected result that exists in both runs."""

    id: str
    baseline: int
    current: int


@dataclass(frozen=True)
class RegressionEvaluation:
    """One explicit baseline-relative regression contract."""

    metric: str
    baseline: float
    current: float
    max_drop: float | None
    max_increase: float | None
    passed: bool

    @property
    def delta(self) -> float:
        return self.current - self.baseline


@dataclass(frozen=True)
class ScenarioComparison:
    """Comparable changes for one scenario."""

    id: str
    baseline_status: Literal["pass", "fail"]
    current_status: Literal["pass", "fail"]
    metrics: tuple[MetricDelta, ...]
    missing: tuple[tuple[str, int], ...]
    recovered: tuple[tuple[str, int], ...]
    rank_changes: tuple[RankDelta, ...]
    regressions: tuple[RegressionEvaluation, ...]


@dataclass(frozen=True)
class SuiteComparison:
    """Deterministic comparison between two compatible suites."""

    baseline_status: Literal["pass", "fail"]
    current_status: Literal["pass", "fail"]
    baseline_mrr: float
    current_mrr: float
    suite_metrics: tuple[MetricDelta, ...]
    scenarios: tuple[ScenarioComparison, ...]

    @property
    def regression_failed(self) -> bool:
        return any(
            not evaluation.passed
            for scenario in self.scenarios
            for evaluation in scenario.regressions
        )

    @property
    def exit_code(self) -> int:
        """Fail for an absolute contract failure or an explicit regression gate."""

        return 1 if self.current_status == "fail" or self.regression_failed else 0


def load_result(path: Path) -> SuiteResult:
    """Load and validate one retrievalgate structured result file."""

    try:
        payload = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ComparisonError(f"cannot read result file {path}: {exc}") from exc

    try:
        return SuiteResult.model_validate_json(payload)
    except ValidationError as exc:
        raise ComparisonError(f"invalid retrievalgate result {path}:\n{exc}") from exc


def _index_scenarios(result: SuiteResult, label: str) -> dict[str, ScenarioResult]:
    indexed: dict[str, ScenarioResult] = {}
    for scenario in result.scenarios:
        if scenario.id in indexed:
            raise ComparisonError(f"{label} contains duplicate scenario id '{scenario.id}'")
        indexed[scenario.id] = scenario
    return indexed


def _validate_compatibility(
    baseline: dict[str, ScenarioResult],
    current: dict[str, ScenarioResult],
) -> None:
    baseline_ids = set(baseline)
    current_ids = set(current)
    if baseline_ids != current_ids:
        removed = sorted(baseline_ids - current_ids)
        added = sorted(current_ids - baseline_ids)
        details: list[str] = []
        if removed:
            details.append(f"missing from current: {', '.join(removed)}")
        if added:
            details.append(f"new in current: {', '.join(added)}")
        raise ComparisonError("scenario sets differ; " + "; ".join(details))

    mismatched = sorted(
        scenario_id
        for scenario_id in baseline_ids
        if baseline[scenario_id].scenario_fingerprint
        != current[scenario_id].scenario_fingerprint
    )
    if mismatched:
        raise ComparisonError(
            "scenario fingerprints differ for: "
            + ", ".join(mismatched)
            + "; compare results generated from the same scenario contracts"
        )


def _mapping_deltas(
    baseline: dict[str, float],
    current: dict[str, float],
    *,
    label: str,
) -> tuple[MetricDelta, ...]:
    if set(baseline) != set(current):
        raise ComparisonError(f"{label} metric availability differs between results")
    return tuple(
        MetricDelta(name=name, baseline=baseline[name], current=current[name])
        for name in sorted(baseline)
    )


def _metric_deltas(
    baseline: ScenarioResult,
    current: ScenarioResult,
) -> tuple[MetricDelta, ...]:
    if baseline.metrics.measures or current.metrics.measures:
        return _mapping_deltas(
            baseline.metrics.measures,
            current.metrics.measures,
            label=f"scenario '{baseline.id}'",
        )

    deltas: list[MetricDelta] = []
    for name in _LEGACY_METRIC_NAMES:
        baseline_value = getattr(baseline.metrics, name)
        current_value = getattr(current.metrics, name)
        if baseline_value is None and current_value is None:
            continue
        if baseline_value is None or current_value is None:
            raise ComparisonError(
                f"metric availability differs for scenario '{baseline.id}': {name}"
            )
        deltas.append(
            MetricDelta(
                name=name,
                baseline=baseline_value,
                current=current_value,
            )
        )
    return tuple(deltas)


def _rank_deltas(
    baseline: ScenarioResult,
    current: ScenarioResult,
) -> tuple[
    tuple[tuple[str, int], ...],
    tuple[tuple[str, int], ...],
    tuple[RankDelta, ...],
]:
    baseline_ranks = baseline.expected.ranks
    current_ranks = current.expected.ranks
    if set(baseline_ranks) != set(current_ranks):
        raise ComparisonError(
            f"expected result IDs differ for scenario '{baseline.id}' despite matching fingerprint"
        )

    missing: list[tuple[str, int]] = []
    recovered: list[tuple[str, int]] = []
    changed: list[RankDelta] = []

    for result_id in sorted(baseline_ranks):
        before = baseline_ranks[result_id]
        after = current_ranks[result_id]
        if before is not None and after is None:
            missing.append((result_id, before))
        elif before is None and after is not None:
            recovered.append((result_id, after))
        elif before is not None and after is not None and before != after:
            changed.append(RankDelta(id=result_id, baseline=before, current=after))

    return tuple(missing), tuple(recovered), tuple(changed)


def _regression_evaluation(
    metric: str,
    bounds: RegressionGateBounds,
    baseline: ScenarioResult,
    current: ScenarioResult,
) -> RegressionEvaluation:
    try:
        before = baseline.metrics.measures[metric]
        after = current.metrics.measures[metric]
    except KeyError as exc:
        raise ComparisonError(
            f"regression metric {metric!r} is unavailable for scenario '{baseline.id}'"
        ) from exc

    delta = after - before
    passed = True
    if bounds.max_drop is not None and delta < -bounds.max_drop:
        passed = False
    if bounds.max_increase is not None and delta > bounds.max_increase:
        passed = False
    return RegressionEvaluation(
        metric=metric,
        baseline=before,
        current=after,
        max_drop=bounds.max_drop,
        max_increase=bounds.max_increase,
        passed=passed,
    )


def compare_results(baseline: SuiteResult, current: SuiteResult) -> SuiteComparison:
    """Compare compatible suites and apply only explicitly configured regression gates."""

    baseline_index = _index_scenarios(baseline, "baseline")
    current_index = _index_scenarios(current, "current")
    _validate_compatibility(baseline_index, current_index)

    scenarios: list[ScenarioComparison] = []
    for scenario_id in sorted(baseline_index):
        before = baseline_index[scenario_id]
        after = current_index[scenario_id]
        missing, recovered, rank_changes = _rank_deltas(before, after)
        regressions = tuple(
            _regression_evaluation(metric, bounds, before, after)
            for metric, bounds in sorted(after.regression_gates.items())
        )
        scenarios.append(
            ScenarioComparison(
                id=scenario_id,
                baseline_status=before.status,
                current_status=after.status,
                metrics=_metric_deltas(before, after),
                missing=missing,
                recovered=recovered,
                rank_changes=rank_changes,
                regressions=regressions,
            )
        )

    suite_metrics = ()
    if baseline.summary.metrics or current.summary.metrics:
        suite_metrics = _mapping_deltas(
            baseline.summary.metrics,
            current.summary.metrics,
            label="suite",
        )

    return SuiteComparison(
        baseline_status=baseline.status,
        current_status=current.status,
        baseline_mrr=baseline.summary.mrr,
        current_mrr=current.summary.mrr,
        suite_metrics=suite_metrics,
        scenarios=tuple(scenarios),
    )


def compare_files(baseline_path: Path, current_path: Path) -> SuiteComparison:
    """Load and compare two retrievalgate result files."""

    return compare_results(load_result(baseline_path), load_result(current_path))


def _format_number(value: float | int) -> str:
    if isinstance(value, int):
        return str(value)
    return f"{value:.3f}"


def _format_delta(delta: float, *, integer: bool) -> str:
    if integer:
        return f"{int(delta):+d}"
    return f"{delta:+.3f}"


def format_comparison(comparison: SuiteComparison) -> str:
    """Render deterministic, CI-friendly comparison output."""

    lines = ["Retrieval Regression Report", ""]
    if comparison.suite_metrics:
        lines.append("Suite metrics")
        for metric in comparison.suite_metrics:
            lines.append(
                f"  {metric.name}: {metric.baseline:.3f} -> "
                f"{metric.current:.3f} ({metric.delta:+.3f})"
            )
    else:
        lines.append(
            f"Suite MRR {comparison.baseline_mrr:.3f} -> "
            f"{comparison.current_mrr:.3f} "
            f"({comparison.current_mrr - comparison.baseline_mrr:+.3f})"
        )

    for scenario in comparison.scenarios:
        lines.append("")
        lines.append(
            f"{scenario.id} {scenario.baseline_status.upper()} -> "
            f"{scenario.current_status.upper()}"
        )
        for metric in scenario.metrics:
            integer = isinstance(metric.baseline, int) and isinstance(metric.current, int)
            lines.append(
                f"  {metric.name}: {_format_number(metric.baseline)} -> "
                f"{_format_number(metric.current)} "
                f"({_format_delta(metric.delta, integer=integer)})"
            )

        for result_id, previous_rank in scenario.missing:
            lines.append(f"  Missing: {result_id} (was rank {previous_rank})")
        for result_id, current_rank in scenario.recovered:
            lines.append(f"  Recovered: {result_id} (now rank {current_rank})")
        for rank in scenario.rank_changes:
            lines.append(f"  Rank: {rank.id} {rank.baseline} -> {rank.current}")

        for regression in scenario.regressions:
            marker = "PASS" if regression.passed else "FAIL"
            bounds: list[str] = []
            if regression.max_drop is not None:
                bounds.append(f"max_drop={regression.max_drop:.3f}")
            if regression.max_increase is not None:
                bounds.append(f"max_increase={regression.max_increase:.3f}")
            lines.append(
                f"  {marker} regression {regression.metric}: "
                f"{regression.baseline:.3f} -> {regression.current:.3f} "
                f"({regression.delta:+.3f}; {', '.join(bounds)})"
            )

        if scenario.baseline_status == "pass" and scenario.current_status == "fail":
            lines.append("  REGRESSION: PASS -> FAIL")
        elif scenario.baseline_status == "fail" and scenario.current_status == "pass":
            lines.append("  RECOVERY: FAIL -> PASS")

    lines.append("")
    outcome = "FAIL" if comparison.exit_code else "PASS"
    lines.append(f"CURRENT {comparison.current_status.upper()} | REGRESSION {outcome}")
    return "\n".join(lines)
