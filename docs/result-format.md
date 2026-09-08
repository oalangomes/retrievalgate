# Structured result format v1

`retrievalgate run --output result.json` writes deterministic JSON suitable for CI artifacts and baseline comparison.

The output intentionally omits timestamps, hostnames, environment paths, and other run-specific metadata that would make identical evaluations serialize differently.

## Shape

```json
{
  "schema_version": 1,
  "tool": {
    "name": "retrievalgate",
    "version": "0.1.0.dev0"
  },
  "status": "pass",
  "summary": {
    "scenarios": 1,
    "passed": 1,
    "failed": 0,
    "mrr": 1.0
  },
  "scenarios": [
    {
      "id": "medication-history",
      "scenario_fingerprint": "sha256:...",
      "status": "pass",
      "top_k": 3,
      "metrics": {
        "recall": 1.0,
        "rr": 1.0,
        "result_count": 3,
        "precision": null,
        "unexpected_count": null
      },
      "expected": {
        "total": 3,
        "found": 3,
        "missing": [],
        "ranks": {
          "src/services/medicationUsageHistoryService.js": 1,
          "src/controllers/medicationUsageController.js": 2,
          "tests/medicationUsageHistoryService.test.js": 3
        }
      },
      "gates": []
    }
  ]
}
```

## Determinism

For the same normalized scenarios and the same ordered retriever results, serialized output is stable. Scenario input ordering is deterministic, and each scenario carries a SHA-256 fingerprint of its normalized contract.

## Safe baseline comparison

`retrievalgate compare baseline.json current.json` only compares result suites when their scenario sets match and each same-ID scenario has the same fingerprint.

A matching fingerprint means the query, `top_k`, ground truth, exhaustiveness declaration, and gates came from the same normalized scenario contract. This prevents a changed test definition from being mistaken for a retriever regression.

Comparison also verifies that metric availability and expected result IDs remain compatible.

The command reports:

- metric deltas;
- expected IDs missing from current results;
- expected IDs recovered in current results;
- rank changes for expected IDs present in both runs;
- PASS/FAIL transitions;
- suite MRR delta.

There are no implicit relative regression thresholds in v0.1. Exit code `1` reflects the current result's existing absolute gates; comparison/configuration errors return `2`.
