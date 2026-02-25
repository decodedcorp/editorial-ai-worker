"""Rich health check endpoint with dependency probing."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health_check(request: Request):
    """Probe Supabase, required tables, and checkpointer connectivity."""
    checks: dict = {}
    overall = "healthy"
    client = None

    # 1. Supabase connection
    try:
        from editorial_ai.services.supabase_client import get_supabase_client

        client = await get_supabase_client()
        resp = (
            await client.table("editorial_contents")
            .select("id", count="exact")
            .limit(0)
            .execute()
        )
        checks["supabase"] = {"status": "healthy", "editorial_contents_count": resp.count}
    except Exception as e:
        checks["supabase"] = {"status": "unhealthy", "error": str(e)}
        overall = "unhealthy"

    # 2. Required tables
    if client:
        table_status: dict[str, str] = {}
        for table_name in ["editorial_contents", "posts", "spots", "solutions"]:
            try:
                await client.table(table_name).select("id").limit(1).execute()
                table_status[table_name] = "ok"
            except Exception:
                table_status[table_name] = "missing_or_inaccessible"
                if overall == "healthy":
                    overall = "degraded"
        checks["tables"] = table_status
    else:
        checks["tables"] = {"status": "skipped", "reason": "supabase_unhealthy"}

    # 3. Checkpointer
    try:
        cp = request.app.state.checkpointer
        await cp.aget({"configurable": {"thread_id": "__health_check__"}})
        checks["checkpointer"] = {"status": "healthy"}
    except Exception as e:
        checks["checkpointer"] = {"status": "unhealthy", "error": str(e)}
        overall = "unhealthy"

    return {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }
