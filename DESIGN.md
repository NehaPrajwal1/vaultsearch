# VaultSearch system design

## Data and identity

Synthetic Drive, Slack and ticket records normalize into documents and overlapping chunks. Every chunk inherits its document ACL. The corpus contains 513 chunks, 12 personas and 6 groups. The API binds a bearer token to an operator-configured identity; data requests cannot override that identity. The directory exposes intentionally org-public names and group memberships.

## Retrieval path

1. Expand the bound identity into user and group principals.
2. Select chunks whose ACL intersects those principals.
3. Compute BM25 statistics and scores using only the permitted corpus.
4. In full mode, reconstruct permitted FAISS vectors and calculate normalized dot-product scores.
5. Fuse sparse and dense rankings with reciprocal-rank fusion; optionally apply a cross-encoder to permitted candidates.
6. Recheck returned chunk permissions before evidence reaches synthesis. Stable chunk-ID tie breaks keep ordering deterministic.

Search-only startup reads the synthetic corpus directly and does not initialize embedding, reranking or generation models. The browser presents complete excerpts and document/chunk IDs independently of the answer pipeline.

## Answer orchestration

The planner proposes validated tool calls. A Toolbox is bound to one identity and exposes search, lookup_person and list_my_sources. An assessor may request up to two additional evidence-refinement rounds. Evidence is deduplicated, budgeted and permission-checked; synthesis receives the selected evidence. Citation labels are filtered to that evidence. The groundedness critic is advisory source agreement.

Flagged answers are replaced by a fixed application-written message without draft citations or model-written trace text. Evidence remains visible. Raw model responses are retained by evaluation recorders, not hidden fields in the public API. Unflagged answers remain untrusted; presentation checks are not a comprehensive safety detector.

## API and client boundary

FastAPI serves the UI and authenticated data routes. Search defaults to BM25; optional full-mode retrieval supports vector, hybrid, hybrid+rerank and explicit all-mode comparison. /api/users returns the bound identity only. The four MCP tools forward via HTTP through the same identity boundary; they accept no identity parameter.

Model requests have per-call timeouts and a scheduling budget. A transport failure stops subsequent model requests in that request. Explicit states distinguish disabled generation, no evidence, withheld output, unavailable synthesis and retrieval failure. Keyword search remains an independent path. The UI uses local assets, renders untrusted source text, and provides citation navigation.

## Red-team methodology

The harness invokes the actual API handler, records synthesis/assessment exposure and raw outputs, checks restricted-fact variants and citations, and compares present/repeat/absent corpus variants. Scripted tests include deliberately unsafe and broken model responses to exercise the harness and presentation policy. Live-model measurements, scripted acceptance and recorded-answer replay are separate evidence categories.

See [the methodology](redteam/README.md) and [measured results](reports/release_review.md).

## Optional infrastructure

Docker Compose supplies separate generation and cloud profiles. Terraform describes S3 source/artifact storage, SQS ingestion and DynamoDB audit storage using LocalStack endpoints. The optional audit mirror is best-effort; local audit logging remains independent. These are included implementation/configuration paths, while the release's measured runtime is native search-only.

## Engineering choices

ACL prefiltering keeps unauthorized text out of ranking candidates and model context. Permitted-corpus BM25 prevents hidden documents from changing visible term statistics. RRF combines ranks without calibrating unlike sparse/dense score scales. A deterministic verifier keeps authorization outside the model. Separate presentation and evaluation layers permit raw-output analysis while controlling the public response.
