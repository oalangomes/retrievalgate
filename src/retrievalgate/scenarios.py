"""Scenario loading, validation, and deterministic fingerprinting."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from retrievalgate.errors import ScenarioError
from retrievalgate.models import Scenario


def _scenario_paths(path: Path) -> list[Path]:
    if not path.exists():
        raise ScenarioError(f"scenario path does not exist: {path}")
    if path.is_file():
        if path.suffix.lower() not in {".yaml", ".yml"}:
            raise ScenarioError(f"scenario file must be YAML: {path}")
        return [path]

    paths = sorted(
        candidate
        for candidate in path.rglob("*")
        if candidate.is_file() and candidate.suffix.lower() in {".yaml", ".yml"}
    )
    if not paths:
        raise ScenarioError(f"no .yaml or .yml scenarios found under: {path}")
    return paths


def load_scenarios(path: Path) -> list[Scenario]:
    """Load a file or directory of YAML scenarios in deterministic order."""

    scenarios: list[Scenario] = []
    seen_ids: dict[str, Path] = {}

    for scenario_path in _scenario_paths(path):
        try:
            raw: Any = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise ScenarioError(f"cannot read {scenario_path}: {exc}") from exc

        if not isinstance(raw, dict):
            raise ScenarioError(f"{scenario_path}: scenario root must be a mapping/object")

        try:
            scenario = Scenario.model_validate(raw)
        except ValidationError as exc:
            raise ScenarioError(f"{scenario_path}:\n{exc}") from exc

        previous = seen_ids.get(scenario.id)
        if previous is not None:
            raise ScenarioError(
                f"duplicate scenario id '{scenario.id}' in {previous} and {scenario_path}"
            )
        seen_ids[scenario.id] = scenario_path
        scenarios.append(scenario)

    return scenarios


def scenario_fingerprint(scenario: Scenario) -> str:
    """Return a stable SHA-256 over the normalized scenario contract."""

    payload = json.dumps(
        scenario.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"
