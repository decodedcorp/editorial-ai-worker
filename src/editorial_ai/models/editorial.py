"""Pydantic models for editorial content generation output.

EditorialContent is the intermediate model that Gemini generates directly
(content-only, no layout). The layout is determined separately by Nano Banana
or the template fallback, then content is mapped into layout blocks.
"""

from pydantic import BaseModel, ConfigDict, Field

from editorial_ai.models.layout import CreditEntry


class ProductMention(BaseModel):
    """A product mentioned in the editorial content."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    brand: str | None = None
    context: str  # how it relates to the editorial


class CelebMention(BaseModel):
    """A celebrity mentioned in the editorial content."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    context: str  # how they relate to the editorial


class EditorialContent(BaseModel):
    """Intermediate editorial content produced by Gemini structured output.

    This model captures the *content* of an editorial before layout mapping.
    Fields correspond to what the LLM generates; the layout step places
    this content into MagazineLayout blocks.
    """

    model_config = ConfigDict(from_attributes=True)

    keyword: str
    title: str
    subtitle: str | None = None
    body_paragraphs: list[str]
    pull_quotes: list[str] = Field(default_factory=list)
    product_mentions: list[ProductMention] = Field(default_factory=list)
    celeb_mentions: list[CelebMention] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    credits: list[CreditEntry] = Field(default_factory=list)
