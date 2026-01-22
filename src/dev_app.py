from __future__ import annotations

import inspect
import os

from fastapi import FastAPI, Query
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP

from .qdrant_repo import QdrantRepo
from .schemas import GetPolicyChunkResult, SearchPolicyChunksResult

load_dotenv()

# --- MCP server (same as yours) ---
mcp = FastMCP("policy-mcp")
repo = QdrantRepo.from_env()

@mcp.tool()
def search_policy_chunks(
    query: str,
    doctype: str | None = None,
    department: str | None = None,
    revised_after: str | None = None,
    limit: int = 5,
) -> SearchPolicyChunksResult:
    items = repo.search(
        query=query,
        limit=limit,
        doctype=doctype,
        department=department,
        revised_after=revised_after,
    )
    return SearchPolicyChunksResult(items=items)

@mcp.tool()
def get_policy_chunk(id: str | int) -> GetPolicyChunkResult:
    item = repo.get(id)
    return GetPolicyChunkResult(item=item)

# --- FastAPI wrapper for quick testing ---
app = FastAPI(title="policy-mcp-dev")

# (1) Debug REST endpoints
@app.get("/debug/search")
def debug_search(
    query: str = Query(...),
    doctype: str | None = None,
    department: str | None = None,
    revised_after: str | None = None,
    limit: int = 5,
):
    res = search_policy_chunks(
        query=query,
        doctype=doctype,
        department=department,
        revised_after=revised_after,
        limit=limit,
    )
    return res.model_dump()  # pydantic v2

@app.get("/debug/chunk/{chunk_id}")
def debug_chunk(chunk_id: str):
    res = get_policy_chunk(chunk_id)
    return res.model_dump()

# (2) Mount MCP Streamable HTTP at /mcp
# 버전별로 method/인자명이 달라서 안전하게 처리
if hasattr(mcp, "streamable_http_app"):
    # path를 넘길 수 있으면 "/"로 두고 /mcp에 mount
    sig = inspect.signature(mcp.streamable_http_app)
    if "path" in sig.parameters:
        mcp_app = mcp.streamable_http_app(path="/")
    elif "http_path" in sig.parameters:
        mcp_app = mcp.streamable_http_app(http_path="/")
    else:
        mcp_app = mcp.streamable_http_app()
    app.mount("/mcp", mcp_app)
