"""Versioned public contracts for scenarios and command adapters."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SUPPORTED_GATE_METRICS = {
    "recall",
    "rr",
    "result_count",
    "precision",
    "unexpected_count",
}
EXHAUSTIVE_ONLY_METRICS = {"precision", "unexpected_count"}


class StrictModel(BaseModel):
    """Reject unknown fields so contract drift is explicit."""

    model_config = ConfigDict(extra="forbid")


class GateBounds(StrictModel):
    """Inclusive numeric bounds for a metric."""

    min: float | None = None
    max: float | None = None

    @model_validator(mode="after")
    def validate_bounds(self) -> GateBounds:
        if self.min is None and self.max is None:
            raise ValueError("a gate must define at least one of 'min' or 'max'")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("gate 'min' cannot be greater than 'max'")
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
    ground_truth: GroundTruth
    gates: dict[str, GateBounds] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_contract(self) -> Scenario:
        self.id = self.id.strip()
        self.query = self.query.strip()
        if not self.id:
            raise ValueError("scenario id cannot be blank")
        if not self.query:
            raise ValueError("query cannot be blank")

        unknown = sorted(set(self.gates) - SUPPORTED_GATE_METRICS)
        if unknown:
            supported = ", ".join(sorted(SUPPORTED_GATE_METRICS))
            raise ValueError(
                f"unsupported gate metric(s): {', '.join(unknown)}; supported: {supported}"
            )

        if not self.ground_truth.exhaustive:
            invalid = sorted(set(self.gates) & EXHAUSTIVE_ONLY_METRICS)
            if invalid:
                raise ValueError(
                    "precision/unexpected_count require ground_truth.exhaustive=true "
                    f"(invalid: {', '.join(invalid)})"
                )
        return self


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


class AdapterResponse(StrictModel):
    """JSON expected from an external retriever on stdout."""

    protocol_version: Literal[1]
    results: list[RetrievalItem]

    @model_validator(mode="after")
    def validate_unique_ids(self) -> AdapterResponse:
        ids = [item.id for item in self.results]
        if len(set(ids)) != len(ids):
            raise ValueError("adapter results cannot contain duplicate IDs")
        return self


class MetricValues(StrictModel):
    """Deterministic metrics for one scenario."""

    recall: float
    rr: float
    result_count: int
    precision: float | None = None
    unexpected_count: int | None = None


class ExpectedResults(StrictModel):
    """Diagnostic view of known relevant IDs."""

    total: int
    found: int
    missing: list[str]
    ranks: dict[str, int | None]


class GateEvaluation(StrictModel):
    """Evaluation result for one configured gate."""

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


class SuiteSummary(StrictModel):
    """Stable aggregate values for a run."""

    scenarios: int
    passed: int
    failed: int
    mrr: float


class SuiteResult(StrictModel):
    """Versioned machine-readable output."""

    schema_version: Literal[1] = 1
    tool: dict[str, str]
    status: Literal["pass", "fail"]
    summary: SuiteSummary
    scenarios: list[ScenarioResult]
