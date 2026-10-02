"""Versioned public contracts for scenarios, adapters, and results."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LEGACY_GATE_ALIASES = {
    "recall": "Recall",
    "rr": "RR",
    "result_count": "ResultCount",
    "precision": "Precision",
    "unexpected_count": "UnexpectedCount",
}
CUTOFF_METRICS = {
    "Recall",
    "Success",
    "RR",
    "nDCG",
    "EvidenceDensity",
    "ResultCount",
    "Precision",
    "UnexpectedCount",
}
EXHAUSTIVE_ONLY_BASE_METRICS = {"Precision", "UnexpectedCount"}


class StrictModel(BaseModel):
    """Reject unknown fields so contract drift is explicit."""

    model_config = ConfigDict(extra="forbid")


def canonical_metric_name(name: str, *, top_k: int) -> str:
    """Normalize legacy and canonical scenario metric names."""

    raw = name.strip()
    if raw in LEGACY_GATE_ALIASES:
        return f"{LEGACY_GATE_ALIASES[raw]}@{top_k}"

    if "@" not in raw:
        supported = ", ".join(sorted(CUTOFF_METRICS))
        raise ValueError(
            f"unsupported metric {name!r}; use one of {supported} with an @K cutoff"
        )

    base, cutoff_raw = raw.rsplit("@", 1)
    if base not in CUTOFF_METRICS:
        supported = ", ".join(sorted(CUTOFF_METRICS))
        raise ValueError(f"unsupported metric {name!r}; supported metric families: {supported}")
    try:
        cutoff = int(cutoff_raw)
    except ValueError as exc:
        raise ValueError(f"metric cutoff must be an integer in {name!r}") from exc
    if cutoff < 1:
        raise ValueError(f"metric cutoff must be positive in {name!r}")
    return f"{base}@{cutoff}"


def metric_cutoff(name: str) -> int:
    """Return the cutoff from a canonical metric name."""

    return int(name.rsplit("@", 1)[1])


def metric_base(name: str) -> str:
    """Return the metric family from a canonical metric name."""

    return name.rsplit("@", 1)[0]


class GateBounds(StrictModel):
    """Inclusive numeric bounds for an absolute metric contract."""

    min: float | None = None
    max: float | None = None

    @model_validator(mode="after")
    def validate_bounds(self) -> GateBounds:
        if self.min is None and self.max is None:
            raise ValueError("a gate must define at least one of 'min' or 'max'")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("gate 'min' cannot be greater than 'max'")
        return self


class RegressionGateBounds(StrictModel):
    """Allowed relative movement between a baseline and current result."""

    max_drop: float | None = Field(default=None, ge=0)
    max_increase: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_bounds(self) -> RegressionGateBounds:
        if self.max_drop is None and self.max_increase is None:
            raise ValueError(
                "a regression gate must define at least one of 'max_drop' or 'max_increase'"
            )
        return self


class EvaluationConfig(StrictModel):
    """Optional extra cutoffs evaluated from one ranked result list."""

    cutoffs: list[int] = Field(min_length=1)

    @model_validator(mode="after")
    def normalize_cutoffs(self) -> EvaluationConfig:
        if any(cutoff < 1 for cutoff in self.cutoffs):
            raise ValueError("evaluation.cutoffs must contain positive integers")
        self.cutoffs = sorted(set(self.cutoffs))
        return self


class GroundTruth(StrictModel):
    """Known relevant result IDs for a scenario."""

    relevant: list[str] = Field(min_length=1)
    exhaustive: bool = False

    @model_validator(mode="after")
    def validate_relevant_ids(self) -> GroundTruth:
        normalized = [item.strip() for item in self.relevant]
        if any(not item for item in normalized):
            raise ValueError("ground_truth.relevant cannot contain empty IDs")
        if len(set(normalized)) != len(normalized):
            raise ValueError("ground_truth.relevant cannot contain duplicate IDs")
        self.relevant = normalized
        return self


class Scenario(StrictModel):
    """Executable retrieval expectation."""

    schema_version: Literal[1]
    id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    top_k: int = Field(default=20, gt=0)
    evaluation: EvaluationConfig | None = None
    ground_truth: GroundTruth
    gates: dict[str, GateBounds] = Field(default_factory=dict)
    regression_gates: dict[str, RegressionGateBounds] = Field(default_factory=dict)

    @property
    def cutoffs(self) -> tuple[int, ...]:
        """All requested cutoffs, always including top_k."""

        values = {self.top_k}
        if self.evaluation is not None:
            values.update(self.evaluation.cutoffs)
        return tuple(sorted(values))

    @model_validator(mode="after")
    def validate_contract(self) -> Scenario:
        self.id = self.id.strip()
        self.query = self.query.strip()
        if not self.id:
            raise ValueError("scenario id cannot be blank")
        if not self.query:
            raise ValueError("query cannot be blank")

        if self.evaluation is not None:
            too_large = [cutoff for cutoff in self.evaluation.cutoffs if cutoff > self.top_k]
            if too_large:
                rendered = ", ".join(str(item) for item in too_large)
                raise ValueError(
                    f"evaluation cutoffs cannot exceed top_k={self.top_k}: {rendered}"
                )

        self._validate_metric_mapping(self.gates, "gate")
        self._validate_metric_mapping(self.regression_gates, "regression gate")
        return self

    def _validate_metric_mapping(
        self,
        mapping: dict[str, GateBounds] | dict[str, RegressionGateBounds],
        label: str,
    ) -> None:
        for name in mapping:
            try:
                canonical = canonical_metric_name(name, top_k=self.top_k)
            except ValueError as exc:
                raise ValueError(f"invalid {label} metric {name!r}: {exc}") from exc
            cutoff = metric_cutoff(canonical)
            if cutoff not in self.cutoffs:
                raise ValueError(
                    f"{label} metric {canonical!r} requires cutoff {cutoff}; "
                    f"configured cutoffs are {list(self.cutoffs)}"
                )
            if (
                metric_base(canonical) in EXHAUSTIVE_ONLY_BASE_METRICS
                and not self.ground_truth.exhaustive
            ):
                raise ValueError(f"{canonical} requires ground_truth.exhaustive=true")


class AdapterRequest(StrictModel):
    """JSON sent to an external retriever on stdin."""

    protocol_version: Literal[1] = 1
    scenario_id: str
    query: str
    top_k: int


class RetrievalItem(StrictModel):
    """One ranked item returned by a retriever."""

    id: str = Field(min_length=1)
    score: float | None = None


class OperationalTelemetry(StrictModel):
    """Optional backend-neutral retrieval cost observations."""

    duration_ms: float | None = Field(default=None, ge=0)
    candidates_examined: int | None = Field(default=None, ge=0)
    candidates_returned: int | None = Field(default=None, ge=0)
    returned_chars: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def require_observation(self) -> OperationalTelemetry:
        if all(
            value is None
            for value in (
                self.duration_ms,
                self.candidates_examined,
                self.candidates_returned,
                self.returned_chars,
            )
        ):
            raise ValueError("telemetry must contain at least one observation")
        return self


class AdapterResponse(StrictModel):
    """JSON expected from an external retriever on stdout."""

    protocol_version: Literal[1]
    results: list[RetrievalItem]
    telemetry: OperationalTelemetry | None = None

    @model_validator(mode="after")
    def validate_unique_ids(self) -> AdapterResponse:
        ids = [item.id for item in self.results]
        if len(set(ids)) != len(ids):
            raise ValueError("adapter results cannot contain duplicate IDs")
        return self


class MetricValues(StrictModel):
    """Deterministic metrics for one scenario.

    Legacy v0.1 fields remain available while canonical @K measures are the
    preferred machine-readable representation.
    """

    recall: float
    rr: float
    result_count: int
    precision: float | None = None
    unexpected_count: int | None = None
    measures: dict[str, float] = Field(default_factory=dict)
    telemetry: OperationalTelemetry | None = None


class ExpectedResults(StrictModel):
    """Diagnostic view of known relevant IDs."""

    total: int
    found: int
    missing: list[str]
    ranks: dict[str, int | None]


class GateEvaluation(StrictModel):
    """Evaluation result for one configured absolute gate."""

    metric: str
    value: float
    min: float | None = None
    max: float | None = None
    passed: bool


class ScenarioResult(StrictModel):
    """Structured result for one scenario."""

    id: str
    scenario_fingerprint: str
    status: Literal["pass", "fail"]
    top_k: int
    metrics: MetricValues
    expected: ExpectedResults
    gates: list[GateEvaluation]
    regression_gates: dict[str, RegressionGateBounds] = Field(default_factory=dict)


class SuiteSummary(StrictModel):
    """Stable aggregate values for a run."""

    scenarios: int
    passed: int
    failed: int
    mrr: float
    metrics: dict[str, float] = Field(default_factory=dict)
    metric_counts: dict[str, int] = Field(default_factory=dict)
    telemetry: dict[str, float] = Field(default_factory=dict)
    telemetry_counts: dict[str, int] = Field(default_factory=dict)


class SuiteResult(StrictModel):
    """Versioned machine-readable output."""

    schema_version: Literal[1] = 1
    tool: dict[str, str]
    status: Literal["pass", "fail"]
    summary: SuiteSummary
    scenarios: list[ScenarioResult]
