"""Enrich node variant that uses posts/solutions data instead of celebs/products tables.

Replaces the original enrich node for the posts-based pipeline.
Takes enriched_contexts (from source node) and current_draft (from editorial node),
then injects real image URLs, product data, and artist info into the layout blocks.
"""

from __future__ import annotations

import logging
from copy import deepcopy

from editorial_ai.models.layout import (
    BodyTextBlock,
    CelebFeatureBlock,
    CelebItem,
    HeroBlock,
    ImageGalleryBlock,
    ImageItem,
    MagazineLayout,
    ProductItem,
    ProductShowcaseBlock,
)
from editorial_ai.state import EditorialPipelineState

logger = logging.getLogger(__name__)


async def enrich_from_posts_node(state: EditorialPipelineState) -> dict:
    """LangGraph node: enrich editorial draft with real posts/solutions data.

    Reads current_draft and enriched_contexts from state,
    injects real image URLs, artist info, and product data into layout blocks.
    """
    current_draft = state.get("current_draft")
    enriched_contexts = state.get("enriched_contexts") or []

    if not current_draft:
        return {"error_log": ["Enrich skipped: no current_draft in state"]}

    if not enriched_contexts:
        logger.info("No enriched_contexts, returning draft as-is")
        return {}

    try:
        layout = MagazineLayout.model_validate(current_draft)
        enriched = _inject_posts_data(layout, enriched_contexts)
        return {"current_draft": enriched.model_dump()}
    except Exception as e:  # noqa: BLE001
        logger.exception("Enrich from posts failed")
        return {"error_log": [f"Enrich failed: {type(e).__name__}: {e!s}"]}


def _inject_posts_data(
    layout: MagazineLayout,
    contexts: list[dict],
) -> MagazineLayout:
    """Inject real posts data into layout blocks.

    - HeroBlock: use the best post image
    - ImageGalleryBlock: fill with post images
    - CelebFeatureBlock: use artist_name + image from posts
    - ProductShowcaseBlock: use solutions metadata
    """
    new_layout = deepcopy(layout)

    # Collect real images and artist info
    post_images = _collect_post_images(contexts)
    artists = _collect_artists(contexts)
    products = _collect_products(contexts)

    hero_used = False
    gallery_filled = False

    for block in new_layout.blocks:
        if isinstance(block, HeroBlock) and not hero_used and post_images:
            # Use first (best) post image as hero
            best = post_images[0]
            block.image_url = best["url"]
            hero_used = True

        elif isinstance(block, ImageGalleryBlock) and not gallery_filled and len(post_images) > 1:
            block.images = [
                ImageItem(
                    url=img["url"],
                    alt=img.get("alt"),
                    caption=img.get("caption"),
                )
                for img in post_images[1:7]  # up to 6 gallery images
            ]
            gallery_filled = True

        elif isinstance(block, CelebFeatureBlock) and artists:
            block.celebs = [
                CelebItem(
                    name=a["name"],
                    image_url=a.get("image_url"),
                    description=a.get("description"),
                )
                for a in artists[:5]
            ]

        elif isinstance(block, ProductShowcaseBlock) and products:
            block.products = [
                ProductItem(
                    product_id=p.get("solution_id"),
                    name=p["name"],
                    brand=p.get("brand"),
                    image_url=p.get("thumbnail_url"),
                    link_url=p.get("original_url"),
                    description=p.get("description"),
                )
                for p in products[:6]
            ]

    return new_layout


def _collect_post_images(contexts: list[dict]) -> list[dict]:
    """Collect post images sorted by view_count (best first)."""
    images: list[dict] = []
    sorted_ctx = sorted(contexts, key=lambda c: c.get("view_count", 0), reverse=True)
    for ctx in sorted_ctx:
        if ctx.get("image_url"):
            artist = ctx.get("artist_name") or ""
            group = ctx.get("group_name") or ""
            caption = f"{artist} ({group})".strip(" ()") if artist or group else None
            images.append({
                "url": ctx["image_url"],
                "alt": f"{artist} fashion" if artist else "fashion",
                "caption": caption,
            })
    return images


def _collect_artists(contexts: list[dict]) -> list[dict]:
    """Collect unique artists from posts."""
    seen: set[str] = set()
    artists: list[dict] = []
    for ctx in contexts:
        name = ctx.get("artist_name")
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        group = ctx.get("group_name") or ""
        artists.append({
            "name": name,
            "image_url": ctx.get("image_url"),
            "description": f"{group} 멤버" if group else "아티스트",
        })
    return artists


def _collect_products(contexts: list[dict]) -> list[dict]:
    """Collect product info from solutions metadata."""
    products: list[dict] = []
    seen_ids: set[str] = set()
    for ctx in contexts:
        for sol in ctx.get("solutions", []):
            sol_id = sol.get("solution_id", "")
            if sol_id in seen_ids:
                continue
            seen_ids.add(sol_id)

            title = sol.get("title") or ""
            if not title:
                continue

            metadata = sol.get("metadata") or {}
            # Extract brand from metadata keywords if available
            keywords = metadata.get("keywords", [])
            brand = keywords[0] if keywords else None

            # Build description from Q&A if available
            qa_pairs = metadata.get("qa_pairs", [])
            description = qa_pairs[0].get("answer", "") if qa_pairs else ""

            products.append({
                "solution_id": sol_id,
                "name": title,
                "brand": brand,
                "thumbnail_url": sol.get("thumbnail_url"),
                "original_url": sol.get("original_url"),
                "description": description[:150] if description else None,
            })
    return products
