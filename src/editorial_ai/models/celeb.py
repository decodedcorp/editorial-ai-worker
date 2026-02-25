"""Celeb model matching Supabase 'celebs' table schema.

NOTE: Schema fields are based on reasonable defaults for a fashion editorial domain.
Verify against actual Supabase schema when credentials are available.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Celeb(BaseModel):
    """A celebrity entity used in editorial content."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    name_en: str | None = None
    category: str | None = None
    profile_image_url: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
