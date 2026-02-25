"""Enrichment service orchestrating keyword expansion, DB search, and content re-generation.

Pipeline:
1. Extract celeb/product mention names from current layout
2. Expand keywords via Gemini for broader search coverage
3. Search Supabase with mention names + expanded keywords
4. Re-generate editorial content with real DB data as context
5. Rebuild layout blocks with actual DB IDs

Uses existing utilities from curation_service (retry, strip_fences, get_client)
and search functions from celeb_service/product_service.
"""

import json
import logging
from copy import deepcopy

from google import genai
from google.genai import types

from editorial_ai.config import settings
from editorial_ai.models.celeb import Celeb
from editorial_ai.models.editorial import EditorialContent
from editorial_ai.models.layout import (
    BodyTextBlock,
    CelebFeatureBlock,
    CelebItem,
    MagazineLayout,
    ProductItem,
    ProductShowcaseBlock,
)
from editorial_ai.models.product import Product
from editorial_ai.prompts.enrich import (
    build_enrichment_regeneration_prompt,
    build_keyword_expansion_prompt,
)
from editorial_ai.services.celeb_service import search_celebs_multi
from editorial_ai.services.curation_service import (
    _strip_markdown_fences,
    get_genai_client,
    retry_on_api_error,
)
from editorial_ai.services.product_service import search_products_multi

logger = logging.getLogger(__name__)


def extract_celeb_names(layout: MagazineLayout) -> list[str]:
    """Extract celeb names from CelebFeatureBlock blocks in layout."""
    names: list[str] = []
    for block in layout.blocks:
        if isinstance(block, CelebFeatureBlock):
            names.extend(c.name for c in block.celebs)
    return names


def extract_product_names(layout: MagazineLayout) -> list[str]:
    """Extract product names from ProductShowcaseBlock blocks in layout."""
    names: list[str] = []
    for block in layout.blocks:
        if isinstance(block, ProductShowcaseBlock):
            names.extend(p.name for p in block.products)
    return names


@retry_on_api_error
async def expand_keywords(client: genai.Client, keyword: str) -> list[str]:
    """Use Gemini to expand a keyword into related fashion search terms.

    Returns a list of related search term strings. On parse error,
    returns an empty list (graceful degradation).
    """
    prompt = build_keyword_expansion_prompt(keyword)
    response = await client.aio.models.generate_content(
        model=settings.default_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.3,
        ),
    )
    try:
        raw = _strip_markdown_fences(response.text or "[]")
        terms = json.loads(raw)
        if not isinstance(terms, list):
            logger.warning("Keyword expansion response is not a list, returning empty")
            return []
        return [str(t) for t in terms]
    except (json.JSONDecodeError, TypeError):
        logger.warning("Failed to parse keyword expansion JSON response")
        return []


@retry_on_api_error
async def regenerate_with_enrichment(
    client: genai.Client,
    original: EditorialContent,
    celebs: list[Celeb],
    products: list[Product],
    keyword: str,
) -> EditorialContent:
    """Re-generate editorial content with DB celeb/product data as context.

    Uses Gemini structured output to produce an enriched EditorialContent.
    On failure, returns the original content unchanged (graceful degradation).
    """
    original_json = original.model_dump_json()
    celebs_json = json.dumps(
        [c.model_dump(mode="json", exclude={"created_at", "updated_at"}) for c in celebs],
        ensure_ascii=False,
    )
    products_json = json.dumps(
        [p.model_dump(mode="json", exclude={"created_at", "updated_at"}) for p in products],
        ensure_ascii=False,
    )

    prompt = build_enrichment_regeneration_prompt(
        original_json, celebs_json, products_json, keyword
    )

    try:
        response = await client.aio.models.generate_content(
            model=settings.editorial_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=EditorialContent,
                temperature=0.7,
            ),
        )
        raw_text = response.text or "{}"
        return EditorialContent.model_validate_json(
            _strip_markdown_fences(raw_text),
        )
    except Exception:  # noqa: BLE001
        logger.warning("Re-generation failed, returning original content", exc_info=True)
        return original


def rebuild_layout_with_db_data(
    layout: MagazineLayout,
    enriched_content: EditorialContent,
    celebs: list[Celeb],
    products: list[Product],
) -> MagazineLayout:
    """Rebuild layout blocks with real DB IDs and details.

    Creates a deep copy to preserve input immutability.
    Builds name->model lookup maps (case-insensitive) for celeb and product matching.
    """
    new_layout = deepcopy(layout)

    # Build case-insensitive lookup maps
    celeb_map: dict[str, Celeb] = {c.name.lower(): c for c in celebs}
    product_map: dict[str, Product] = {p.name.lower(): p for p in products}

    for block in new_layout.blocks:
        if isinstance(block, CelebFeatureBlock):
            block.celebs = [
                CelebItem(
                    celeb_id=celeb_map[cm.name.lower()].id if cm.name.lower() in celeb_map else None,
                    name=cm.name,
                    image_url=(
                        celeb_map[cm.name.lower()].profile_image_url
                        if cm.name.lower() in celeb_map
                        else None
                    ),
                    description=cm.context,
                )
                for cm in enriched_content.celeb_mentions
            ]
        elif isinstance(block, ProductShowcaseBlock):
            block.products = [
                ProductItem(
                    product_id=(
                        product_map[pm.name.lower()].id
                        if pm.name.lower() in product_map
                        else None
                    ),
                    name=pm.name,
                    brand=pm.brand,
                    image_url=(
                        product_map[pm.name.lower()].image_url
                        if pm.name.lower() in product_map
                        else None
                    ),
                    description=pm.context,
                )
                for pm in enriched_content.product_mentions
            ]
        elif isinstance(block, BodyTextBlock):
            block.paragraphs = enriched_content.body_paragraphs

    return new_layout


async def enrich_editorial_content(layout: MagazineLayout) -> MagazineLayout:
    """Top-level orchestration: enrich a MagazineLayout with real DB data.

    Steps:
    1. Extract mention names from layout blocks
    2. Expand keywords via Gemini
    3. Search DB with mention names + expanded keywords
    4. If no DB results, return original layout unchanged (graceful passthrough)
    5. Re-generate content with DB context
    6. Rebuild layout with actual DB IDs
    """
    # 1. Extract mention names
    celeb_names = extract_celeb_names(layout)
    product_names = extract_product_names(layout)

    # 2. Expand keywords via Gemini
    client = get_genai_client()
    expanded = await expand_keywords(client, layout.keyword)

    # 3. Combine mention names + expanded keywords as search terms
    celeb_search_terms = celeb_names + expanded
    product_search_terms = product_names + expanded

    celebs = await search_celebs_multi(celeb_search_terms)
    products = await search_products_multi(product_search_terms)

    # 4. Graceful passthrough if no DB results
    if not celebs and not products:
        logger.info("No DB results found for keyword=%s, returning original layout", layout.keyword)
        return layout

    # 5. Build EditorialContent from current layout for re-generation context
    # Extract current content from layout blocks
    current_content = _extract_content_from_layout(layout)

    enriched_content = await regenerate_with_enrichment(
        client, current_content, celebs, products, layout.keyword
    )

    # 6. Rebuild layout with DB IDs
    return rebuild_layout_with_db_data(layout, enriched_content, celebs, products)


def _extract_content_from_layout(layout: MagazineLayout) -> EditorialContent:
    """Extract an EditorialContent from existing layout blocks for re-generation context."""
    from editorial_ai.models.editorial import CelebMention, ProductMention
    from editorial_ai.models.layout import (
        CreditsBlock,
        HashtagBarBlock,
        HeadlineBlock,
        HeroBlock,
        PullQuoteBlock,
    )

    title = layout.title
    subtitle = layout.subtitle
    body_paragraphs: list[str] = []
    pull_quotes: list[str] = []
    celeb_mentions: list[CelebMention] = []
    product_mentions: list[ProductMention] = []
    hashtags: list[str] = []
    credits: list = []

    for block in layout.blocks:
        if isinstance(block, HeroBlock):
            if block.overlay_title:
                title = block.overlay_title
            if block.overlay_subtitle:
                subtitle = block.overlay_subtitle
        elif isinstance(block, HeadlineBlock):
            if not title:
                title = block.text
        elif isinstance(block, BodyTextBlock):
            body_paragraphs.extend(block.paragraphs)
        elif isinstance(block, PullQuoteBlock):
            if block.quote:
                pull_quotes.append(block.quote)
        elif isinstance(block, CelebFeatureBlock):
            for c in block.celebs:
                celeb_mentions.append(
                    CelebMention(name=c.name, context=c.description or "")
                )
        elif isinstance(block, ProductShowcaseBlock):
            for p in block.products:
                product_mentions.append(
                    ProductMention(name=p.name, brand=p.brand, context=p.description or "")
                )
        elif isinstance(block, HashtagBarBlock):
            hashtags.extend(block.hashtags)
        elif isinstance(block, CreditsBlock):
            credits.extend(block.entries)

    return EditorialContent(
        keyword=layout.keyword,
        title=title,
        subtitle=subtitle,
        body_paragraphs=body_paragraphs or [""],
        pull_quotes=pull_quotes,
        celeb_mentions=celeb_mentions,
        product_mentions=product_mentions,
        hashtags=hashtags,
        credits=credits,
    )
