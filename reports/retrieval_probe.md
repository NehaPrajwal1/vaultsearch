# Retrieval-only boundary measurements

Execution: real BM25, MiniLM embeddings, FAISS, cross-encoder, and /api/search; no LLM
UTC: 2026-10-04T13:51:55.804919+00:00

- Cases: 15
- Unauthorized chunks returned: 0
- Cases retrieving injection chunks: 3
- Stable paired response differences: 3 / 3

Retrieved injection chunks are NOT measured LLM exposure.
Paired differences disprove identical search responses in these cases;
they do not alone establish inference of any particular hidden topic.
The persona API is unauthenticated. These results do not validate a production boundary.
Full responses and changed fields are in retrieval_probe.json.
