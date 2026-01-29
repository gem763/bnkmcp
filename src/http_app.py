from fastapi import FastAPI
from src.server import mcp

app = FastAPI()

# ✅ MCP는 루트에 mount (중요)
# 그러면 MCP 엔드포인트는 내부적으로 그대로 /mcp 로 동작합니다.
app.mount("/", mcp.streamable_http_app())

@app.get("/health")
def health():
    return {"ok": True}
