from __future__ import annotations

import inspect
import time
import os
import asyncio, time

from typing import Annotated
from mcp.types import CallToolResult, TextContent
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from pathlib import Path
from .qdrant_repo import QdrantRepo
from .schemas import GetPolicyChunkResult, SearchPolicyChunksResult
from dotenv import load_dotenv
load_dotenv()


mcp = FastMCP(
    "policy-mcp",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    ),
)
repo = QdrantRepo.from_env()


WIDGET_URI = "ui://widget/policy-widget.v2.html"
WIDGET_FILE = Path(__file__).resolve().parent.parent / "web" / "public" / "policy-widget.v2.html"

@mcp.resource(WIDGET_URI, mime_type="text/html+skybridge")
def policy_widget() -> str:
    return WIDGET_FILE.read_text(encoding="utf-8")


TOOL_META = {
    "openai/outputTemplate": WIDGET_URI,
    "openai/widgetAccessible": True,  # 위젯에서 callTool 쓰려면 True
    "openai/toolInvocation/invoking": "사규를 검색 중…",
    "openai/toolInvocation/invoked": "사규 검색 결과",
}


@mcp.tool(meta=TOOL_META, annotations={"readOnlyHint": True})
async def search_policy_chunks(
    query: str,
    doctype: str | None = None,
    department: str | None = None,
    revised_after: str | None = None,
    limit: int = 5,
) -> Annotated[CallToolResult, SearchPolicyChunksResult]:
    t0 = time.time()
    print("[tool] search_policy_chunks start", query, flush=True)

    # ✅ 동기 I/O를 이벤트루프 밖으로
    items = await asyncio.to_thread(
        repo.search,
        query=query,
        limit=limit,
        doctype=doctype,
        department=department,
        revised_after=revised_after,
    )

    print("[tool] search_policy_chunks end", len(items), "elapsed", round(time.time()-t0, 2), "s", flush=True)

    structured = SearchPolicyChunksResult(items=items).model_dump()

    return CallToolResult(
        content=[TextContent(type="text", text=f"검색 결과 {len(items)}건입니다. 위젯에서 확인하세요.")],
        structuredContent=structured,
    )


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

    run_sig = inspect.signature(mcp.run)
    
    if "path" in run_sig.parameters:
        mcp.run(transport="streamable-http")
    elif "http_path" in run_sig.parameters:
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
