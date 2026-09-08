# Contributing

Thanks for helping improve retrievalgate.

## Product boundary first

Before adding a feature, ask:

1. Does this test retrieval, or start implementing retrieval?
2. Does it make regressions easier to detect?
3. Can the need be handled by an external adapter instead?
4. Does it preserve deterministic behavior without requiring an LLM?
5. Is the added complexity justified by a concrete use case?

Backend clients, embeddings, indexing, reranking, agent behavior, dashboards, servers, and benchmark publishing do not belong in the core without a separately discussed architectural decision.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check .
mypy src tests
```

Changes to a public contract must update its corresponding documentation and include focused tests.
