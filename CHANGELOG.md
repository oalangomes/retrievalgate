# Changelog

All notable changes to retrievalgate are documented in this file.

The project follows Semantic Versioning.

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
