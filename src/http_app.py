# src/http_app.py
import contextlib
from fastapi import FastAPI
from src.server import mcp

mcp_app = mcp.streamable_http_app()

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp.session_manager.run():
        yield

app = FastAPI(lifespan=lifespan)

# ✅ 1) health를 먼저 등록
@app.get("/health")
def health():
    return {"ok": True}

# ✅ 2) 맨 마지막에 "/"로 mount
app.mount("/", mcp_app)
