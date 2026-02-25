"""CRUD service for the editorial_contents table in Supabase.

Provides async functions for saving, updating, and querying editorial content
that flows through the admin approval pipeline.
"""

from __future__ import annotations

from editorial_ai.services.supabase_client import get_supabase_client


async def save_pending_content(
    thread_id: str,
    layout_json: dict,
    title: str,
    keyword: str,
    review_summary: str | None = None,
) -> dict:
    """Save or update pending content for a given thread (upsert on thread_id).

    Idempotent: if content for the thread already exists, it overwrites
    the existing row. This makes node re-execution safe.
    """
    client = await get_supabase_client()
    data = {
        "thread_id": thread_id,
        "status": "pending",
        "title": title,
        "keyword": keyword,
        "layout_json": layout_json,
        "review_summary": review_summary,
    }
    response = (
        await client.table("editorial_contents")
        .upsert(data, on_conflict="thread_id")
        .execute()
    )
    return response.data[0]


async def update_content_status(
    content_id: str,
    status: str,
    *,
    rejection_reason: str | None = None,
    admin_feedback: str | None = None,
) -> dict:
    """Update the status of a content entry.

    Sets updated_at to now(). If status is 'published', also sets published_at.
    """
    client = await get_supabase_client()
    data: dict = {"status": status, "updated_at": "now()"}
    if rejection_reason is not None:
        data["rejection_reason"] = rejection_reason
    if admin_feedback is not None:
        data["admin_feedback"] = admin_feedback
    if status == "published":
        data["published_at"] = "now()"
    response = (
        await client.table("editorial_contents")
        .update(data)
        .eq("id", content_id)
        .execute()
    )
    return response.data[0]


async def get_content_by_id(content_id: str) -> dict | None:
    """Fetch a single content entry by its UUID."""
    client = await get_supabase_client()
    response = (
        await client.table("editorial_contents")
        .select("*")
        .eq("id", content_id)
        .maybe_single()
        .execute()
    )
    return response.data


async def get_content_by_thread_id(thread_id: str) -> dict | None:
    """Fetch a single content entry by LangGraph thread_id."""
    client = await get_supabase_client()
    response = (
        await client.table("editorial_contents")
        .select("*")
        .eq("thread_id", thread_id)
        .maybe_single()
        .execute()
    )
    return response.data


async def list_contents(
    *, status: str | None = None, limit: int = 50, offset: int = 0
) -> list[dict]:
    """List content entries, optionally filtered by status, ordered by created_at desc."""
    client = await get_supabase_client()
    query = client.table("editorial_contents").select("*", count="exact")
    if status is not None:
        query = query.eq("status", status)
    response = (
        await query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    )
    return response.data


async def list_contents_count(*, status: str | None = None) -> int:
    """Count content entries, optionally filtered by status."""
    client = await get_supabase_client()
    query = client.table("editorial_contents").select("*", count="exact")
    if status is not None:
        query = query.eq("status", status)
    response = await query.limit(0).execute()
    return response.count or 0
