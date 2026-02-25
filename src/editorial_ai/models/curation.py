"""Pydantic models for curation pipeline output.

These models represent the structured output of the two-step Gemini grounding
pipeline: grounded research → structured JSON extraction.
"""

from pydantic import BaseModel, ConfigDict, Field


class CelebReference(BaseModel):
    """A celebrity referenced in a curated topic."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    relevance: str


class BrandReference(BaseModel):
    """A brand or product referenced in a curated topic."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    relevance: str


class GroundingSource(BaseModel):
    """A grounding source URL extracted from Gemini search grounding metadata."""

    url: str
    title: str | None = None


class CuratedTopic(BaseModel):
    """A single curated topic produced by the two-step Gemini grounding pipeline."""

    model_config = ConfigDict(from_attributes=True)

    keyword: str
    trend_background: str
    related_keywords: list[str]
    celebrities: list[CelebReference]
    brands_products: list[BrandReference]
    seasonality: str
    sources: list[GroundingSource] = Field(default_factory=list)
    relevance_score: float = Field(ge=0.0, le=1.0, description="0-1 trend relevance score")
    low_quality: bool = False


class CurationResult(BaseModel):
    """Aggregated result from curating a seed keyword and its sub-topics."""

    seed_keyword: str
    topics: list[CuratedTopic]
    total_generated: int  # before filtering
    total_filtered: int  # after relevance threshold
