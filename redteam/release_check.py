"""Bounded offline portfolio-release validation. Never starts a model or overwrites results."""
from __future__ import annotations
import importlib.metadata
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/"tests"))

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    out=ROOT/".local-evaluations"/("release-check-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    out.mkdir(parents=True)
    report={"execution":"offline scripted tests, deterministic replay, BM25 and loopback HTTP; no model calls", "checks":{}, "status":"INCOMPLETE"}
    def save(): (out/"validation.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    historical=[p for p in (ROOT/"reports/redteam_results.json",ROOT/"reports/redteam_report.md") if p.is_file()]
    historical += [p for folder in ("colab-four-case-review","colab-second-round-review") for p in (ROOT/".local-evaluations"/folder).rglob("*") if p.is_file()]
    before={str(p.relative_to(ROOT)):digest(p) for p in historical}
    source=[p for folder in ("app","web","tests","redteam","ingestion") for p in (ROOT/folder).rglob("*") if p.is_file() and p.suffix in {".py",".js",".html",".css",".json"}]
    source += [ROOT/name for name in ("README.md","run_demo.py",".dockerignore","requirements-search.txt","requirements-test.txt","mcp_server.py","docker-compose.yml","docker-entrypoint.sh","setup.sh")]
    report["source"]={str(p.relative_to(ROOT)):digest(p) for p in sorted(source)}
    report["runtime"]={"python":sys.version,"packages":{name:importlib.metadata.version(name) for name in ("numpy","rank-bm25","faiss-cpu","fastapi","uvicorn","httpx","pytest","mcp")}}
    report["head"]=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    report["git_status"]=subprocess.check_output(["git","status","--short"],cwd=ROOT,text=True)
    save()
    try:
        result=subprocess.run([sys.executable,"-m","pytest","-q","-p","no:cacheprovider","--ignore=tests/test_integration_retrieval.py"],cwd=ROOT,capture_output=True,text=True,timeout=90)
        report["checks"]["lightweight"]={"returncode":result.returncode,"stdout":result.stdout,"stderr":result.stderr}
        save()
        if result.returncode: raise RuntimeError("Lightweight tests failed")
        from test_release import FIXTURES, acceptance
        acceptance_rows=[{"fixture":case,"api_case":acceptance(case)} for case in FIXTURES]
        (out/"acceptance.json").write_text(json.dumps(acceptance_rows,indent=2),encoding="utf-8")
        report["checks"]["acceptance"]={"cases":len(acceptance_rows),"execution":"scripted model; real BM25/API", "known_false_positive":"security_quote withheld"}
        from app.acl import IdentityStore, can_access
        from app.presentation import present_answer, SAFETY_MESSAGE
        from redteam.api_probe import LexicalRetriever
        from redteam.run_redteam import make_client, stable_response
        from test_release import Script
        identity=IdentityStore.load(ROOT/"data/users_groups.json")
        chunks=json.loads((ROOT/"data/chunks.json").read_text())
        pairs=[]
        for user in ("user:ines","user:asha","user:dmitri"):
            for query in ("Q3 infrastructure budget", "leadership compensation bands", "paid time off"):
                views=[]
                permitted=[c for c in chunks if can_access(identity.expand_principals(user),c["allowed_principals"])]
                for subset in (chunks,chunks,permitted):
                    client=make_client(LexicalRetriever(subset,identity),identity,Script(query,"unused"))
                    client.app.state.demo_user=user
                    try:
                        response=client.post("/api/search",json={"query":query})
                        response.raise_for_status()
                        views.append(stable_response(response.json()))
                    finally: client.close()
                pairs.append({"user":user,"query":query,"baseline_stable":views[0]==views[1],"identical":views[0]==views[2],"responses":views})
        (out/"retrieval-pairs.json").write_text(json.dumps(pairs,indent=2),encoding="utf-8")
        assert all(p["baseline_stable"] and p["identical"] for p in pairs)
        report["checks"]["retrieval_pairs"]={"stable":len(pairs),"differences":0,"scope":"existing synthetic corpus; BM25 only; full non-timing search responses"}
        replay=[]
        first=ROOT/".local-evaluations/colab-four-case-review/review.json"
        second=ROOT/".local-evaluations/colab-second-round-review/original-results.json"
        if first.exists() and second.exists():
            originals=[("round1",v["case"],v["case_result"]) for v in json.loads(first.read_text())]
            originals += [("round2",v["original_report"]["metadata"]["case"],v["original_report"]["case_result"]) for v in json.loads(second.read_text()).values()]
            for round_name,case,row in originals:
                calls=[c for c in row["calls"] if c["stage"]=="synthesis" and c["completed"]]
                assert len(calls)==1
                raw=calls[0]["response"]
                answer,state=present_answer(raw)
                expected="unflagged" if case=="benign" else "review_required"
                assert state["status"]==expected
                if expected=="review_required": assert answer==SAFETY_MESSAGE and raw not in answer
                else: assert answer==raw
                replay.append({"round":round_name,"case":case,"raw":raw,"public_answer":answer,"presentation":state,"original_status":row["status"]})
            (out/"offline-replay.json").write_text(json.dumps(replay,indent=2),encoding="utf-8")
            report["checks"]["replay"]={"cases":len(replay),"withheld":sum(x["presentation"]["status"]=="review_required" for x in replay),"scope":"presentation only; original automatic findings unchanged"}
        else:
            report["checks"]["replay"]={"status":"not_available", "reason":"Private historical archives are optional and not shipped in a new checkout"}
        # Real startup on loopback, no model subprocess. Process is always terminated.
        import httpx
        with socket.socket() as sock: sock.bind(("127.0.0.1",0));port=sock.getsockname()[1]
        token=secrets.token_urlsafe(32)
        env=dict(os.environ,VAULTSEARCH_USER="user:ines",VAULTSEARCH_TOKEN=token,VAULTSEARCH_SEARCH_ONLY="true",PYTHONDONTWRITEBYTECODE="1")
        with (out/"http-server.log").open("w") as log:
            process=subprocess.Popen([sys.executable,"-m","uvicorn","app.api:app","--host","127.0.0.1","--port",str(port)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
            try:
                with httpx.Client(base_url=f"http://127.0.0.1:{port}",timeout=3,trust_env=False) as client:
                    deadline=time.monotonic()+20
                    while True:
                        try:
                            health=client.get("/health");health.raise_for_status();break
                        except httpx.HTTPError:
                            if time.monotonic()>deadline or process.poll() is not None: raise RuntimeError("Search-only startup failed")
                            time.sleep(.2)
                    assert health.json()["search_only"]
                    assert client.get("/").status_code==200
                    assert client.post("/api/search",json={"query":"paid time off"}).status_code==401
                    client.headers["Authorization"]="Bearer "+token
                    search=client.post("/api/search",json={"query":"paid time off"})
                    assert search.status_code==200 and search.json()["modes"]["bm25"]["results"]
                    assert client.post("/api/search",json={"query":"budget","user_id":"user:dmitri"}).status_code==403
                    assert client.post("/api/ask",json={"question":"paid days"}).status_code==409
                    assert client.post("/api/search",json={"query":"x"}).status_code==422
                    from redteam.mcp_smoke import run_probe
                    report["checks"]["mcp_stdio"]=run_probe(f"http://127.0.0.1:{port}",token,out/"mcp-stderr.log")
                    report["checks"]["loopback_http"]={"startup":True,"static_ui":200,"unauthenticated":401,"conflicting_identity":403,"search":200,"generation_disabled":409,"invalid_query":422}
            finally:
                process.terminate()
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired: process.kill();process.wait(timeout=5)
        js=subprocess.run(["node","--check",str(ROOT/"web/app.js")],capture_output=True,text=True,timeout=15)
        report["checks"]["javascript"]={"returncode":js.returncode,"output":js.stdout+js.stderr}
        assert js.returncode==0
        whitespace=subprocess.run(["git","diff","--check"],cwd=ROOT,capture_output=True,text=True,timeout=20)
        report["checks"]["whitespace"]={"returncode":whitespace.returncode,"output":whitespace.stdout+whitespace.stderr}
        assert whitespace.returncode==0
        assert before=={str(p.relative_to(ROOT)):digest(p) for p in historical}
        report["checks"]["historical_artifacts"]={"unchanged":True,"files":len(before),"sha256":before}
        report["status"]="LOCAL_CHECKS_PASSED"
    except Exception as exc:
        report["status"]="FAILED_OR_INCOMPLETE"
        report["error"]=f"{type(exc).__name__}: {exc}"
        raise
    finally:
        save()
        print(out)
        print(report["status"])
if __name__=="__main__": main()
