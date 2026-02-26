"""FastAPI application with lifespan for checkpointer lifecycle."""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from editorial_ai.api.routes import admin, health, logs, pipeline
from editorial_ai.checkpointer import create_checkpointer
from editorial_ai.config import settings
from editorial_ai.graph import build_graph


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage checkpointer and graph lifecycle."""
    # Fail-fast: check required env vars
    missing = settings.validate_required_for_server()
    if missing:
        print(
            f"FATAL: Missing required environment variables:\n"
            + "\n".join(f"  - {v}" for v in missing)
            + "\nSee .env.example for required configuration.",
            file=sys.stderr,
        )
        sys.exit(1)

    async with create_checkpointer() as checkpointer:
        await checkpointer.setup()
        app.state.checkpointer = checkpointer
        app.state.graph = build_graph(checkpointer=checkpointer)
        yield


app = FastAPI(title="Editorial AI Admin API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "traceback": traceback.format_exc()},
    )


app.include_router(logs.router, prefix="/api/contents", tags=["logs"])
app.include_router(admin.router, prefix="/api/contents", tags=["contents"])
app.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"])
app.include_router(health.router, tags=["health"])
