"""Backend-agnostic external command adapter."""

from __future__ import annotations

import shlex
import subprocess

from pydantic import ValidationError

from retrievalgate.errors import AdapterError
from retrievalgate.models import AdapterRequest, AdapterResponse, Scenario


def run_adapter(command: str, scenario: Scenario, timeout: float) -> AdapterResponse:
    """Execute one retriever process for one scenario using JSON stdin/stdout."""

    argv = shlex.split(command)
    if not argv:
        raise AdapterError("adapter command cannot be empty")

    request = AdapterRequest(
        scenario_id=scenario.id,
        query=scenario.query,
        top_k=scenario.top_k,
    )

    try:
        completed = subprocess.run(
            argv,
            input=request.model_dump_json(),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise AdapterError(
            f"adapter timed out after {timeout:g}s for scenario '{scenario.id}'"
        ) from exc
    except OSError as exc:
        raise AdapterError(f"cannot execute adapter '{argv[0]}': {exc}") from exc

    if completed.returncode != 0:
        detail = completed.stderr.strip()
        suffix = f": {detail}" if detail else ""
        raise AdapterError(
            f"adapter exited with code {completed.returncode} for scenario '{scenario.id}'{suffix}"
        )

    try:
        return AdapterResponse.model_validate_json(completed.stdout)
    except ValidationError as exc:
        raise AdapterError(f"invalid adapter JSON for scenario '{scenario.id}': {exc}") from exc
