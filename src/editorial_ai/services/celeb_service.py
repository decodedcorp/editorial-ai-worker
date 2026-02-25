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
