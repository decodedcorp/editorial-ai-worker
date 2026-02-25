"""FastAPI dependency injection for auth, graph, and checkpointer."""

from __future__ import annotations

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from langgraph.graph.state import CompiledStateGraph

from editorial_ai.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(
    api_key: str | None = Security(_api_key_header),
) -> str | None:
    """Verify X-API-Key header if ADMIN_API_KEY is configured.

    If ADMIN_API_KEY is not set (dev mode), skip auth entirely.
    If set, the request must provide a matching key.
    """
    if settings.admin_api_key is None:
        return None
    if api_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return api_key


def get_graph(request: Request) -> CompiledStateGraph:
    """Return the compiled graph from app state."""
    return request.app.state.graph


def get_checkpointer(request: Request):
    """Return the checkpointer from app state."""
    return request.app.state.checkpointer
