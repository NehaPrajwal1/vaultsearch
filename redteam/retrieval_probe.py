"""Real retrieval/API measurements without an LLM; never counts retrieval as prompt exposure."""
import json
import hashlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.acl import IdentityStore, can_access
from app.retrieval_core import Retriever
from redteam.run_redteam import (
    PAIR_QUESTIONS, QUESTIONS, changed_paths, fingerprint, make_client, stable_response, without_hidden,
)


def main():
    identity = IdentityStore.load(ROOT / "data/users_groups.json")
    retriever = Retriever(ROOT / "indexes", identity, use_reranker=True)
    rows = []
    for user in ("user:asha", "user:hiro", "user:ines"):
        for question in QUESTIONS:
            result = retriever.search(user, question, top_n=6)
            rows.append({
                "user_id": user, "question": question,
                "retrieved_injection_ids": sorted({c.doc_id for c in result.chunks if c.doc_id.startswith("inject-")}),
                "unauthorized_chunks": [c.chunk_id for c in result.chunks
                                        if not can_access(identity.expand_principals(user), c.allowed_principals)],
                "result_ids": [c.chunk_id for c in result.chunks],
            })
    absent = without_hidden(retriever, identity, "user:ines")
    pairs = []
    for question in PAIR_QUESTIONS:
        samples = []
        for variant in (retriever, retriever, absent):
            client = make_client(variant, identity, None)  # /search never uses the LLM
            try:
                response = client.post("/api/search", json={"user_id": "user:ines", "query": question, "mode": "all"})
                response.raise_for_status()
                samples.append(response.json())
            finally:
                client.close()
        a, b, c = [stable_response(s) for s in samples]
        pairs.append({
            "question": question, "baseline_stable": a == b,
            "response_changed": a != c, "stable_difference": a == b and a != c,
            "changed_fields": sorted(k for k in a.keys() | c.keys() if a.get(k) != c.get(k)),
            "changed_paths": changed_paths(a, c),
            "responses": samples,
        })
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "execution": "real BM25, MiniLM embeddings, FAISS, cross-encoder, and /api/search; no LLM",
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for folder in ("app", "redteam") for p in (ROOT / folder).glob("*.py")},
        "corpus_sha256": fingerprint(retriever.chunks),
        "injection_retrieval_cases": rows, "paired_cases": pairs,
        "unauthorized_chunk_count": sum(len(r["unauthorized_chunks"]) for r in rows),
        "cases_retrieving_injection_chunks": sum(bool(r["retrieved_injection_ids"]) for r in rows),
        "stable_paired_differences": sum(p["stable_difference"] for p in pairs),
    }
    (ROOT / "reports/retrieval_probe.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = ["# Retrieval-only boundary measurements", "",
             f"Execution: {report['execution']}", f"UTC: {report['timestamp_utc']}", "",
             f"- Cases: {len(rows)}",
             f"- Unauthorized chunks returned: {report['unauthorized_chunk_count']}",
             f"- Cases retrieving injection chunks: {report['cases_retrieving_injection_chunks']}",
             f"- Stable paired response differences: {report['stable_paired_differences']} / {len(pairs)}",
             "", "Retrieved injection chunks are NOT measured LLM exposure.",
             "Any paired differences indicate changed non-timing fields in these cases;",
             "they do not alone establish inference of any particular hidden topic.",
             "The harness uses a server-bound test identity; this does not validate production authentication.",
             "Full responses and changed fields are in retrieval_probe.json."]
    (ROOT / "reports/retrieval_probe.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 1 if report["unauthorized_chunk_count"] or report["stable_paired_differences"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
