# VaultSearch

A local portfolio demo of permission-aware retrieval and cited answers over a synthetic company corpus. The API binds requests to one operator-configured test identity. This is not production authentication or a guarantee that a language model cannot disclose or invent information.

## Current security work

- API data routes require a bearer token. The server chooses the identity; a caller-supplied `user_id` can only match it, otherwise the API returns 403.
- BM25 statistics use only permitted documents. Vector scores use permitted embeddings with stable chunk-ID tie breaking. Hybrid and reranked results inherit that boundary.
- Responses no longer expose global corpus totals, other users' visibility counts, or rejected chunk identifiers. Operator audit logs remain privileged.
- MCP authenticates with the same token and obtains its identity from the API.
- The browser token stays in page memory and is cleared on reload. The sidebar shows the bound identity.

See [security review](reports/security_review.md), [retrieval measurements](reports/retrieval_probe.md), and [live red-team status](reports/redteam_report.md). Historical measurements are preserved in `reports/baseline-2026-10-04/` and must not be interpreted as current results.

## Local Windows setup

Use Python 3.11+, Git, and [Ollama](https://ollama.com/download/windows). The existing project already has a virtual environment and indexes; do not overwrite those just to resume work.

```powershell
# New clone only:
git clone https://github.com/NehaPrajwal1/vaultsearch.git
cd vaultsearch
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

ollama pull gemma3:4b
# If the Ollama background app is not running, start `ollama serve` separately.

# New corpus/index only:
.\.venv\Scripts\python.exe ingestion/generate_data.py
.\.venv\Scripts\python.exe ingestion/ingest.py
.\.venv\Scripts\python.exe indexing/build_indexes.py

$env:VAULTSEARCH_USER = 'user:ines'
$env:VAULTSEARCH_TOKEN = python -c "import secrets; print(secrets.token_urlsafe(32))"
$env:OLLAMA_MODEL = 'gemma3:4b'
.\.venv\Scripts\python.exe -m uvicorn app.api:app --host 127.0.0.1 --port 8000
```

Copy the generated token from your operator shell into the browser's **Demo token** field at http://127.0.0.1:8000. Keep the token private. The API refuses startup if the identity is unknown or the token has fewer than 32 characters. Generate a fresh random token when switching identities, then restart the API. A token holder acts as that single identity; this is not multi-user login. Do not use a privileged/admin demo identity for untrusted users.

Direct local setup reads environment variables, not `.env`. For Docker, copy `.env.example` to `.env`, set `VAULTSEARCH_USER` and a fresh random `VAULTSEARCH_TOKEN`, then run `docker compose up --build`. Compose keeps the API port on loopback. Do not commit `.env`.

Linux/macOS use the corresponding `.venv/bin/python` and `export` commands. `requirements.txt` lists dependencies. `OLLAMA_URL` defaults to `http://127.0.0.1:11434`; `OLLAMA_MODEL` defaults to `gemma3:4b`.

## API and MCP

Data routes require `Authorization: Bearer <token>`. `/health`, the static UI, and API schema are public and contain no corpus data.

- `POST /api/ask`: `{"question":"How many PTO days?","top_n":6}`
- `POST /api/search`: `{"query":"PTO days","top_n":6}`
- `GET /api/users`: the authenticated deployment identity and its visible chunk count.
- `GET /api/directory`: org-public names and memberships, without document counts.

An optional legacy `user_id` field is accepted only when it equals the server identity. It never selects an identity. Use the bound identity's token for MCP:

```json
{
  "mcpServers": {
    "vaultsearch": {
      "command": "/path/to/vaultsearch/.venv/bin/python",
      "args": ["/path/to/vaultsearch/mcp_server.py"],
      "env": {
        "VAULTSEARCH_URL": "http://127.0.0.1:8000",
        "VAULTSEARCH_TOKEN": "<operator-provided token>"
      }
    }
  }
}
```

MCP tools are `ask`, `search`, `lookup_person`, and `whoami`. No tool accepts an identity. `whoami` reads the API's identity; setting a different `VAULTSEARCH_USER` on the MCP client cannot change it. Protect client configuration files containing tokens. Keep HTTP on loopback; production requires an agreed authentication provider, TLS, secret lifecycle, abuse controls, and a separate review.

## Evaluation

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe redteam/retrieval_probe.py
.\.venv\Scripts\python.exe redteam/run_redteam.py
```

For an existing local Hugging Face cache, set `HF_HOME` to `.model-cache`; set `HF_HUB_OFFLINE=1` only when all required embedding/reranker files are cached.

The retrieval probe compares full API search responses across all four modes, retaining counts, scores, rankings, and result text while excluding timing fields. Three queries and repeated baselines do not prove general noninterference. The live suite additionally inspects answer/evidence/traces, prompt payload exposure, errors, fallback behavior, and model completion. It writes model/version/source identifiers and per-case records. Exit 0 means no configured failure observed in completed, exposed cases; exit 1 means a detected failure; exit 2 means inconclusive. Unexposed attacks, unavailable models, truncated generation, and incomplete runs are not passes. In-process evaluation configures trusted fixture identities and is not an end-to-end network authentication test.

The unit tests deliberately use scripted models and embeddings in some cases. Those tests validate enforcement and measurement logic, not empirical resistance of Ollama.

## Scope and remaining limits

The attacker can submit queries and malicious text in permitted documents, but cannot change server configuration, steal the bearer token, modify ACL truth, or inspect operator files. Directory names/memberships and permitted-document ACL labels are intentionally visible. Global hidden-document counts and hidden-dependent ranking statistics are within scope and have been removed from public responses/scoring.

Timings remain visible and depend on corpus traversal, model execution, and machine load. Timing indistinguishability is not established. Prompt injection, fabricated uncited facts, semantic leakage beyond configured secret variants, nondeterminism, malicious upstream permissions, and host compromise remain limitations. The critic is advisory; citation filtering only validates citation membership, not factual truth. Read measured reports before making claims.

Per-request permitted-corpus BM25 and exact vector scoring are appropriate for this small demo. Previous performance/quality tables describe an older implementation and have not been revalidated for this scoring change. Larger deployments need permission-partitioned indexes and carefully invalidated caches.

## Project map

- `app/`: API identity boundary, ACLs, retrieval, tools, agent orchestration, Ollama client.
- `ingestion/`, `indexing/`, `data/`: synthetic corpus and local index generation.
- `redteam/`, `tests/`, `reports/`: evaluation tools, regression tests, and measured artifacts.
- `web/`, `mcp_server.py`: browser and MCP clients.
- `cloud/`: optional LocalStack prototype; not validated by this security change.
- [Design](DESIGN.md), [restoration provenance](RESTORATION.md), [saved continuation checklist](CONTINUE_SECURITY.md).
- [Historical walkthrough](docs/legacy-walkthrough.md): background only, with obsolete setup and security claims clearly archived.
