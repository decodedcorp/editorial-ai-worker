"""Product model matching Supabase 'products' table schema.

NOTE: Schema fields are based on reasonable defaults for a fashion editorial domain.
Verify against actual Supabase schema when credentials are available.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Product(BaseModel):
    """A fashion product entity used in editorial content."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    brand: str | None = None
    category: str | None = None
    price: int | None = None
    image_url: str | None = None
    description: str | None = None
    product_url: str | None = None
    tags: list[str] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
