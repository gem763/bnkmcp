# src/http_app.py
from starlette.applications import Starlette
from starlette.routing import Mount

from src.server import mcp  # mcp 객체/툴 등록만 있는 모듈이어야 함(아래 참고)

app = Starlette(
    routes=[
        Mount("/mcp", app=mcp.streamable_http_app()),
    ]
)
