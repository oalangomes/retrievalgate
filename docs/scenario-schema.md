# Scenario schema v1

A scenario describes one retrieval expectation. Scenario files are YAML and use `schema_version: 1`.

## Minimal example

```yaml
schema_version: 1
id: find-auth-handler
query: where is authentication handled?
top_k: 10

ground_truth:
  relevant:
    - src/auth/handler.py
  exhaustive: false

gates:
  recall:
    min: 1.0
```

## Fields

### `schema_version`

Required. Must be `1` for the current contract.

### `id`

Required non-empty string. IDs must be unique across all scenarios loaded in one command.

### `query`

Required non-empty string passed to the retriever.

### `top_k`

Positive integer. Defaults to `20`. Evaluation considers at most the first `top_k` adapter results.

### `ground_truth.relevant`

Required non-empty list of unique stable result IDs expected to be relevant.

The ID is backend-agnostic. It can represent a file, document, chunk, URI, database key, or another stable retrieval identity.

### `ground_truth.exhaustive`

Boolean, default `false`.

- `false`: the declared IDs are known-relevant examples, but unlisted results are not automatically considered irrelevant.
- `true`: the scenario asserts that the declared set is the complete relevant set for the evaluated scope.

`precision` and `unexpected_count` gates are rejected unless this value is `true`.

### `gates`

Optional mapping from metric names to inclusive `min` and/or `max` bounds.

Supported v0.1 scenario metrics:

- `recall`
- `rr`
- `result_count`
- `precision` — exhaustive judgments only
- `unexpected_count` — exhaustive judgments only

Example:

```yaml
gates:
  recall:
    min: 1.0
  rr:
    min: 0.25
  result_count:
    max: 20
```

Unknown fields and unknown gate metrics are rejected rather than ignored.

## Fingerprints

Each normalized scenario is serialized canonically and hashed with SHA-256. Structured results include this fingerprint so future baseline comparison can reject comparisons produced from materially different contracts.
