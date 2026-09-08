import json
import sys
from pathlib import Path

from typer.testing import CliRunner

from retrievalgate.cli import app

runner = CliRunner()


def _write_scenario(path: Path) -> None:
    path.write_text(
        """schema_version: 1
id: cli-case
query: find foo
top_k: 2
ground_truth:
  relevant:
    - foo
gates:
  recall:
    min: 1.0
""",
        encoding="utf-8",
    )


def test_validate_returns_zero_for_valid_scenario(tmp_path: Path) -> None:
    scenario = tmp_path / "scenario.yaml"
    _write_scenario(scenario)

    result = runner.invoke(app, ["validate", str(scenario)])

    assert result.exit_code == 0
    assert "Validated 1 scenario(s)." in result.stdout


def test_run_writes_json_and_returns_zero_on_pass(tmp_path: Path) -> None:
    scenario = tmp_path / "scenario.yaml"
    output = tmp_path / "result.json"
    adapter = tmp_path / "adapter.py"
    _write_scenario(scenario)
    adapter.write_text(
        """import json, sys
json.load(sys.stdin)
json.dump({'protocol_version': 1, 'results': [{'id': 'foo'}]}, sys.stdout)
""",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "run",
            str(scenario),
            "--adapter",
            f'{sys.executable} "{adapter}"',
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
    assert payload["summary"]["mrr"] == 1.0


def test_run_returns_one_on_contract_failure(tmp_path: Path) -> None:
    scenario = tmp_path / "scenario.yaml"
    adapter = tmp_path / "adapter.py"
    _write_scenario(scenario)
    adapter.write_text(
        """import json, sys
json.load(sys.stdin)
json.dump({'protocol_version': 1, 'results': [{'id': 'bar'}]}, sys.stdout)
""",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["run", str(scenario), "--adapter", f'{sys.executable} "{adapter}"'],
    )

    assert result.exit_code == 1
    assert "FAIL cli-case" in result.stdout


def test_run_returns_two_on_adapter_error(tmp_path: Path) -> None:
    scenario = tmp_path / "scenario.yaml"
    adapter = tmp_path / "adapter.py"
    _write_scenario(scenario)
    adapter.write_text("raise SystemExit(3)\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["run", str(scenario), "--adapter", f'{sys.executable} "{adapter}"'],
    )

    assert result.exit_code == 2
    assert "ERROR:" in result.stderr
