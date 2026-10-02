# Command adapter protocol v1

`retrievalgate` executes an external command once per scenario and exchanges JSON
through standard streams.

## Request

```json
{
  "protocol_version": 1,
  "scenario_id": "medication-history",
  "query": "add medication usage history endpoint",
  "top_k": 20
}
```

Ground truth, absolute gates, and regression gates are deliberately not sent to the
retriever.

## Response

```json
{
  "protocol_version": 1,
  "results": [
    {"id": "src/foo.py", "score": 0.91},
    {"id": "src/bar.py", "score": 0.84}
  ],
  "telemetry": {
    "duration_ms": 18.4,
    "candidates_examined": 80,
    "candidates_returned": 20,
    "returned_chars": 9210
  }
}
```

Rules:

- array order defines rank;
- `id` is required and unique within a response;
- `score` is optional and never reorders results;
- optional `telemetry` is backend-neutral and does not affect quality scoring;
- telemetry fields must be non-negative when present;
- unknown fields are rejected;
- more than `top_k` results may be returned, but evaluation is bounded at `top_k`;
- invalid JSON, duplicate IDs, timeout, command-not-found, or non-zero exit is an
  infrastructure error and returns retrievalgate exit code `2`.

## Process and shell safety

The configured adapter string is tokenized into argv and executed with
`shell=False`. The query is transported only in JSON on stdin and is never
interpolated into a shell command.
