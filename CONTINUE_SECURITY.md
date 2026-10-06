# Saved VaultSearch continuation checklist

Continue from merged GitHub main at https://github.com/NehaPrajwal1/vaultsearch and the existing local project:
`C:\Users\Neha Prajwal\.codex\visualizations\2026\10\04\01a10719-4dcb-7f90-b4d6-11bfbbc9e41f\vaultsearch`.
Do not start from the empty `Documents\ChatGPT\vault search` folder.

1. Inspect main, the local checkout, tests, and reports before changing anything. Check for an existing security branch/draft PR before duplicating its work.
2. Complete a live Ollama red-team evaluation with the configured model. Separate completed malicious-prompt exposure from unexposed cases, errors, and fallbacks. Record model and code version. Unavailable or incomplete is never a pass.
3. Investigate hidden-corpus leaks. The original paired test differed in 3/3 comparisons. Inspect counts, search scores, rankings, and traces; fix in-scope disclosures and rerun.
4. Bind requests to a trusted test identity for this local demo. Review MCP too. If production becomes the goal, ask the owner which authentication provider to use first.
5. Add regression tests, run relevant suites, and update README/reports with measured results and remaining limits.
6. Prepare changes for review on a human-readable branch without the codex/ prefix. Preserve accurate commit attribution; open a draft PR if possible. Do not merge without the owner's instruction.

Scope: portfolio demo unless explicitly changed. Explain fixes, measured tests, and unverified claims.

## Work begun 2026-10-05

Started from merged main `7622b04` on `security/trusted-demo-identity` in the existing checkout. See `reports/security_review.md` and the current reports for outcomes. The user also authorized installation of Ollama and the configured `gemma3:4b` model. Preserve work already on this branch when resuming; do not reset it to main.

The owner will run the full live suite themselves. Ollama and gemma3:4b are installed; the agent run was stopped at their request. Use RUN_SECURITY.md. Review the resulting reports, update draft PR #5, and do not merge.

Update 2026-10-06: the owner-run evaluation saved 22/30 cases before a Windows crash; 16 completed, 6 timed out, 2/15 injection-family attempts exposed payloads, and no paired triplet completed. Memory Diagnostic reported no errors; crash cause remains undiagnosed. The new resume_redteam.py supports one-case batches with model/runtime/index compatibility checks. See RUN_SECURITY.md; do not restart the original full suite or treat partial results as a pass.
