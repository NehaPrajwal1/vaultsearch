# Historical retrieval benchmark

These figures are preserved from the earlier retrieval evaluation. They are not current-source release measurements or end-to-end answer latency.

| Mode | NDCG@10 | MRR | p50 latency (ms) | p95 latency (ms) |
|---|---:|---:|---:|---:|
| bm25 | 0.783 | 0.708 | 3.9 | 8.1 |
| vector | 0.853 | 0.792 | 25.4 | 56.1 |
| hybrid | 0.843 | 0.750 | 23.9 | 29.4 |
| hybrid+rerank | 0.865 | 0.792 | 1723.6 | 1961.9 |

Current scoped validation is recorded in [release_review.md](release_review.md).
