# Command adapter protocol v1

`retrievalgate` does not know how retrieval is implemented. It executes an external command once per scenario and exchanges JSON through standard streams.

## Process model

For each scenario:

1. `retrievalgate` starts the configured command with `shell=False` semantics.
2. One JSON request is written to `stdin`.
3. The retriever writes one JSON response to `stdout`.
4. Retriever logs may be written to `stderr`.
5. Exit code `0` means the protocol response is available.
6. Any non-zero exit code is an adapter execution error.

There is no daemon, socket, streaming session, or persistent worker protocol in v0.1.

## Request

```json
{
  "protocol_version": 1,
  "scenario_id": "medication-history",
  "query": "add medication usage history endpoint",
  "top_k": 20
}
```

Fields:

- `protocol_version`: always `1`.
- `scenario_id`: stable scenario identifier for correlation only.
- `query`: retrieval query.
- `top_k`: requested result cutoff.

Ground truth and gates are deliberately **not** sent to the retriever. This avoids leaking expected answers into the system under test.

## Response

```json
{
  "protocol_version": 1,
  "results": [
    {"id": "src/foo.py", "score": 0.91},
    {"id": "src/bar.py", "score": 0.84}
  ]
}
```

Rules:

- array order defines rank;
- `id` is required and must be unique within the response;
- `score` is optional and is not used to reorder results;
- unknown response fields are rejected;
- more than `top_k` results may be returned, but evaluation considers only the first `top_k`;
- invalid JSON, duplicate IDs, timeout, command-not-found, or non-zero process exit produces retrievalgate exit code `2`.

## Security and shell behavior

The adapter option is tokenized as a command line and executed without a shell. The query itself is transported only inside JSON on `stdin`; it is never interpolated into a shell command.
