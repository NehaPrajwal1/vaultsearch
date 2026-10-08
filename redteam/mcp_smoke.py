"""Real local MCP stdio -> HTTP integration. Uses search only; no model invocation."""
from datetime import timedelta
import asyncio
import json
import os
from pathlib import Path
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT=Path(__file__).resolve().parent.parent

async def probe(url, token, log_path):
    observations={"execution":"real MCP stdio client/server and loopback HTTP; no model calls"}
    async def connect(credential, invalid=False):
        params=StdioServerParameters(command=sys.executable,args=[str(ROOT/"mcp_server.py")],cwd=str(ROOT),
            env=dict(os.environ,VAULTSEARCH_URL=url,VAULTSEARCH_TOKEN=credential,VAULTSEARCH_USER="user:dmitri"))
        with Path(log_path).open("a",encoding="utf-8") as log:
            async with stdio_client(params,errlog=log) as (read,write):
                async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=10)) as session:
                    await session.initialize()
                    if invalid:
                        result=await session.call_tool("whoami",{})
                        assert result.isError and "credentials were rejected" in str(result)
                        return {"rejected":True,"is_error":result.isError}
                    listing=await session.list_tools()
                    assert {t.name for t in listing.tools}=={"search","ask","whoami","lookup_person"}
                    assert all("user_id" not in t.inputSchema.get("properties",{}) for t in listing.tools)
                    async def call(name,args):
                        result=await session.call_tool(name,args)
                        assert not result.isError, str(result)
                        return result.structuredContent or json.loads(result.content[0].text)
                    who=await call("whoami",{})
                    assert who["user_id"]=="user:ines"  # MCP env cannot choose the API identity.
                    search=await call("search",{"query":"paid time off","top_n":2})
                    assert len(search["results"])==2 and search["evidence_is_untrusted"]
                    assert all(item.get("chunk_id") and item.get("text") for item in search["results"])
                    spoof=await call("search",{"query":"paid time off","top_n":2,"user_id":"user:dmitri"})
                    assert spoof==search
                    disabled=await session.call_tool("ask",{"question":"How many PTO days?"})
                    assert disabled.isError and "disabled" in str(disabled)
                    invalid_query=await session.call_tool("search",{"query":"x"})
                    assert invalid_query.isError and "Invalid input" in str(invalid_query)
                    recovered=await call("search",{"query":"paid time off","top_n":2})
                    assert recovered==search
                    return {"tools":sorted(t.name for t in listing.tools),"identity_bound":True,"no_identity_parameter":True,
                        "unknown_identity_argument_does_not_change_result":True,"search_excerpts":len(search["results"]),
                        "disabled_ask_is_error":True,"invalid_query_is_error":True,"search_recovers_after_error":True}
    observations["valid_token"]=await connect(token)
    observations["invalid_token"]=await connect("invalid-demo-credential-with-at-least-32-characters",True)
    return observations

def run_probe(url,token,log_path):
    return asyncio.run(asyncio.wait_for(probe(url,token,log_path),timeout=45))
