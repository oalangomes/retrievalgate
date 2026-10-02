# Changelog

All notable changes to retrievalgate are documented in this file.

The project follows Semantic Versioning.

## [Unreleased]

### Added

- canonical cutoff metrics: Recall@K, Success@K, RR@K, MRR@K, binary nDCG@K,
  EvidenceDensity@K, and ResultCount@K;
- multiple evaluation cutoffs from one retriever invocation;
- optional backend-neutral operational telemetry for latency, candidate counts, and
  returned characters;
- suite-level metric and telemetry aggregation with contribution counts;
- explicit baseline-relative regression gates using max_drop/max_increase;
- structured console reporting split into quality, efficiency, and performance/cost;
- Markdown and JUnit XML report output.

### Compatibility

- v0.1 gate names remain accepted as top_k aliases;
- unchanged v0.1 scenarios retain their historical fingerprint when new optional
  fields are not configured;
- legacy structured-result metric fields remain present.

## [0.1.0] - 2026-09-07

### Added

- versioned YAML retrieval scenario contract;
- backend-agnostic command adapter protocol over JSON stdin/stdout;
- generic stable retrieval result IDs;
- explicit partial versus exhaustive ground-truth semantics;
- Recall, RR/MRR, result count, expected ranks, and missing-ID diagnostics;
- Precision and unexpected-count evaluation for exhaustive judgments;
- structured min/max gates with CI-friendly exit codes;
- deterministic scenario fingerprints and structured JSON results;
- `validate`, `run`, and `compare` CLI commands;
- strict baseline/current compatibility checks and deterministic comparison output;
- reproducible minimal example;
- Python 3.11, 3.12, and 3.13 CI;
- Ruff, mypy strict, package-build validation, and clean-wheel smoke tests;
- PyPI Trusted Publishing release workflow.
