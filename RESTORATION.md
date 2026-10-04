# Implementation recovery

Eight missing runtime files were recovered from
https://github.com/vishakkashyapk30/vaultsearch at commit
`e38fb46ab8f25a9bc68b749566d9b98290c8a71f`, the original repository referenced
by the README. They were absent throughout this repository's history.

Recovered: `app/agents.py`, `app/api.py`, `app/cloud_audit.py`,
`app/ollama_client.py`, `app/retrieval_core.py`, `app/tools.py`,
`indexing/build_indexes.py`, and `ingestion/generate_data.py`.
Recovery does not establish that old reports describe this code.
Later changes add evaluation instrumentation, regression tests, and corrected claims.

This is a local persona demo, not an authenticated multi-user deployment.
The API trusts caller-selected user_id. The MCP wrapper does not authenticate
direct API callers. Docker now binds to loopback. A deployment needs
server-validated identity and a separate metadata/timing-channel review.

The live evaluation writes INCONCLUSIVE if Ollama is unavailable.
Deterministic test models validate the harness and enforcement code only;
their outcomes must never be reported as measured real-model resistance.
