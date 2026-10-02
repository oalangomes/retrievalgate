# retrievalgate

> **Regression tests for retrieval.**

`retrievalgate` is a backend-agnostic CLI for turning retrieval expectations into
executable quality contracts. Point it at any retriever that speaks a tiny JSON
stdin/stdout protocol, define the evidence that must be retrieved, and fail CI when
quality drops below an absolute contract or an explicit baseline-relative regression
budget.

It does **not** implement retrieval. No embeddings, vector database, search engine,
LLM judge, agent framework, or backend SDK is required.

## Quickstart

```bash
pipx install retrievalgate
# or
uv tool install retrievalgate
```

Validate and run the bundled example:

```bash
retrievalgate validate examples/minimal/scenarios/

retrievalgate run examples/minimal/scenarios/ \
  --adapter "python examples/minimal/retriever.py" \
  --output result.json \
  --markdown report.md \
  --junit report.xml
```

The console report separates **quality**, **efficiency**, and optional
**performance/cost** observations so a regression is understandable without opening
the JSON artifact.

## Scenario

```yaml
schema_version: 1
id: medication-history
query: add medication usage history endpoint
top_k: 20

evaluation:
  cutoffs: [1, 5, 10, 20]

ground_truth:
  relevant:
    - src/services/medicationUsageHistoryService.js
    - src/controllers/medicationUsageController.js
  exhaustive: false

gates:
  Success@5:
    min: 1.0
  Recall@20:
    min: 1.0
  nDCG@20:
    min: 0.8

regression_gates:
  Recall@20:
    max_drop: 0.05
  nDCG@20:
    max_drop: 0.10
```

Legacy v0.1 gate names such as `recall`, `rr`, `result_count`, `precision`,
and `unexpected_count` remain accepted and resolve to the scenario's `top_k`
cutoff.

## Metrics

One ranked result list can be evaluated at multiple cutoffs without invoking the
retriever again.

Always available:

- `Recall@K`
- `Success@K`
- `RR@K`
- suite-level `MRR@K`
- binary `nDCG@K`
- `EvidenceDensity@K` — known relevant results / returned results
- `ResultCount@K`
- expected ranks and missing IDs

With `ground_truth.exhaustive: true`:

- `Precision@K`
- `UnexpectedCount@K`

`EvidenceDensity@K` is diagnostic when ground truth is partial. It measures density
of **known** relevant evidence and must not be interpreted as exhaustive precision.

## Optional operational telemetry

Adapters may attach backend-neutral observations:

```json
{
  "protocol_version": 1,
  "results": [
    {"id": "src/foo.py", "score": 0.91}
  ],
  "telemetry": {
    "duration_ms": 18.4,
    "candidates_examined": 80,
    "candidates_returned": 20,
    "returned_chars": 9210
  }
}
```

These values are reported separately from quality metrics. A single retrievalgate run
does not fabricate p50/p95/p99; repeated-run percentile methodology belongs to the
benchmark producing those observations.

## Regression comparison

```bash
retrievalgate compare baseline.json current.json
```

Comparison remains strict:

- scenario sets must match;
- scenario fingerprints must match;
- metric availability must match;
- expected IDs must match.

It reports metric deltas, lost/recovered expected IDs, rank movement, PASS/FAIL
transitions, and configured regression gates. A comparison fails only for a current
absolute contract failure or an **explicitly configured** regression budget.

## Reports

`retrievalgate run` supports:

- console — human-readable local/CI report;
- canonical JSON via `--output`;
- Markdown via `--markdown`;
- JUnit XML via `--junit`.

The JSON artifact remains deterministic and suitable for later comparison.

## Adapter protocol

For each scenario, retrievalgate sends:

```json
{
  "protocol_version": 1,
  "scenario_id": "medication-history",
  "query": "add medication usage history endpoint",
  "top_k": 20
}
```

The retriever returns ranked stable IDs:

```json
{
  "protocol_version": 1,
  "results": [
    {"id": "src/foo.py", "score": 0.91},
    {"id": "src/bar.py", "score": 0.84}
  ]
}
```

Ground truth and gates are never sent to the retriever.

## Exit codes

| Code | Meaning |
|---:|---|
| `0` | Current absolute contracts and configured regression gates pass |
| `1` | A current contract or explicit regression gate fails |
| `2` | Scenario, adapter, protocol, configuration, or comparison error |

## Design boundary

`retrievalgate` is intentionally not a retriever, benchmark runner, embeddings
library, search-engine client, LLM judge, observability server, or dashboard. Backend
integration stays outside the core and talks through the command adapter protocol.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
mypy src tests
```

CI runs Python 3.11, 3.12, and 3.13, Ruff, mypy strict, package validation, and a
clean-wheel quickstart.

## Documentation

- [Scenario schema](docs/scenario-schema.md)
- [Command adapter protocol](docs/adapter-protocol.md)
- [Structured result format](docs/result-format.md)
- [Product boundary ADR](docs/adr/0001-product-boundary.md)
- [Release process](docs/releasing.md)
- [Contributing](CONTRIBUTING.md)

## License

MIT
