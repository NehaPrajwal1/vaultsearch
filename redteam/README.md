# Red-team and validation harness

VaultSearch includes prompt-injection fixtures, restricted-fact checks, citation analysis and permission-isolation experiments. The harness records source hashes, exact API responses, raw model calls and source exposure so findings can be traced to the evaluated source version.

## Default: bounded, model-free validation

Install requirements-test.txt and run `python redteam/release_check.py` from the project root. This runs lightweight tests, eight scripted acceptance cases, nine BM25 present/repeat/absent comparisons, loopback HTTP and real MCP stdio integration. Historical answer archives are replayed only when available locally. Every invocation creates a new private output directory.

See [measured evidence](../reports/release_review.md) and [the runbook](../RUN_SECURITY.md).

## What the harness checks

- Unauthorized evidence and configured restricted facts in raw synthesis and public responses.
- Forged or unapproved citation labels before and after production filtering.
- Whether the complete attack text actually reached a completed assessment or synthesis call.
- Repeated-baseline stability and response differences when restricted documents are removed.
- Correct failure handling for missing synthesis, malformed responses, service failure and incomplete execution.
- Expected application presentation over deliberately unsafe drafts and legitimate security quotations.

The agent uses the real in-process /api/ask handler; separate HTTP/MCP checks exercise transport authentication. The source corpus and attack fixtures are synthetic. Evaluation outputs and operator tokens are not publication artifacts.

## Interpreting results

Scripted tests validate deterministic behavior. Recorded-answer replay validates presentation, including known false positives, without rerunning the model. Historical automatic live red-team findings remain **INCONCLUSIVE**; unsafe draft findings are preserved in the local archives. No result is a blanket prompt-injection-resistance claim.

The live runner uses exit 0 for no detected failure in a completed scoped experiment, 1 for a detected failure, and 2 for incomplete/inconclusive execution. Unexposed attacks, model failures, missing synthesis and unstable paired baselines cannot be counted as successful defenses. String matching does not cover all semantic or encoded disclosure.

## Optional live work

Use a newly versioned Colab notebook/bundle from build_colab_bundle.py on suitable hardware. Keep automatic bounded preload, one-case execution, preserved raw outputs and review between cases. Do not merge checkpoints across source versions or weaken memory gates. The default local validator starts no model.
