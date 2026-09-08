import sys
from pathlib import Path

import pytest

from retrievalgate.adapter import run_adapter
from retrievalgate.errors import AdapterError
from retrievalgate.models import Scenario


def _scenario() -> Scenario:
    return Scenario.model_validate(
        {
            "schema_version": 1,
            "id": "adapter",
            "query": "find foo",
            "top_k": 2,
            "ground_truth": {"relevant": ["foo"]},
        }
    )


def test_command_adapter_uses_json_stdin_stdout(tmp_path: Path) -> None:
    script = tmp_path / "adapter.py"
    script.write_text(
        """import json, sys
request = json.load(sys.stdin)
assert request == {
    'protocol_version': 1,
    'scenario_id': 'adapter',
    'query': 'find foo',
    'top_k': 2,
}
json.dump({'protocol_version': 1, 'results': [{'id': 'foo', 'score': 0.9}]}, sys.stdout)
""",
        encoding="utf-8",
    )

    response = run_adapter(f'{sys.executable} "{script}"', _scenario(), timeout=5)
    assert response.results[0].id == "foo"


def test_command_adapter_rejects_duplicate_ids(tmp_path: Path) -> None:
    script = tmp_path / "adapter.py"
    script.write_text(
        """import json
print(json.dumps({'protocol_version': 1, 'results': [{'id': 'foo'}, {'id': 'foo'}]}))
""",
        encoding="utf-8",
    )

    with pytest.raises(AdapterError, match="duplicate IDs"):
        run_adapter(f'{sys.executable} "{script}"', _scenario(), timeout=5)
