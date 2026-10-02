#!/usr/bin/env python3
"""Tiny deterministic retriever used only by the retrievalgate quickstart."""

import json
import sys

request = json.load(sys.stdin)

results = [
    {"id": "src/services/medicationUsageHistoryService.js", "score": 0.91},
    {"id": "src/controllers/medicationUsageController.js", "score": 0.84},
    {"id": "tests/medicationUsageHistoryService.test.js", "score": 0.79},
]

selected = results[: request["top_k"]]
json.dump(
    {
        "protocol_version": request["protocol_version"],
        "results": selected,
        "telemetry": {
            "duration_ms": 1.0,
            "candidates_examined": 3,
            "candidates_returned": len(selected),
            "returned_chars": 0,
        },
    },
    sys.stdout,
)
