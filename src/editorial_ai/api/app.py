"""FastAPI application with lifespan for checkpointer lifecycle."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from editorial_ai.api.routes import admin, pipeline
from editorial_ai.checkpointer import create_checkpointer
from editorial_ai.graph import build_graph


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage checkpointer and graph lifecycle."""
    async with create_checkpointer() as checkpointer:
        await checkpointer.setup()
        app.state.checkpointer = checkpointer
        app.state.graph = build_graph(checkpointer=checkpointer)
        yield


app = FastAPI(title="Editorial AI Admin API", lifespan=lifespan)

app.include_router(admin.router, prefix="/api/contents", tags=["contents"])
app.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"])


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
