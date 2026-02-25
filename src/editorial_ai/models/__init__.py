"""Pydantic models for Supabase table entities and pipeline output."""

from editorial_ai.models.celeb import Celeb
from editorial_ai.models.curation import (
    BrandReference,
    CelebReference,
    CuratedTopic,
    CurationResult,
    GroundingSource,
)
from editorial_ai.models.editorial import (
    CelebMention,
    EditorialContent,
    ProductMention,
)
from editorial_ai.models.layout import (
    BodyTextBlock,
    CelebFeatureBlock,
    CelebItem,
    CreditEntry,
    CreditsBlock,
    DividerBlock,
    HashtagBarBlock,
    HeadlineBlock,
    HeroBlock,
    ImageGalleryBlock,
    ImageItem,
    KeyValuePair,
    LayoutBlock,
    MagazineLayout,
    ProductItem,
    ProductShowcaseBlock,
    PullQuoteBlock,
    create_default_template,
)
from editorial_ai.models.post import Post
from editorial_ai.models.product import Product

__all__ = [
    "BodyTextBlock",
    "BrandReference",
    "Celeb",
    "CelebFeatureBlock",
    "CelebMention",
    "CelebItem",
    "CelebReference",
    "CreditEntry",
    "CreditsBlock",
    "CuratedTopic",
    "CurationResult",
    "EditorialContent",
    "DividerBlock",
    "GroundingSource",
    "HashtagBarBlock",
    "HeadlineBlock",
    "HeroBlock",
    "ImageGalleryBlock",
    "ImageItem",
    "KeyValuePair",
    "LayoutBlock",
    "MagazineLayout",
    "Post",
    "Product",
    "ProductItem",
    "ProductMention",
    "ProductShowcaseBlock",
    "PullQuoteBlock",
    "create_default_template",
]
