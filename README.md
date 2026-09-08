# retrievalgate

> **Regression tests for retrieval.**

`retrievalgate` is a backend-agnostic CLI for turning retrieval expectations into deterministic, executable contracts. Point it at any retriever that can speak a tiny JSON stdin/stdout protocol, define what must be retrieved, and fail CI when retrieval quality regresses.

It does **not** implement retrieval. No embeddings, vector database, search engine, LLM judge, agent framework, or backend SDK is required.

## Why

Changes to BM25, dense retrieval, hybrid search, query expansion, chunking, indexing, filters, ranking thresholds, or `top_k` can improve one case and silently break another.

`retrievalgate` makes those expectations testable:

```text
retriever -> ranked result IDs -> metrics -> gates -> PASS / FAIL
```

A scenario is deliberately small:

```yaml
schema_version: 1
id: medication-history
query: add medication usage history endpoint
top_k: 3

ground_truth:
  relevant:
    - src/services/medicationUsageHistoryService.js
    - src/controllers/medicationUsageController.js
    - tests/medicationUsageHistoryService.test.js
  exhaustive: false

gates:
  recall:
    min: 1.0
  rr:
    min: 0.5
```

## Quickstart

> The project is currently pre-release. Install from a local clone until `v0.1.0` is published.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Validate the example contract:

```bash
retrievalgate validate examples/minimal/scenarios/
```

Run it against the example retriever:

```bash
retrievalgate run examples/minimal/scenarios/ \
  --adapter "python examples/minimal/retriever.py" \
  --output result.json
```

Expected shape:

```text
PASS medication-history | recall=1.000 rr=1.000 results=3
PASS 1/1 scenarios | MRR=1.000
```

A failed gate exits with code `1`, making the command directly usable in CI.

## Any retriever can be tested

For each scenario, `retrievalgate` starts the configured command and writes this JSON to its `stdin`:

```json
{
  "protocol_version": 1,
  "scenario_id": "medication-history",
  "query": "add medication usage history endpoint",
  "top_k": 3
}
```

The retriever writes ranked IDs to `stdout`:

```json
{
  "protocol_version": 1,
  "results": [
    {"id": "src/services/medicationUsageHistoryService.js", "score": 0.91},
    {"id": "src/controllers/medicationUsageController.js", "score": 0.84},
    {"id": "tests/medicationUsageHistoryService.test.js", "score": 0.79}
  ]
}
```

The result `id` is intentionally generic. It may be a file path, document ID, chunk ID, URI, database key, or any stable identifier meaningful to the system under test.

See [`docs/adapter-protocol.md`](docs/adapter-protocol.md) for the exact contract.

## Metrics in the v0.1 contract

Always available:

- **Recall** — fraction of declared relevant IDs found within `top_k`.
- **RR** — reciprocal rank of the first declared relevant ID.
- **MRR** — mean RR across the executed scenario suite.
- **Result count** — number of returned results considered, capped at `top_k`.
- **Expected ranks / missing IDs** — deterministic diagnostics for each declared relevant ID.

Only when `ground_truth.exhaustive: true`:

- **Precision** — relevant IDs found divided by `top_k`.
- **Unexpected count** — returned IDs within `top_k` that are not in the exhaustive relevant set.

That distinction is intentional. A partial ground truth cannot prove that an unlisted result is irrelevant, so `retrievalgate` refuses precision-like gates unless the scenario explicitly declares its judgments exhaustive.

## Gates

Gates use structured inclusive bounds rather than a custom expression language:

```yaml
gates:
  recall:
    min: 1.0
  rr:
    min: 0.25
  result_count:
    max: 20
```

For exhaustive judgments:

```yaml
ground_truth:
  relevant: [doc-a, doc-b]
  exhaustive: true

gates:
  precision:
    min: 0.20
  unexpected_count:
    max: 8
```

## CLI

```text
retrievalgate validate <scenario-or-directory>
retrievalgate run <scenario-or-directory> --adapter <command>
retrievalgate run <scenario-or-directory> --adapter <command> --output result.json
```

`retrievalgate compare baseline.json current.json` is tracked for the v0.1.0 MVP but intentionally lives in a separate implementation slice.

### Exit codes

| Code | Meaning |
|---:|---|
| `0` | All executed retrieval contracts passed |
| `1` | Execution succeeded, but at least one retrieval contract failed |
| `2` | Scenario, configuration, adapter, or protocol error |

## Design boundaries

`retrievalgate` is intentionally not:

- a retrieval engine;
- a RAG framework;
- an embeddings library;
- a vector database client;
- a search-engine-specific test harness;
- an LLM-as-a-judge framework;
- a benchmark publishing platform;
- an observability server.

Backend-specific integration belongs outside the core and talks to `retrievalgate` through the command adapter protocol.

The architectural boundary is recorded in [`ADR-0001`](docs/adr/0001-product-boundary.md).

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
mypy src tests
```

CI runs tests on Python 3.11, 3.12, and 3.13 plus lint and type checking.

## Documentation

- [Scenario schema](docs/scenario-schema.md)
- [Command adapter protocol](docs/adapter-protocol.md)
- [Structured result format](docs/result-format.md)
- [Product boundary ADR](docs/adr/0001-product-boundary.md)
- [Contributing](CONTRIBUTING.md)

## Status

`retrievalgate` is under active development toward `v0.1.0`. The public contracts are versioned from day one, but breaking changes are still possible before the first release.

## License

MIT
