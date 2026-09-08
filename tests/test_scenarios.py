from pathlib import Path

import pytest

from retrievalgate.errors import ScenarioError
from retrievalgate.models import Scenario
from retrievalgate.scenarios import load_scenarios, scenario_fingerprint


def test_partial_ground_truth_rejects_precision_gate() -> None:
    with pytest.raises(ValueError, match="require ground_truth.exhaustive=true"):
        Scenario.model_validate(
            {
                "schema_version": 1,
                "id": "partial",
                "query": "find foo",
                "ground_truth": {"relevant": ["foo"]},
                "gates": {"precision": {"min": 0.5}},
            }
        )


def test_scenario_fingerprint_is_stable() -> None:
    scenario = Scenario.model_validate(
        {
            "schema_version": 1,
            "id": "stable",
            "query": "find foo",
            "ground_truth": {"relevant": ["foo"]},
            "gates": {"recall": {"min": 1.0}},
        }
    )
    assert scenario_fingerprint(scenario) == scenario_fingerprint(scenario)
    assert scenario_fingerprint(scenario).startswith("sha256:")


def test_load_scenarios_rejects_duplicate_ids(tmp_path: Path) -> None:
    payload = """schema_version: 1
id: same
query: find foo
ground_truth:
  relevant: [foo]
"""
    (tmp_path / "a.yaml").write_text(payload, encoding="utf-8")
    (tmp_path / "b.yaml").write_text(payload, encoding="utf-8")

    with pytest.raises(ScenarioError, match="duplicate scenario id"):
        load_scenarios(tmp_path)
