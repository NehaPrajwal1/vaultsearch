# Case study: VaultSearch

## Project overview

VaultSearch explores a concrete retrieval problem: a shared knowledge base contains documents with different access permissions, while users expect one search interface. The demonstration uses 225 synthetic documents, 513 chunks and 12 personas to make those permission differences visible and reproducible.

The supported product is a local keyword search application. Optional generated answers provide a separate experiment in evidence selection, citations and prompt-injection handling.

## The engineering problem

Filtering a final answer is too late to define a retrieval boundary. Restricted chunks should not enter the permitted search results, and a request field should not let a caller change identity. Even ranking statistics can depend on inaccessible documents: global BM25 statistics may change when hidden documents are added.

VaultSearch addresses these specific issues by binding an identity at the API, computing its permitted chunk set, and computing BM25 scores from that permitted corpus. Stable chunk-ID tie breaks make comparisons reproducible.

## Implementation and tradeoffs

### Bind identity before processing requests

An operator starts the demo for one known persona with a fresh bearer token. The API validates that token and rejects conflicting legacy identity claims. MCP forwards the same token and exposes no identity-selection parameter.

This is a deliberately small identity mechanism for a local demonstration. It does not implement enterprise sign-in, token expiry or a multi-user identity provider.

### Make evidence inspectable

The default UI returns source excerpts and stable identifiers. It handles empty results and authentication errors visibly. Reviewers can compare a general-staff query with a finance query and inspect the permitted text directly.

Keyword retrieval reduces runtime dependencies and makes the demonstration practical on an 8 GB laptop. Semantic retrieval is retained as an optional path, with its current validation gap stated.

### Separate model behavior from permission enforcement

The optional answer pipeline selects permitted evidence and filters citation labels to that selection. A model critic checks source agreement. Agreement with a malicious source still does not establish safe advice.

Recorded model experiments produced unsafe instruction repetition, including a missed passive credential-export warning. The application now replaces flagged drafts with a fixed message and keeps permitted evidence available. A lexical detector remains incomplete: it can miss paraphrases and withhold benign quotations. These limitations are part of the result, rather than hidden behind a successful unit-test count.

### Keep evaluation reproducible

The release validator combines regression tests, scripted API cases, corpus comparisons, loopback HTTP and real MCP stdio integration. It records source hashes and creates separate output directories. Packaged source has a verified hash manifest and can be checked without Git history or private raw reports.

Scripted outputs test application behavior. Recorded model outputs support historical findings. Neither is presented as fresh live-model evidence.

## What was measured

The extracted-package run on October 22, 2026 passed 176 lightweight tests, eight scripted acceptance cases, nine stable BM25 present/repeat/absent corpus comparisons with zero non-timing differences, and real HTTP/MCP integration checks.

The corpus comparisons hold the permitted documents constant while removing hidden documents. Their scope is those queries and identities; they do not measure timing leakage or establish general noninterference.

The tests ran on Windows using the existing dependency environment. This was not a new clean installation or a remote CI run. The latest bounded cached-embedding check exceeded its 90-second deadline. Docker and WSL were unavailable.

## Demonstrate it in three minutes

1. **Problem:** explain why document access must shape retrieval.
2. **Evidence:** search “paid time off” as Ines and open an excerpt.
3. **Boundary:** query the infrastructure budget, restart as Dmitri, and compare permitted evidence.
4. **Engineering:** show the permission filter and permitted-corpus BM25 implementation.
5. **Results:** explain the nine corpus comparisons and distinguish them from live-model quality.
6. **Tradeoff:** explain why the useful default works without a model and what remains experimental.

The [demo guide](demo.md) includes the exact operator flow.

## Portfolio and interview copy

**One-sentence summary**

Built a local permission-aware search demo with server-bound identities, inspectable evidence and MCP integration, backed by reproducible API and retrieval checks.

**Evidence-based project bullets**

- Implemented authenticated demo requests and permission filtering over a synthetic 225-document corpus, with BM25 scoring restricted to permitted chunks.
- Validated the local search path with 176 lightweight tests, eight scripted acceptance cases and nine stable hidden-corpus comparisons with zero non-timing response differences.
- Integrated MCP tools with the same API identity boundary and documented generated-answer failure modes, including detector evasions and false positives.

These describe the demonstrated implementation. Do not substitute claims about production adoption, real customer data, latency improvements or comprehensive injection resistance.

## Next engineering milestones

Complete Linux/container validation; measure current-source hybrid/reranker behavior; run bounded live-model cases with matching provenance; and select a production identity provider only if the project scope expands beyond the local demo.
