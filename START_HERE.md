# Start here: VaultSearch

Local portfolio demo: permission-aware keyword search over synthetic documents. AI generation is optional and experimental.

## Windows setup

From this folder with Python 3.11 or newer:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-search.txt
.\.venv\Scripts\python.exe run_demo.py --user ines
```

Open http://127.0.0.1:8000, paste the printed token into Demo token, connect, and search `paid time off`. Ctrl+C stops the server. Restart with `--user dmitri` for finance; reconnect with its fresh token. Use `--port 8001` if the default port is occupied.

Follow [the demo](docs/demo.md). Linux/macOS instructions are in [README](README.md).

## Validation

Install `requirements-test.txt`, ensure Node.js is available, and run `python redteam/release_check.py` with the virtual environment. This checks regression tests, scripted answers, BM25 corpus comparisons, real HTTP startup and MCP stdio integration. It does not load a model. Missing private historical archives are recorded as unavailable.

The source ZIP excludes Git history, operator tokens, raw reports, model weights, indexes and the virtual environment. Its hash manifest verifies the packaged files. Editing a file invalidates that snapshot's provenance. Install dependencies after extraction.

## Remaining scope

The local search demo is the supported delivery scope. The latest cached-embedding check exceeded its deadline; hybrid/reranker validation remains incomplete. Generated-answer usefulness and injection resistance remain unverified. Docker/WSL and named desktop MCP hosts require separate validation environments. See [release evidence](reports/release_review.md) and [container progress](docs/docker.md).
