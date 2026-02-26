"""Pydantic models for Supabase table entities and pipeline output."""

from editorial_ai.models.celeb import Celeb
from editorial_ai.models.curation import (
    BrandReference,
    CelebReference,
    CuratedTopic,
    CurationResult,
    GroundingSource,
)
from editorial_ai.models.design_spec import (
    ColorPalette,
    DesignSpec,
    FontPairing,
    default_design_spec,
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
from editorial_ai.models.review import CriterionResult, ReviewResult

__all__ = [
    "BodyTextBlock",
    "BrandReference",
    "Celeb",
    "CelebFeatureBlock",
    "CelebMention",
    "CelebItem",
    "CelebReference",
    "ColorPalette",
    "CreditEntry",
    "CriterionResult",
    "CreditsBlock",
    "CuratedTopic",
    "CurationResult",
    "DesignSpec",
    "EditorialContent",
    "DividerBlock",
    "FontPairing",
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
    "ReviewResult",
    "create_default_template",
    "default_design_spec",
]
