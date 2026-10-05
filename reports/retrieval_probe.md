# Retrieval-only boundary measurements

Execution: real BM25, MiniLM embeddings, FAISS, cross-encoder, and /api/search; no LLM
UTC: 2026-10-05T06:04:37.437357+00:00

- Cases: 15
- Unauthorized chunks returned: 0
- Cases retrieving injection chunks: 3
- Stable paired response differences: 0 / 3

Retrieved injection chunks are NOT measured LLM exposure.
Any paired differences indicate changed non-timing fields in these cases;
they do not alone establish inference of any particular hidden topic.
The harness uses a server-bound test identity; this does not validate production authentication.
Full responses and changed fields are in retrieval_probe.json.
