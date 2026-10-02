# Structured result format v1

`retrievalgate run --output result.json` writes deterministic JSON for CI artifacts
and baseline comparison.

The schema remains version `1`. v0.1 fields are retained while canonical `@K`
measures and optional telemetry extend the result.

## Scenario metrics

Each scenario keeps the legacy top-k summary fields:

```json
{
  "recall": 1.0,
  "rr": 1.0,
  "result_count": 3,
  "precision": null,
  "unexpected_count": null
}
```

and adds canonical measures:

```json
{
  "measures": {
    "EvidenceDensity@1": 1.0,
    "EvidenceDensity@3": 1.0,
    "RR@1": 1.0,
    "RR@3": 1.0,
    "Recall@1": 0.3333333333333333,
    "Recall@3": 1.0,
    "ResultCount@1": 1.0,
    "ResultCount@3": 3.0,
    "Success@1": 1.0,
    "Success@3": 1.0,
    "nDCG@1": 1.0,
    "nDCG@3": 1.0
  }
}
```

Optional adapter telemetry is preserved under the scenario metric object and aggregated
separately at suite level.

## Suite aggregation

The suite summary includes:

- pass/fail counts;
- legacy `mrr`;
- mean canonical metrics;
- `MRR@K` derived from scenario `RR@K`;
- a count of how many scenarios contributed to each aggregate;
- mean operational telemetry and contribution counts when telemetry exists.

This prevents a metric evaluated on only a subset of scenarios from silently looking
like a full-suite aggregate.

## Determinism

Timestamps, hostnames, local paths, and other run-specific metadata remain excluded.
Given the same normalized scenarios and ranked retriever results, canonical JSON is
stable.

## Comparison

`retrievalgate compare baseline.json current.json` requires identical scenario sets
and matching scenario fingerprints. It reports:

- suite and scenario metric deltas;
- missing and recovered expected IDs;
- expected-result rank movement;
- absolute PASS/FAIL transitions;
- explicit regression-gate evaluation.

No implicit relative threshold exists. If a scenario does not configure a regression
gate, a numeric delta is diagnostic only.
