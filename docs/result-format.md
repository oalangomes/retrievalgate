# Structured result format v1

`retrievalgate run --output result.json` writes deterministic JSON suitable for CI artifacts and future baseline comparison.

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
