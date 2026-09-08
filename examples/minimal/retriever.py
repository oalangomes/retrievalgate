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

json.dump(
    {
        "protocol_version": request["protocol_version"],
        "results": results[: request["top_k"]],
    },
    sys.stdout,
)
