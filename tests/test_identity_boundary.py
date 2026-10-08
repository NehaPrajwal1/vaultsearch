from types import SimpleNamespace
import httpx
import pytest
from app.auth import configure_identity
from app.ollama_client import OllamaClient, OllamaError
from app.tools import Toolbox
from redteam.run_redteam import make_client, without_hidden
from test_tools import FakeRetriever, make_chunks, make_identity
from test_redteam import Model

@pytest.fixture
def client():
    identity = make_identity()
    client = make_client(FakeRetriever(make_chunks(), identity), identity, Model())
    client.app.state.demo_user = "user:eng"
    yield client
    client.close()

@pytest.mark.parametrize("path,body", [("/api/users", None), ("/api/directory", None), ("/api/ask", {"question":"pto days"}), ("/api/search", {"query":"pto days"})])
@pytest.mark.parametrize("header", ["", "Bearer wrong", "Basic wrong"])
def test_no_data_without_token(client, path, body, header):
    res = client.request("GET" if body is None else "POST", path, json=body, headers={"Authorization":header})
    assert res.status_code == 401
    assert "budget" not in res.text

@pytest.mark.parametrize("path,key", [("/api/search","query"), ("/api/ask","question")])
def test_claim_cannot_override_server_identity(client, path, key):
    assert client.post(path, json={key:"budget", "user_id":"user:fin"}).status_code == 403
    assert client.post(path, json={key:"budget", "user_id":"user:unknown"}).status_code == 403
    response = client.post(path, json={key:"budget"})
    assert response.status_code == 200
    assert "1.2 million" not in response.text

def test_identity_directory_and_traces_hide_corpus_totals(client):
    users = client.get("/api/users").json()
    assert [u["user_id"] for u in users["users"]] == ["user:eng"]
    assert "total_chunks" not in users
    directory = client.get("/api/directory").json()
    assert all("visible_chunks" not in u for u in directory["users"])
    response = client.post("/api/ask", json={"question":"pto days"})
    assert response.status_code == 200
    for forbidden in ("total_candidates", "total_chunks", "verification_rejections"):
        assert forbidden not in response.text
    toolbox = Toolbox("user:eng", client.app.state.retriever, make_identity())
    assert "total_chunks" not in toolbox.list_my_sources()

def test_invalid_startup_configuration_fails_closed(monkeypatch):
    for user, token in [("", "x"*40), ("user:unknown", "x"*40), ("user:eng", "short")]:
        monkeypatch.setenv("VAULTSEARCH_USER", user)
        monkeypatch.setenv("VAULTSEARCH_TOKEN", token)
        with pytest.raises(RuntimeError):
            configure_identity(SimpleNamespace(), make_identity())
    monkeypatch.setenv("VAULTSEARCH_TOKEN", "x"*40)
    state = SimpleNamespace()
    configure_identity(state, make_identity())
    assert state.demo_user == "user:eng"

@pytest.mark.parametrize("value", [{"done":False, "message":{"content":"partial"}}, {"done":True,"done_reason":"length","message":{"content":"partial"}}, {"done":True,"message":{"content":""}}])
def test_incomplete_ollama_output_is_not_completion(monkeypatch, value):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(200, json=value, request=httpx.Request("POST","http://localhost/api/chat")))
    with pytest.raises(OllamaError):
        OllamaClient().chat("system", "question")

def test_hidden_corpus_and_order_cannot_change_rankings():
    import faiss
    import numpy as np
    from app.retrieval_core import Retriever
    identity = make_identity()
    r = Retriever.__new__(Retriever)
    r.identity = identity
    r.chunks = make_chunks() + [{**make_chunks()[0], "chunk_id":"extra", "doc_id":"extra", "text":"unrelated words"}]
    class Embedder:
        def encode(self, *a, **kw): return np.array([[1., 0.]], dtype="float32")
    r.embedder = Embedder()
    r.reranker = None
    r.faiss_index = faiss.IndexFlatIP(2)
    r.faiss_index.add(np.array([[1.,0.]] * len(r.chunks), dtype="float32"))
    absent = without_hidden(r, identity, "user:eng")
    absent.chunks.reverse()  # identical vectors; tie order must use stable IDs
    for mode in ("bm25", "vector", "hybrid", "hybrid+rerank"):
        def view(x):
            return [(c.chunk_id,c.score) for c in x.search("user:eng","atlas pto",mode=mode).chunks]
        assert view(r) == view(absent)


def test_mcp_uses_token_and_api_reported_identity(monkeypatch):
    import importlib
    monkeypatch.setenv("VAULTSEARCH_TOKEN", "m" * 40)
    monkeypatch.setenv("VAULTSEARCH_USER", "user:fin")  # cannot override API binding
    import mcp_server
    mcp_server = importlib.reload(mcp_server)
    requests = []
    class Client:
        def __init__(self, **kwargs):
            assert kwargs["headers"] == {"Authorization":"Bearer " + "m" * 40}
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get(self, url):
            requests.append((url, None))
            return httpx.Response(200, json={"users":[{"user_id":"user:eng","name":"Eve","groups":[],"visible_chunks":2}]}, request=httpx.Request("GET",url))
        def post(self, url, json):
            requests.append((url, json))
            return httpx.Response(200, json={"modes":{"bm25":{"results":[]}},"visible_chunks":2},request=httpx.Request("POST",url))
    monkeypatch.setattr(mcp_server.httpx, "Client", Client)
    assert mcp_server.whoami()["user_id"] == "user:eng"
    assert mcp_server.search("budget")["searched_chunks"] == 2
    assert "user_id" not in requests[-1][1]


def test_mcp_preserves_full_citation_evidence_and_untrusted_label(monkeypatch):
    monkeypatch.setenv("VAULTSEARCH_TOKEN","m"*40)
    import mcp_server
    evidence={"doc_id":"leave","chunk_id":"leave#0","source":"fixture","title":"Leave policy","text":"25 paid days off.","cited":True}
    monkeypatch.setattr(mcp_server,"_post",lambda *a,**kw:{"answer":"25 days [leave].","citations":["leave"],"evidence":[evidence],"trace":{"answer_status":"draft"}})
    result=mcp_server.ask("paid days")
    assert result["evidence"]==[evidence]
    assert result["evidence_is_untrusted"] and result["status"]=="draft"


def test_mcp_transport_failure_hides_internal_diagnostics(monkeypatch):
    monkeypatch.setenv("VAULTSEARCH_TOKEN","m"*40)
    import mcp_server
    from mcp.server.fastmcp.exceptions import ToolError
    class Unavailable:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,*args,**kwargs):raise httpx.ConnectError("internal-hostname-and-sensitive-diagnostic")
    monkeypatch.setattr(mcp_server.httpx,"Client",Unavailable)
    with pytest.raises(ToolError,match="could not be reached") as exc:
        mcp_server.ask("paid days")
    assert "internal-hostname" not in str(exc.value)
