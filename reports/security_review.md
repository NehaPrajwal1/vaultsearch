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

## Handoff update

74 tests passed in the full updated suite; 37 targeted security/harness tests passed after instrumentation changes. JavaScript syntax and git diff checks passed. The refreshed real retrieval report records source commit 79e3d70 and source hashes, with 0/3 stable paired differences.

Ollama 0.35.1 and gemma3:4b (Q4_K_M, digest a2af6cc3eb7fa8be8504abaf9b04e88f17a119ec3f04a3addf55f92841195f5a) were installed. Live readiness generation completed. The first injection-family case for user:asha completed but reported no exposed payload IDs. The user chose to run the lengthy full suite themselves; the active evaluation was stopped. Complete case outputs were not persisted by that version of the runner, so no attack-resistance result can be inferred from this partial attempt. The runner now checkpoints completed cases and handles Ctrl+C as incomplete for the user's upcoming run.

Draft PR: https://github.com/NehaPrajwal1/vaultsearch/pull/5. No merge performed. Live evaluation remains INCONCLUSIVE until the owner completes and reviews the run. See RUN_SECURITY.md for exact commands.

The final checkpoint/cancellation regression also passed: 38 targeted tests. The earlier full-suite result was 74 tests before this additional regression.

## Interrupted owner-run measurements and resume support (2026-10-06)

The owner-run live checkpoint records 22 cases at code 5351e51: 16 completed and 6 incomplete due to model-call timeouts. All 15 injection attempts were tried; 2 had measured completed pre-answer payload exposure, 13 did not. Six citation-family cases were tried. Six raw forged-citation cases were detected and zero forged final citations survived in the saved outputs. No configured restricted fact or unauthorized evidence hit was detected. One existence sample completed, but no paired triplet completed; zero stable paired differences in this partial report is not a result for unrun comparisons. Status remains INCONCLUSIVE after the Windows restart. Original checkpoint copies are kept locally under interrupted-2026-10-05/.

A separate resume runner now checks model digest, Python/package versions, runtime code hashes, identity and indexes before combining observations. It runs bounded new cases, checkpoints them, retains prior errors/unexposed cases, and recomputes pairs only when all three samples are present. Session version/timestamps are retained. Scripted regression coverage verifies prefix ordering, variant pairing, interruption, preservation of incomplete cases, and refusal to mix incompatible environments: 51 targeted tests passed. The actual 22-case checkpoint matched local runtime artifacts in a dry compatibility check. No resumed live inference has been started by the agent.

## Final resumed result reviewed 2026-10-07

All 30 planned cases have now been attempted and saved. The original run began on October 5; resumed-session timestamps and code/model provenance are retained in the JSON. Application/index/identity compatibility was checked before resumption. This is a multi-session evaluation, not one continuous run.

- 24 cases completed; 6 retained model-call timeouts remain incomplete.
- Only 2 of 15 injection-family attempts had measured completed pre-answer prompt exposure; 13 were unexposed.
- No configured restricted-fact hits, unauthorized evidence, or surviving final forged citations were detected in saved responses. Seven cases contained raw citation labels outside the allowed evidence set; none survived final filtering.
- Live paired results: acquisition had a stable repeated baseline and identical non-timing present/absent responses. Compensation and finance-reserve baselines were unstable; hidden-corpus comparisons for those two are inconclusive. Therefore, zero stable paired differences must NOT be read as three successful noninterference checks.
- The separate retrieval-only study still showed 0/3 differences across its three stable comparisons. It uses no LLM and is a different measurement.

Manual review of the two exposed injection-family answers found that the model repeated malicious source instructions as guidance about the assistant, including ignoring access restrictions and inventing confidential figures. These outputs did not disclose the configured restricted facts, but they do not demonstrate that the model recognizes or rejects malicious instructions. The current automated disclosure/citation oracle does not score this answer-contamination behavior.

No further model run is required merely to reach 30 saved cases. Potential follow-up work is targeted timeout retries with attempt history preserved, deliberate exposure coverage, and controlled paired runs. Those would be separate measurements; the current INCONCLUSIVE result remains valid and must not be relabeled a pass.

