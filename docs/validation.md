# Reproducing the evidence

Use Python 3.12, the project virtual environment and Node.js. Install `requirements-test.txt`, then run:

```powershell
.\.venv\Scripts\python.exe redteam/release_check.py
```

The runner exercises the lightweight regression suite, eight scripted cases, nine keyword corpus comparisons, actual loopback HTTP and real MCP stdio forwarding. It does not load the embedding integration module or invoke an answer model. Private historical archives are replayed only when present.

A successful run writes `LOCAL_CHECKS_PASSED` and a unique `.local-evaluations/release-check-*/validation.json`. Inspect each check's scope; unavailable historical replay and inapplicable Git checks in a ZIP are explicitly labeled.

## Continuous integration

The prepared workflow runs this validator on Windows and Ubuntu with Python 3.12 and Node.js 24. It installs only test/search dependencies and uses read-only repository permissions. No model, cloud credential or deployment is needed. The merged version has passed on both runners: [GitHub Actions evidence](https://github.com/NehaPrajwal1/vaultsearch/actions/runs/40180282456).

Action configuration follows the official [checkout](https://github.com/actions/checkout), [setup-python](https://github.com/actions/setup-python) and [setup-node](https://github.com/actions/setup-node) documentation.

## Produce a local portfolio ZIP

```powershell
.\.venv\Scripts\python.exe redteam/build_release.py
```

The builder selects an explicit list of source files, normalizes text line endings, annotates omitted historical document links, writes a hash manifest, extracts the ZIP, and runs the validator against that extracted source. It excludes Git history, virtual environments, operator tokens, raw local evaluation output and model artifacts. It performs no upload.

The extracted validation uses the invoking Python environment. A pass therefore confirms source-package behavior, not a newly installed dependency environment. Changing a manifested file invalidates its recorded provenance.

## Optional runtime checks

- Docker: see [container setup](docker.md). A missing CLI/engine is blocked, not passed.
- Live models: follow [the bounded runbook](../RUN_SECURITY.md) using a fresh matching bundle. Do not merge old checkpoints with changed source.
- Historical results: read their recorded date and source version. The original model evaluation remains inconclusive.
