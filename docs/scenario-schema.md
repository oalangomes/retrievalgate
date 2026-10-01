# Scenario schema v1

A scenario describes one retrieval expectation. Scenario files remain on
`schema_version: 1`; the evaluation/reporting additions are backward-compatible
extensions.

## Example

```yaml
schema_version: 1
id: find-auth-handler
query: where is authentication handled?
top_k: 20

evaluation:
  cutoffs: [1, 5, 10, 20]

ground_truth:
  relevant:
    - src/auth/handler.py
  exhaustive: false

gates:
  Success@5:
    min: 1.0
  Recall@20:
    min: 1.0

regression_gates:
  Recall@20:
    max_drop: 0.05
```

## Cutoffs

`top_k` is the maximum ranked result budget requested from the retriever.
`evaluation.cutoffs` optionally evaluates that same result list at smaller cutoffs.
Every cutoff must be positive and no larger than `top_k`. `top_k` is always
evaluated even when omitted from `evaluation.cutoffs`.

## Ground truth

`ground_truth.relevant` is a non-empty set of stable known-relevant result IDs.

`ground_truth.exhaustive: false` means unlisted results are unjudged, not proven
irrelevant. `Precision@K` and `UnexpectedCount@K` are therefore unavailable.

`ground_truth.exhaustive: true` declares the relevant set complete for the evaluated
scope and enables those exhaustive-only measures.

## Canonical metrics

Supported scenario-level metric families are:

- `Recall@K`
- `Success@K`
- `RR@K`
- `nDCG@K` using binary relevance
- `EvidenceDensity@K`
- `ResultCount@K`
- `Precision@K` — exhaustive only
- `UnexpectedCount@K` — exhaustive only

Suite aggregation converts `RR@K` to `MRR@K`.

Legacy gate names from v0.1 resolve to `top_k`:

- `recall` -> `Recall@top_k`
- `rr` -> `RR@top_k`
- `result_count` -> `ResultCount@top_k`
- `precision` -> `Precision@top_k`
- `unexpected_count` -> `UnexpectedCount@top_k`

## Absolute gates

```yaml
gates:
  Recall@20:
    min: 0.90
  ResultCount@20:
    max: 20
```

Bounds are inclusive.

## Regression gates

Regression gates are evaluated only by `retrievalgate compare`.

```yaml
regression_gates:
  Recall@20:
    max_drop: 0.05
  ResultCount@20:
    max_increase: 5
```

`max_drop` limits how far current may fall below baseline. `max_increase` limits
how far current may rise above baseline. Neither direction is assumed to be globally
good or bad; the scenario author chooses the relevant bound.

## Fingerprints

Each normalized scenario is canonically serialized and hashed with SHA-256. New
optional fields are omitted from the fingerprint while left at their defaults so an
unchanged v0.1 scenario preserves its historical fingerprint.
