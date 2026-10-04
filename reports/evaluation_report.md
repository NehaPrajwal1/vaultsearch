# VaultSearch Evaluation Report

## Retrieval quality and latency

| Mode | NDCG@10 | MRR | p50 latency (ms) | p95 latency (ms) |
|---|---:|---:|---:|---:|
| bm25 | 0.783 | 0.708 | 3.9 | 8.1 |
| vector | 0.853 | 0.792 | 25.4 | 56.1 |
| hybrid | 0.843 | 0.750 | 23.9 | 29.4 |
| hybrid+rerank | 0.865 | 0.792 | 1723.6 | 1961.9 |

## Permission safety

- Adversarial retrieval attempts: 100
- Restricted-fact leaks: 0
- Unauthorized chunks returned: 0
- Permission leakage rate: 0.00%

All queries use retrieval-time ACL pre-filtering. The leakage metric also
searches returned chunk text for a distinctive restricted fact.
