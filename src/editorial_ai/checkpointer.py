"""AsyncPostgresSaver factory for graph state persistence.

Uses Supabase's Postgres session pooler (port 5432).
The factory returns an async context manager -- caller manages lifecycle.
"""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from editorial_ai.config import settings


def create_checkpointer() -> AbstractAsyncContextManager[AsyncPostgresSaver]:
    """Create an AsyncPostgresSaver from DATABASE_URL.

    Returns an async context manager. Usage::

        async with create_checkpointer() as checkpointer:
            await checkpointer.setup()
            graph = build_graph(checkpointer=checkpointer)
            ...

    ``from_conn_string()`` sets ``autocommit=True``,
    ``prepare_threshold=0`` automatically -- compatible with Supabase pooler.

    Raises:
        ValueError: If DATABASE_URL is not configured.
    """
    if not settings.database_url:
        raise ValueError(
            "DATABASE_URL is required for checkpointer. "
            "Set it to your Supabase session pooler connection string (port 5432)."
        )
    return AsyncPostgresSaver.from_conn_string(settings.database_url)
