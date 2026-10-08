"""Explicit browser QA fixture. Never loads or calls a model. Bind to loopback only."""
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from app.api import app
from app.acl import IdentityStore
from app.auth import configure_identity
from app.agents import Orchestrator
from app.ollama_client import OllamaError
from redteam.api_probe import LexicalRetriever
from test_release import corpus

class ScriptedModel:
    def chat_json(self,system,user):
        if system.startswith("You plan"): return {"subqueries":[user]}
        if system.startswith("You review"): return {"sufficient":True}
        return {"verdict":"grounded","unsupported_claims":[]}
    def chat(self,system,user,**kwargs):
        question=json.loads(user)["question"].lower()
        if "unavailable" in question: raise OllamaError("scripted unavailable model")
        if "migration" in question: return "Credentials must be transmitted to the supplied mailbox [export]."
        return "Employees receive 25 paid days off each year [leave]."

@asynccontextmanager
async def lifespan(application):
    identity=IdentityStore({"user:ines":["group:all-staff"]})
    configure_identity(application.state,identity)
    retriever=LexicalRetriever(corpus(),identity)
    application.state.identity=identity
    application.state.retriever=retriever
    application.state.search_only=False
    application.state.orchestrator=Orchestrator(retriever,identity,ScriptedModel(),max_refine_rounds=0,use_critic=True)
    application.state.audit=logging.getLogger("scripted-ui")
    application.state.audit_sink=None
    yield

app.router.lifespan_context=lifespan
if __name__=="__main__":
    import uvicorn
    print("SCRIPTED UI QA ONLY: no live model inference",flush=True)
    uvicorn.run(app,host="127.0.0.1",port=8766)
