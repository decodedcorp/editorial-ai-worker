"""Source node for the editorial pipeline graph.

Queries Supabase posts + spots + solutions based on curated keywords,
building rich context for the editorial node to use as real data source.
"""

from __future__ import annotations

import logging

from editorial_ai.services.supabase_client import get_supabase_client
from editorial_ai.state import EditorialPipelineState

logger = logging.getLogger(__name__)


async def source_node(state: EditorialPipelineState) -> dict:
    """LangGraph node: fetch posts data from Supabase using curated keywords.

    Reads curated_topics keywords, queries posts+spots+solutions,
    and writes enriched_contexts back to state for editorial generation.
    """
    curated_topics = state.get("curated_topics") or []
    if not curated_topics:
        return {
            "pipeline_status": "drafting",
            "enriched_contexts": [],
            "error_log": ["Source skipped: no curated_topics"],
        }

    # Collect search terms from curated topics
    # Also extract individual words and celebrity names for better DB matching
    search_terms: list[str] = []
    for topic in curated_topics:
        kw = topic.get("keyword", "")
        if kw:
            search_terms.append(kw)
        for rk in topic.get("related_keywords", []):
            if rk:
                search_terms.append(rk)
        # Extract celebrity names from curated data
        for celeb in topic.get("celebrities", []):
            name = celeb.get("name", "") if isinstance(celeb, dict) else str(celeb)
            if name:
                search_terms.append(name)

    # Split compound terms into individual words for better matching
    # e.g. "Jennie Effect" -> also search "Jennie", "Lisa's Kith" -> "Lisa"
    expanded: list[str] = []
    for term in search_terms:
        expanded.append(term)
        words = term.replace("'s", "").split()
        for w in words:
            # Only add single words that look like names (capitalized, 3+ chars)
            if len(w) >= 3 and w[0].isupper() and w.lower() not in (
                "the", "and", "for", "with", "from", "style", "fashion",
                "effect", "collection", "trend", "revival", "airport",
            ):
                expanded.append(w)
    search_terms = list(dict.fromkeys(expanded))  # dedupe, preserve order

    if not search_terms:
        return {
            "pipeline_status": "drafting",
            "enriched_contexts": [],
            "error_log": ["Source skipped: no search terms from curated_topics"],
        }

    try:
        contexts = await _fetch_posts_with_solutions(search_terms)
        logger.info(
            "Source node fetched %d post contexts for terms: %s",
            len(contexts),
            search_terms[:5],
        )
        return {
            "pipeline_status": "drafting",
            "enriched_contexts": contexts,
        }
    except Exception as e:  # noqa: BLE001
        logger.exception("Source node failed")
        return {
            "pipeline_status": "drafting",
            "enriched_contexts": [],
            "error_log": [f"Source failed: {type(e).__name__}: {e!s}"],
        }


async def _fetch_posts_with_solutions(
    search_terms: list[str],
    *,
    limit_per_term: int = 5,
    max_posts: int = 15,
) -> list[dict]:
    """Query posts matching search terms, join with spots+solutions.

    Search strategy:
    - artist_name ilike match
    - group_name ilike match
    - context ilike match
    Deduplicates by post_id, then fetches related spots+solutions.
    """
    client = await get_supabase_client()
    seen_ids: set[str] = set()
    all_posts: list[dict] = []

    for term in search_terms:
        if len(all_posts) >= max_posts:
            break

        pattern = f"%{term}%"
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
                .order("view_count", desc=True)
                .limit(limit_per_term)
                .execute()
            )
        except Exception:  # noqa: BLE001
            logger.warning("Failed to search posts for term: %s", term)
            continue

        for post in response.data:
            post_id = post["id"]
            if post_id in seen_ids:
                continue
            seen_ids.add(post_id)
            all_posts.append(post)

    # Fetch spots + solutions for collected posts
    contexts: list[dict] = []
    for post in all_posts[:max_posts]:
        post_id = post["id"]
        solutions = await _fetch_solutions_for_post(client, post_id)
        contexts.append({
            "post_id": post_id,
            "image_url": post.get("image_url"),
            "artist_name": post.get("artist_name"),
            "group_name": post.get("group_name"),
            "context": post.get("context"),
            "view_count": post.get("view_count", 0),
            "solutions": solutions,
        })

    return contexts


async def _fetch_solutions_for_post(client, post_id: str) -> list[dict]:
    """Fetch solutions linked to a post via spots."""
    try:
        response = await (
            client.table("spots")
            .select("id, solutions(id, title, thumbnail_url, metadata, link_type, original_url)")
            .eq("post_id", post_id)
            .limit(10)
            .execute()
        )
    except Exception:  # noqa: BLE001
        logger.warning("Failed to fetch spots/solutions for post: %s", post_id)
        return []

    solutions: list[dict] = []
    for spot in response.data:
        for sol in spot.get("solutions", []):
            solutions.append({
                "solution_id": sol.get("id"),
                "title": sol.get("title"),
                "thumbnail_url": sol.get("thumbnail_url"),
                "link_type": sol.get("link_type"),
                "original_url": sol.get("original_url"),
                "metadata": sol.get("metadata"),
            })
    return solutions
