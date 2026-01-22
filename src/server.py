from __future__ import annotations

import inspect
import os

from mcp.server.fastmcp import FastMCP

from .qdrant_repo import QdrantRepo
from .schemas import GetPolicyChunkResult, SearchPolicyChunksResult
from dotenv import load_dotenv
load_dotenv()

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


def main() -> None:
    transport = os.getenv("MCP_TRANSPORT", "streamable-http").lower()
    if transport == "stdio":
        mcp.run(transport="stdio")
        return

    if transport != "streamable-http":
        raise ValueError(
            "Unsupported MCP_TRANSPORT. Use 'stdio' or 'streamable-http'."
        )

    # host = os.getenv("MCP_HOST", "0.0.0.0")
    # port = int(os.getenv("MCP_PORT", "8000"))
    # path = os.getenv("MCP_PATH", "/mcp")

    run_sig = inspect.signature(mcp.run)
    if "path" in run_sig.parameters:
        mcp.run(transport="streamable-http")#, host=host, port=port, path=path)
    elif "http_path" in run_sig.parameters:
        mcp.run(transport="streamable-http")#, host=host, port=port, http_path=path)
    else:
        mcp.run(transport="streamable-http")#, host=host, port=port)


if __name__ == "__main__":
    main()
