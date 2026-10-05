# Security review — 2026-10-05

## Starting state

Existing checkout was clean on chore/ignore-local-model-cache. Fetched merged GitHub main at `7622b04` and created `security/trusted-demo-identity`. The original 53-test suite passed before editing. Previous red-team report was inconclusive because Ollama was unavailable. Historical reports are preserved under `baseline-2026-10-04/`.

## Measured hidden-corpus leak

All three old search comparisons exposed a changing total_chunks value. Additional differences were:

- Acquisition question: two hybrid result scores.
- Compensation question: hybrid scores and positions 1/2 document IDs, titles, and text.
- Finance reserve question: BM25 position 5 and hybrid positions 0/1 changed documents; multiple hybrid scores changed.

Exact paths are recorded in baseline_field_differences.json. Filtering BM25 result IDs was insufficient: its IDF and length-normalization statistics still depended on hidden documents. Global counts were also returned in search, users, tool traces, and source-list payloads.

The fix recomputes BM25 on permitted documents only, scores only permitted vectors, and uses stable chunk-ID tie breaks. Public outputs omit global counts and verification-rejection IDs. Users can see only their own visibility count; org-public directory metadata remains intentionally visible.

The real MiniLM/FAISS/cross-encoder retrieval probe on this machine returned zero unauthorized chunks across 15 cases and zero stable paired differences across three questions, down from 3/3. Counts, rankings, scores, titles, and text were compared in all four search modes; timing fields were excluded. Retrieving injection documents in 3/15 cases is not model prompt exposure.

## Identity boundary

One server-configured test identity and a random bearer token are required at startup. Data routes reject absent/invalid tokens and conflicting user_id claims. The browser keeps the token only in memory. MCP sends the same credential, has no identity tool argument, and obtains whoami from the API. Operator configuration, bearer-token possession, local files, audit logs, and ACL source data are trusted.

This does not provide multi-user accounts, SSO, token expiry/revocation infrastructure, or production readiness. Switching personas requires an operator restart and a fresh token. No provider was chosen.

## Validation and live model

The current tests and live Ollama run are recorded in the final review update below. Ollama installation was explicitly authorized by the user; version 0.35.1 was installed and gemma3:4b download started. A completed installation is not a completed red-team evaluation. Consult redteam_report.md and its JSON before interpreting live outcomes.

## Remaining limits

Three paired questions are a small deterministic search check, not a proof of indistinguishability. Ask-route model behavior and traces require the separate live run. Request timings still depend on corpus traversal and workload and are outside this fix; no timing resistance is claimed. Secret oracles cover listed strings/normalized variants, not every paraphrase or encoded leak. Valid citations do not prove groundedness. The critic is advisory. Historical quality/latency and scaling measurements have not been rerun for the new per-request permitted-corpus scoring. Docker/LocalStack and a real external MCP host were not exercised in this review; MCP HTTP forwarding is covered by regression tests.
