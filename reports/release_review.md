# Release validation - October 8, 2026

This record accompanies the permission-aware synthetic search demo. The publication snapshot was checked with the bounded release validator in a clean worktree, without loading a model or changing the running local demo.

## Measured results

| Check | Result | Scope |
|---|---|---|
| Lightweight suite | **171 passed** | Application, ACL, identity, retrieval primitives, citations, presentation, harness and operator launcher |
| Scripted acceptance | **8 cases passed** | Real API/BM25; scripted drafts for facts, citations, absence, restrictions, onboarding, security quotations and attacks |
| Permission-isolation comparison | **9/9 stable; 0 differences** | Three identities × three queries; full non-timing BM25 responses compared across present/repeat/absent variants |
| HTTP integration | **Passed** | Startup/UI/search, 401 unauthenticated, 403 conflicting identity, 409 disabled generation, 422 invalid input |
| MCP integration | **Passed** | Real stdio client/server and loopback HTTP; four tools, identity binding, excerpts, errors and search recovery |
| JavaScript syntax and Git whitespace | **Passed** | Current publication source |

The publication runner reported private replay archives as unavailable, as intended for a new clone. Its results are separate from the earlier recorded-answer replay below. See [the curated machine-readable record](release_validation.json).

## Earlier evidence retained with provenance

- **8/8 recorded-answer presentation replays:** two four-case Colab rounds. Two ordinary drafts stayed visible; four access/export drafts were withheld; two legitimate security-analysis drafts were also withheld. The relevant API, orchestrator and presentation source hashes match the earlier validated implementation. This measures presentation over preserved output, not new model inference.
- **Clean dependency installation:** isolated requirements-search.txt installation, keyword retrieval and API imports passed without loading Torch, sentence-transformers or FAISS modules.
- **Browser checks:** source expansion, missing evidence, disabled generation, failed reconnect cleanup, keyboard citation navigation, withheld drafts, unavailable synthesis, independent search and recovery were exercised. Scripted answer checks made no model calls.
- **Historical retrieval benchmark:** hybrid plus cross-encoder recorded **NDCG@10 0.865** and **MRR 0.792**. The [mode-by-mode table](evaluation_report.md) retains the measured latency; these figures belong to the earlier source version.

## Interpretation and reproducibility

Run `python redteam/release_check.py` with requirements-test.txt and Node.js installed. Each run writes a fresh ignored local evaluation directory and terminates its temporary server. The six-test real-embedding module is excluded from this model-free command. Private replay archives are optional and are not distributed.

The tested MCP client is the Python stdio client; a named desktop-host check is separate. Native search-only startup is the measured deployment path; Docker/LocalStack configuration is included independently. Generated drafts and source instructions remain untrusted. Citation filtering checks permitted labels, and the critic measures source agreement. Historical automatic live red-team results remain **INCONCLUSIVE**; recorded unsafe outputs and false positives retain their original interpretation. None of these checks is a comprehensive injection-resistance or production-authentication claim.

Raw evaluation outputs, operator credentials, model/index files and local logs are excluded from this snapshot. Original historical archives are preserved in the development checkout. Existing repository history is retained; this publication does not rewrite prior commits.
