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

This remains a local demo. The later security work binds API requests to a
server-configured test identity using a random bearer token, shared with MCP.
Production authentication and timing-channel review remain out of scope.
See reports/security_review.md for current measurements.

The live evaluation writes INCONCLUSIVE if Ollama is unavailable.
Deterministic test models validate the harness and enforcement code only;
their outcomes must never be reported as measured real-model resistance.
