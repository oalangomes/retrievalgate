# ADR-0001: Keep retrieval outside retrievalgate

- Status: Accepted
- Date: 2026-09-07

## Context

The project exists to detect regressions in retrieval and context acquisition. The systems under test may use lexical search, dense retrieval, hybrid search, graph traversal, reranking, proprietary APIs, or simple local scripts.

Embedding backend knowledge into the core would turn a regression-test runner into another retrieval framework and would make evaluation behavior depend on implementation-specific integrations.

## Decision

`retrievalgate` will treat retrieval as an external system.

The v0.1 integration boundary is a small versioned command protocol using JSON over stdin/stdout. Public scenario contracts use generic stable result IDs. Ground truth, metrics, gates, and result serialization stay inside retrievalgate; search, indexing, embeddings, query planning, and reranking stay outside.

## Consequences

Positive:

- backend-agnostic core;
- easy integration with local scripts and existing systems;
- retrievers can evolve independently;
- no Solr/OpenSearch/Qdrant/agent-framework dependency;
- deterministic tests do not require an LLM or network service.

Trade-offs:

- starting one process per scenario has overhead;
- backend-specific ergonomics live in external adapters;
- richer streaming/batch protocols are deferred until real usage proves a need.

## Rejected for v0.1

- native backend SDK adapters;
- plugin registry;
- long-lived adapter daemon;
- MCP integration;
- retrieval or indexing implementation inside the project.
