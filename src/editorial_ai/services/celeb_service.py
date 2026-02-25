"""Read-only service functions for the celebs table."""

from editorial_ai.models.celeb import Celeb
from editorial_ai.services.supabase_client import get_supabase_client


async def get_celeb_by_id(celeb_id: str) -> Celeb | None:
    """Fetch a single celeb by ID. Returns None if not found."""
    client = await get_supabase_client()
    response = await (
        client.table("celebs").select("*").eq("id", celeb_id).maybe_single().execute()
    )
    if response is None or response.data is None:
        return None
    return Celeb.model_validate(response.data)


async def search_celebs(query: str, *, limit: int = 10) -> list[Celeb]:
    """Search celebs by name (case-insensitive partial match)."""
    client = await get_supabase_client()
    response = await (
        client.table("celebs").select("*").ilike("name", f"%{query}%").limit(limit).execute()
    )
    return [Celeb.model_validate(row) for row in response.data]


async def search_celebs_multi(queries: list[str], *, limit: int = 10) -> list[Celeb]:
    """Search celebs across name, name_en, description for multiple queries.

    Uses Supabase or_() with PostgREST syntax for multi-column ilike matching.
    Results from all queries are deduplicated by ID, preserving first occurrence order.
    """
    if not queries:
        return []
    client = await get_supabase_client()
    all_results: list[Celeb] = []
    for query in queries:
        pattern = f"%{query}%"
        response = await (
            client.table("celebs")
            .select("*")
            .or_(f"name.ilike.{pattern},name_en.ilike.{pattern},description.ilike.{pattern}")
            .limit(limit)
            .execute()
        )
        all_results.extend(Celeb.model_validate(row) for row in response.data)
    return _deduplicate_by_id(all_results)


def _deduplicate_by_id(items: list[Celeb]) -> list[Celeb]:
    """Remove duplicate celebs by ID, preserving first occurrence order."""
    seen: set[str] = set()
    result: list[Celeb] = []
    for item in items:
        if item.id not in seen:
            seen.add(item.id)
            result.append(item)
    return result
