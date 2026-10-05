# Running and interpreting the evaluation

Build the real indexes first:

```sh
python ingestion/generate_data.py
python ingestion/ingest.py
python indexing/build_indexes.py
python -m pytest -q
python eval/evaluate.py
python redteam/retrieval_probe.py
ollama pull gemma3:4b
python redteam/run_redteam.py --repeats 3
```

Ollama must be serving at OLLAMA_URL (default http://127.0.0.1:11434).
OLLAMA_MODEL selects the actual model. The runner saves the tags/model metadata,
source and index hashes, package versions, timestamp, inputs, outputs, errors,
raw/final citation findings, and per-stage submitted payload IDs in JSON.

Exit codes: 0 = no failure observed in the completed scoped experiment,
1 = detected failure, 2 = incomplete/inconclusive. None means production validated.
An empty run, model fallback, missing synthesis, unexposed attack, or unstable
paired baseline cannot be counted as a successful defense. Inspect the JSON
even on exit 0: coverage is small and the string oracle is not exhaustive.

The live harness uses the actual /api/ask handler and response serialization
in process. It observes prompts without modifying them. Exposure requires the
whole malicious instruction in a completed assessment/synthesis call. Document
retrieval alone is not exposure, and submission does not prove the model
processed the entire context. It never reuses a different synthesis shortcut.

Secret variants cover configured facts, case/Unicode/whitespace normalization,
and several number forms. The oracle derives restrictions from actual indexed
ACLs and excludes facts also present in permitted text. It checks all returned
JSON, not only the answer. It cannot adjudicate every paraphrase or fabrication.
Citation labels are inspected independently of the production sanitizer, before
and after the real route. Valid IDs do not establish factual grounding.

The paired experiment keeps the query and visible documents unchanged, removes
hidden documents, and rebuilds BM25/FAISS. It repeats the present-corpus baseline.
This checks observable response dependence, not a statistically powered classifier
for any particular topic. Timing measurements alone do not establish resistance.

retrieval_probe.py measures the real /api/search endpoint without Ollama.
It separately records whether injection chunks were retrieved (not LLM exposure)
and observable changes to paired search responses. Global corpus counts have been removed from responses; BM25 statistics now use
only the permitted corpus. Per-field differences are recorded in changed_paths.

tests/test_redteam.py uses scripted models, including deliberately leaky and broken
ones, to verify that the harness detects failures. Those tests are not empirical
LLM red-team results. Keep them separate from reports/redteam_report.md.

The original report's zero-breach and indistinguishability claims are withdrawn.
The API now requires a token bound to one server-configured test identity.
The evaluation harness configures fixture identities in process; it does not
measure network authentication. Separate API regression tests cover spoofing.
Do not expose it as an authenticated multi-user service. Docker binds to loopback.
