"""Async Supabase client factory with lazy singleton initialization."""

from supabase import AsyncClient, acreate_client

from editorial_ai.config import settings

_client: AsyncClient | None = None


async def get_supabase_client() -> AsyncClient:
    """Return a cached async Supabase client, creating it on first call.

    Uses the service_role key to bypass Row Level Security (RLS),
    suitable for backend service access only.

    Raises:
        RuntimeError: If SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is not configured.
    """
    global _client  # noqa: PLW0603

    if _client is not None:
        return _client

    if not settings.supabase_url:
        msg = "SUPABASE_URL is not configured. Set it in .env or environment variables."
        raise RuntimeError(msg)

    if not settings.supabase_service_role_key:
        msg = (
            "SUPABASE_SERVICE_ROLE_KEY is not configured. "
            "Set it in .env or environment variables."
        )
        raise RuntimeError(msg)

    _client = await acreate_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )
    return _client


async def reset_client() -> None:
    """Reset the cached client. Useful for testing."""
    global _client  # noqa: PLW0603
    _client = None
