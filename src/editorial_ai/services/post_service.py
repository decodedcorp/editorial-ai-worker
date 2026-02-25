"""Read-only service functions for the posts table."""

from editorial_ai.models.post import Post
from editorial_ai.services.supabase_client import get_supabase_client


async def get_post_by_id(post_id: str) -> Post | None:
    """Fetch a single post by ID. Returns None if not found."""
    client = await get_supabase_client()
    response = await (
        client.table("posts").select("*").eq("id", post_id).maybe_single().execute()
    )
    if response is None or response.data is None:
        return None
    return Post.model_validate(response.data)


async def list_posts(*, limit: int = 20) -> list[Post]:
    """List recent posts, ordered by created_at descending."""
    client = await get_supabase_client()
    response = await (
        client.table("posts")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [Post.model_validate(row) for row in response.data]
