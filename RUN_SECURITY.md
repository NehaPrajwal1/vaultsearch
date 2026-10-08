# Reproduce the release checks

Use the project virtual environment with requirements-test.txt installed, then run:

```powershell
.\.venv\Scripts\python.exe redteam/release_check.py
```

Node.js supplies the JavaScript syntax check. The runner has bounded subprocess timeouts and creates a fresh ignored .local-evaluations/release-check-* directory. It exercises lightweight tests, scripted API acceptance, BM25 permission-isolation triplets, temporary loopback HTTP and real MCP stdio-to-HTTP integration. No live model, embedder or reranker is loaded. Temporary servers are terminated afterward.

Inspect validation.json, acceptance.json and retrieval-pairs.json. offline-replay.json is produced only when preserved private Colab archives are present; a new clone reports their absence explicitly. Historical raw reports are optional too. The curated [release record](reports/release_review.md) distinguishes fresh-clone checks from earlier private replay results.

## Optional live experiments

The historical automatic live results remain INCONCLUSIVE. Current-source model work needs a new matching notebook/bundle from `python redteam/build_colab_bundle.py`; creating a bundle neither uploads nor runs it. Review its inventory and scripted checks first.

Run on suitable hardware with automatic bounded preload and one case at a time. Start with the benign case, then inspect completion, exposure, raw answer, citations, presentation and provenance before proceeding. Preserve downloaded raw outputs and keep changed-source results separate from old checkpoints. Never weaken memory gates or run the full live suite on an 8 GB laptop.

See [red-team methodology](redteam/README.md) for exposure rules, outcome semantics and evidence categories.
