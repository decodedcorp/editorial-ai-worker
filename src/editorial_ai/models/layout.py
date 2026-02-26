"""Pydantic models for Magazine Layout JSON schema.

The MagazineLayout model is the core data contract between the AI pipeline
and the decoded-editorial frontend renderer. It defines a block-based layout
where each block type maps to a frontend React component.

Schema version: 1.0
"""

from __future__ import annotations

from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from editorial_ai.models.design_spec import DesignSpec

# ---------------------------------------------------------------------------
# Animation type for per-block GSAP animations (AI-decided)
# ---------------------------------------------------------------------------

AnimationType = Literal[
    "fade-up", "fade-in", "slide-left", "slide-right", "scale-in", "parallax", "none"
]

# ---------------------------------------------------------------------------
# Supporting models
# ---------------------------------------------------------------------------


class KeyValuePair(BaseModel):
    """Generic key-value pair. Used instead of dict[str, str] for Gemini compatibility."""

    key: str
    value: str


class ImageItem(BaseModel):
    """An image reference within a gallery or block."""

    model_config = ConfigDict(from_attributes=True)

    url: str
    alt: str | None = None
    caption: str | None = None


class ProductItem(BaseModel):
    """A product reference within a product showcase block.

    product_id is a placeholder for Phase 5 DB linking via Supabase.
    """

    model_config = ConfigDict(from_attributes=True)

    product_id: str | None = None
    name: str
    brand: str | None = None
    image_url: str | None = None
    description: str | None = None


class CelebItem(BaseModel):
    """A celebrity reference within a celeb feature block.

    celeb_id is a placeholder for Phase 5 DB linking via Supabase.
    """

    model_config = ConfigDict(from_attributes=True)

    celeb_id: str | None = None
    name: str
    image_url: str | None = None
    description: str | None = None


class CreditEntry(BaseModel):
    """A single credit attribution entry."""

    model_config = ConfigDict(from_attributes=True)

    role: str
    name: str


# ---------------------------------------------------------------------------
# Block type models — each has a Literal `type` discriminator
# ---------------------------------------------------------------------------


class HeroBlock(BaseModel):
    """Full-width hero image with optional overlay text."""

    model_config = ConfigDict(from_attributes=True)

    type: Literal["hero"] = "hero"
    image_url: str
    overlay_title: str | None = None
    overlay_subtitle: str | None = None
    animation: Optional[AnimationType] = None


class HeadlineBlock(BaseModel):
    """Large typography headline section."""

    model_config = ConfigDict(from_attributes=True)

    type: Literal["headline"] = "headline"
    text: str
    level: int = Field(default=1, ge=1, le=3)
    animation: Optional[AnimationType] = None


class BodyTextBlock(BaseModel):
    """Body copy paragraph(s)."""

    model_config = ConfigDict(from_attributes=True)

    type: Literal["body_text"] = "body_text"
    paragraphs: list[str]
    animation: Optional[AnimationType] = None


class ImageGalleryBlock(BaseModel):
    """Grid, carousel, or masonry image gallery."""

    model_config = ConfigDict(from_attributes=True)

    type: Literal["image_gallery"] = "image_gallery"
    images: list[ImageItem]
    layout_style: Literal["grid", "carousel", "masonry"] = "grid"
    animation: Optional[AnimationType] = None


class PullQuoteBlock(BaseModel):
    """Highlighted quote or callout."""

    model_config = ConfigDict(from_attributes=True)

    type: Literal["pull_quote"] = "pull_quote"
    quote: str
    attribution: str | None = None
    animation: Optional[AnimationType] = None


class ProductShowcaseBlock(BaseModel):
    """Product showcase section with product cards."""

    model_config = ConfigDict(from_attributes=True)

    type: Literal["product_showcase"] = "product_showcase"
    products: list[ProductItem]
    animation: Optional[AnimationType] = None


class CelebFeatureBlock(BaseModel):
    """Celebrity spotlight section."""

    model_config = ConfigDict(from_attributes=True)

    type: Literal["celeb_feature"] = "celeb_feature"
    celebs: list[CelebItem]
    animation: Optional[AnimationType] = None


class DividerBlock(BaseModel):
    """Visual separator between sections."""

    model_config = ConfigDict(from_attributes=True)

    type: Literal["divider"] = "divider"
    style: Literal["line", "space", "ornament"] = "line"
    animation: Optional[AnimationType] = None


class HashtagBarBlock(BaseModel):
    """Trending hashtags / keyword bar."""

    model_config = ConfigDict(from_attributes=True)

    type: Literal["hashtag_bar"] = "hashtag_bar"
    hashtags: list[str]
    animation: Optional[AnimationType] = None


class CreditsBlock(BaseModel):
    """Attribution and source credits."""

    model_config = ConfigDict(from_attributes=True)

    type: Literal["credits"] = "credits"
    entries: list[CreditEntry]
    animation: Optional[AnimationType] = None


# ---------------------------------------------------------------------------
# Discriminated union of all block types
# ---------------------------------------------------------------------------

LayoutBlock = (
    HeroBlock
    | HeadlineBlock
    | BodyTextBlock
    | ImageGalleryBlock
    | PullQuoteBlock
    | ProductShowcaseBlock
    | CelebFeatureBlock
    | DividerBlock
    | HashtagBarBlock
    | CreditsBlock
)


# ---------------------------------------------------------------------------
# Container model
# ---------------------------------------------------------------------------


class MagazineLayout(BaseModel):
    """Complete magazine editorial layout — the core frontend renderer contract.

    This is the final output of the editorial pipeline. The frontend
    (decoded-editorial) renders each block in sequence.
    """

    model_config = ConfigDict(from_attributes=True)

    schema_version: str = "1.0"
    title: str
    subtitle: str | None = None
    keyword: str
    blocks: list[Annotated[LayoutBlock, Field(discriminator="type")]]
    created_at: str | None = None
    metadata: list[KeyValuePair] = Field(default_factory=list)
    design_spec: DesignSpec | None = None


# ---------------------------------------------------------------------------
# Default template factory
# ---------------------------------------------------------------------------


def create_default_template(keyword: str, title: str) -> MagazineLayout:
    """Create a minimal valid layout with standard block sequence.

    This is the fallback when Nano Banana layout generation fails.
    """
    return MagazineLayout(
        keyword=keyword,
        title=title,
        blocks=[
            HeroBlock(image_url="", overlay_title=title, animation="parallax"),
            HeadlineBlock(text=title, animation="fade-up"),
            BodyTextBlock(paragraphs=[], animation="fade-up"),
            PullQuoteBlock(quote="", animation="scale-in"),
            DividerBlock(style="line", animation="fade-in"),
            ImageGalleryBlock(images=[], layout_style="grid", animation="fade-up"),
            BodyTextBlock(paragraphs=[], animation="fade-up"),
            DividerBlock(style="space", animation="fade-in"),
            ProductShowcaseBlock(products=[], animation="slide-right"),
            CelebFeatureBlock(celebs=[], animation="scale-in"),
            DividerBlock(style="line", animation="fade-in"),
            HashtagBarBlock(hashtags=[keyword], animation="slide-left"),
            CreditsBlock(
                entries=[CreditEntry(role="AI Editor", name="decoded editorial")],
                animation="fade-in",
            ),
        ],
    )
