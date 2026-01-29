# src/http_app.py
import contextlib
from fastapi import FastAPI

from src.server import mcp

mcp_app = mcp.streamable_http_app()

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # ✅ MCP 세션 매니저를 FastAPI 라이프사이클에 연결
    async with mcp.session_manager.run():
        yield

app = FastAPI(lifespan=lifespan)

# ✅ 중요: /mcp로 다시 mount 하지 말고 "/"에 mount
# (mcp_app 내부가 이미 /mcp 엔드포인트를 갖고 있음)
app.mount("/", mcp_app)

@app.get("/health")
def health():
    return {"ok": True}
