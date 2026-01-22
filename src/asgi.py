from src.server import mcp

# 이 app은 이미 /mcp 엔드포인트를 포함합니다.
app = mcp.streamable_http_app()