"""Post model matching Supabase 'posts' table schema.

NOTE: Schema fields are based on reasonable defaults for a fashion editorial domain.
Verify against actual Supabase schema when credentials are available.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Post(BaseModel):
    """An editorial post entity."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    content: str | None = None
    status: str | None = None
    celeb_id: str | None = None
    thumbnail_url: str | None = None
    tags: list[str] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    published_at: datetime | None = None
