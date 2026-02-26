"""DB source search endpoints for admin content creation.

Provides unified search across posts (with solutions), celebs, and products
so the admin can browse and select source data before triggering a pipeline.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query

from editorial_ai.api.deps import verify_api_key
from editorial_ai.services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.get("/search")
async def search_sources(
    q: str = Query(..., min_length=1, description="Search query"),
    type: str = Query("all", description="Source type: all, posts, celebs, products"),
    limit: int = Query(10, ge=1, le=50),
):
    """Unified search across DB source tables.

    Returns posts (with linked solutions + metadata), celebs, and products
    matching the query string.
    """
    client = await get_supabase_client()
    pattern = f"%{q}%"
    result: dict = {}

    if type in ("all", "posts"):
        result["posts"] = await _search_posts(client, pattern, limit)

    if type in ("all", "celebs"):
        result["celebs"] = await _search_celebs(client, pattern, limit)

    if type in ("all", "products"):
        result["products"] = await _search_products(client, pattern, limit)

    return result


@router.post("/resolve")
async def resolve_sources(body: dict):
    """Resolve selected source IDs into full enriched data for pipeline injection.

    Accepts:
        {
            "selected_posts": ["post-001", ...],
            "selected_celebs": ["celeb-001", ...],
            "selected_products": ["prod-001", ...],
            "category": "fashion"
        }

    Returns curated_topics and enriched_contexts ready for pipeline state.
    """
    client = await get_supabase_client()

    post_ids = body.get("selected_posts", [])
    celeb_ids = body.get("selected_celebs", [])
    product_ids = body.get("selected_products", [])
    category = body.get("category", "fashion")

    # Fetch full data for selected items
    posts_data = await _fetch_posts_by_ids(client, post_ids) if post_ids else []
    celebs_data = await _fetch_celebs_by_ids(client, celeb_ids) if celeb_ids else []
    products_data = await _fetch_products_by_ids(client, product_ids) if product_ids else []

    # Build curated_topics from selected data
    curated_topics = _build_curated_topics(posts_data, celebs_data, products_data, category)

    # Build enriched_contexts from posts + solutions
    enriched_contexts = posts_data  # Already includes solutions

    return {
        "curated_topics": curated_topics,
        "enriched_contexts": enriched_contexts,
        "summary": {
            "posts": len(posts_data),
            "celebs": len(celebs_data),
            "products": len(products_data),
        },
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _search_posts(client, pattern: str, limit: int) -> list[dict]:
    """Search posts with joined solutions and metadata."""
    try:
        response = await (
            client.table("posts")
            .select("id, image_url, media_type, title, artist_name, group_name, context, view_count, trending_score")
            .or_(
                f"artist_name.ilike.{pattern},"
                f"group_name.ilike.{pattern},"
                f"context.ilike.{pattern},"
                f"title.ilike.{pattern}"
            )
            .eq("status", "active")
            .order("trending_score", desc=True)
            .limit(limit)
            .execute()
        )
    except Exception:
        logger.warning("Failed to search posts with pattern: %s", pattern)
        return []

    posts = response.data or []

    # Enrich each post with solutions
    for post in posts:
        post["solutions"] = await _fetch_solutions_for_post(client, post["id"])

    return posts


async def _search_celebs(client, pattern: str, limit: int) -> list[dict]:
    """Search celebs by name, name_en, description."""
    try:
        response = await (
            client.table("celebs")
            .select("id, name, name_en, category, profile_image_url, description, tags")
            .or_(
                f"name.ilike.{pattern},"
                f"name_en.ilike.{pattern},"
                f"description.ilike.{pattern}"
            )
            .limit(limit)
            .execute()
        )
        return response.data or []
    except Exception:
        logger.warning("Failed to search celebs with pattern: %s", pattern)
        return []


async def _search_products(client, pattern: str, limit: int) -> list[dict]:
    """Search products by name, brand, description."""
    try:
        response = await (
            client.table("products")
            .select("id, name, brand, category, price, image_url, description, product_url, tags")
            .or_(
                f"name.ilike.{pattern},"
                f"brand.ilike.{pattern},"
                f"description.ilike.{pattern}"
            )
            .limit(limit)
            .execute()
        )
        return response.data or []
    except Exception:
        logger.warning("Failed to search products with pattern: %s", pattern)
        return []


async def _fetch_solutions_for_post(client, post_id: str) -> list[dict]:
    """Fetch solutions linked to a post via spots, with flattened metadata."""
    try:
        response = await (
            client.table("spots")
            .select("id, solutions(id, title, thumbnail_url, metadata, link_type, original_url)")
            .eq("post_id", post_id)
            .limit(10)
            .execute()
        )
    except Exception:
        return []

    solutions: list[dict] = []
    for spot in response.data or []:
        for sol in spot.get("solutions", []):
            metadata = sol.get("metadata") or {}
            solutions.append({
                "solution_id": sol.get("id"),
                "title": sol.get("title"),
                "thumbnail_url": sol.get("thumbnail_url"),
                "link_type": sol.get("link_type"),
                "original_url": sol.get("original_url"),
                # Flatten metadata for UI display
                "brand": metadata.get("brand"),
                "category": metadata.get("category"),
                "material": metadata.get("material"),
                "origin": metadata.get("origin"),
                "keywords": metadata.get("keywords", []),
            })
    return solutions


async def _fetch_posts_by_ids(client, post_ids: list[str]) -> list[dict]:
    """Fetch full post data + solutions for given IDs."""
    if not post_ids:
        return []
    try:
        response = await (
            client.table("posts")
            .select("id, image_url, media_type, title, artist_name, group_name, context, view_count, trending_score")
            .in_("id", post_ids)
            .execute()
        )
    except Exception:
        logger.warning("Failed to fetch posts by IDs")
        return []

    posts = response.data or []
    for post in posts:
        post["solutions"] = await _fetch_solutions_for_post(client, post["id"])
    return posts


async def _fetch_celebs_by_ids(client, celeb_ids: list[str]) -> list[dict]:
    """Fetch celebs by IDs."""
    if not celeb_ids:
        return []
    try:
        response = await (
            client.table("celebs")
            .select("id, name, name_en, category, profile_image_url, description, tags")
            .in_("id", celeb_ids)
            .execute()
        )
        return response.data or []
    except Exception:
        return []


async def _fetch_products_by_ids(client, product_ids: list[str]) -> list[dict]:
    """Fetch products by IDs."""
    if not product_ids:
        return []
    try:
        response = await (
            client.table("products")
            .select("id, name, brand, category, price, image_url, description, product_url, tags")
            .in_("id", product_ids)
            .execute()
        )
        return response.data or []
    except Exception:
        return []


def _build_curated_topics(
    posts: list[dict],
    celebs: list[dict],
    products: list[dict],
    category: str,
) -> list[dict]:
    """Build curated_topics structure from selected DB sources.

    Synthesizes posts, celebs, and products into the same format
    that the curation node would produce, so downstream nodes work unchanged.
    """
    # Extract unique keywords from all sources
    keywords: list[str] = []
    celebrities: list[dict] = []
    related_keywords: list[str] = []

    for post in posts:
        if post.get("artist_name"):
            keywords.append(post["artist_name"])
        if post.get("group_name") and post["group_name"] not in keywords:
            keywords.append(post["group_name"])
        if post.get("context"):
            related_keywords.append(post["context"])
        # Extract brand names from solutions
        for sol in post.get("solutions", []):
            if sol.get("brand") and sol["brand"] not in related_keywords:
                related_keywords.append(sol["brand"])

    for celeb in celebs:
        celebrities.append({
            "name": celeb.get("name", ""),
            "name_en": celeb.get("name_en", ""),
        })
        if celeb.get("name") and celeb["name"] not in keywords:
            keywords.append(celeb["name"])
        for tag in celeb.get("tags", []) or []:
            if tag not in related_keywords:
                related_keywords.append(tag)

    for product in products:
        if product.get("brand") and product["brand"] not in related_keywords:
            related_keywords.append(product["brand"])
        if product.get("name") and product["name"] not in related_keywords:
            related_keywords.append(product["name"])

    # Build a single topic combining all selected sources
    main_keyword = keywords[0] if keywords else category
    trend_parts = []
    if posts:
        artists = list({p.get("group_name") or p.get("artist_name", "") for p in posts})
        trend_parts.append(f"Selected {len(posts)} posts featuring {', '.join(artists[:3])}")
    if celebs:
        names = [c.get("name", "") for c in celebs]
        trend_parts.append(f"Featured celebs: {', '.join(names[:3])}")
    if products:
        brands = list({p.get("brand", "") for p in products if p.get("brand")})
        trend_parts.append(f"Products from {', '.join(brands[:3])}")

    return [{
        "keyword": main_keyword,
        "trend_background": ". ".join(trend_parts) if trend_parts else f"DB-sourced content for {category}",
        "related_keywords": related_keywords[:10],
        "celebrities": celebrities,
    }]
