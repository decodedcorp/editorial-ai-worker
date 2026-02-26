"""Curation node for the editorial pipeline graph.

Thin wrapper around CurationService: reads seed keyword from state,
calls the service, writes structured results back to state.
"""

from __future__ import annotations

import json
import logging
import re

from google.genai import types

from editorial_ai.observability import record_token_usage
from editorial_ai.routing import get_model_router
from editorial_ai.services.curation_service import CurationService, get_genai_client
from editorial_ai.state import EditorialPipelineState

logger = logging.getLogger(__name__)


async def _expand_keyword_for_db(keyword: str) -> dict:
    """Use LLM to expand a seed keyword into DB-optimized search terms.

    Returns a synthetic CuratedTopic dict with expanded search keywords,
    celebrity references, and brand references extracted from the LLM response.
    """
    client = get_genai_client()
    decision = get_model_router().resolve("curation_db_expand")

    prompt = (
        "You are a search query expander for a K-pop/fashion database.\n"
        f'Given the keyword "{keyword}", generate a JSON object with:\n'
        '- "search_keywords": list of 5-10 specific search terms optimized for DB text search\n'
        "  (include: celeb names, group names, brand names, style terms, Korean equivalents)\n"
        '- "category_hints": list of relevant categories\n'
        '- "celeb_names": list of celebrity/artist names mentioned\n'
        '- "brand_names": list of brand names mentioned\n\n'
        "Focus on terms that would match artist_name, group_name, title, context fields in a posts table,\n"
        "and product names/brands in a solutions table.\n\n"
        "Return ONLY valid JSON."
    )

    response = await client.aio.models.generate_content(
        model=decision.model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.3,
        ),
    )

    if hasattr(response, "usage_metadata") and response.usage_metadata:
        record_token_usage(
            prompt_tokens=getattr(response.usage_metadata, "prompt_token_count", 0) or 0,
            completion_tokens=getattr(response.usage_metadata, "candidates_token_count", 0) or 0,
            total_tokens=getattr(response.usage_metadata, "total_token_count", 0) or 0,
            model_name=decision.model,
            routing_reason=decision.reason,
        )

    raw_text = response.text or "{}"
    # Strip markdown fences if present
    stripped = re.sub(r"^```(?:json)?\s*\n?", "", raw_text.strip())
    stripped = re.sub(r"\n?```\s*$", "", stripped)
    data = json.loads(stripped.strip())

    search_keywords = data.get("search_keywords", [keyword])
    celeb_names = data.get("celeb_names", [])
    brand_names = data.get("brand_names", [])

    return {
        "keyword": keyword,
        "related_keywords": search_keywords,
        "celebrities": [{"name": n, "relevance": "AI-expanded"} for n in celeb_names],
        "brands_products": [{"name": n, "relevance": "AI-expanded"} for n in brand_names],
        "trend_background": f"AI-expanded DB search for: {keyword}",
        "seasonality": "current",
        "relevance_score": 1.0,
        "sources": [],
        "low_quality": False,
    }


def _fallback_topic(keyword: str) -> dict:
    """Create a minimal CuratedTopic dict from raw keyword splits."""
    parts = keyword.replace(",", " ").split()
    return {
        "keyword": keyword,
        "related_keywords": [keyword] + [p for p in parts if len(p) >= 2],
        "celebrities": [],
        "brands_products": [],
        "trend_background": f"Keyword-based DB search for: {keyword}",
        "seasonality": "current",
        "relevance_score": 1.0,
        "sources": [],
        "low_quality": True,
    }


async def curation_node(state: EditorialPipelineState) -> dict:
    """LangGraph node: curate trending topics from a seed keyword.

    Reads state["curation_input"]["seed_keyword"], calls CurationService.curate_seed(),
    and writes curated_topics + pipeline_status back to state.
    """
    curation_input = state.get("curation_input") or {}

    # DB Source mode: curation already done at trigger time, skip LLM call
    if curation_input.get("mode") == "db_source":
        logger.info("Curation skipped: db_source mode, topics pre-populated")
        return {"pipeline_status": "sourcing"}

    keyword = curation_input.get("seed_keyword") or curation_input.get("keyword")

    if not keyword:
        return {
            "pipeline_status": "failed",
            "error_log": ["Curation failed: no seed keyword provided in curation_input"],
        }

    # AI DB Search mode: expand keyword into DB search terms via lightweight LLM call
    if curation_input.get("mode") == "ai_db_search":
        try:
            topic_dict = await _expand_keyword_for_db(keyword)
            logger.info(
                "AI DB Search: expanded '%s' into %d search terms",
                keyword,
                len(topic_dict.get("related_keywords", [])),
            )
            return {
                "pipeline_status": "sourcing",
                "curated_topics": [topic_dict],
            }
        except Exception as e:  # noqa: BLE001
            logger.exception("AI DB Search expansion failed for keyword=%s, using fallback", keyword)
            return {
                "pipeline_status": "sourcing",
                "curated_topics": [_fallback_topic(keyword)],
            }

    try:
        service = CurationService(get_genai_client())
        result = await service.curate_seed(keyword)
        return {
            "pipeline_status": "sourcing",
            "curated_topics": [t.model_dump() for t in result.topics],
        }
    except Exception as e:  # noqa: BLE001
        logger.exception("Curation node failed for keyword=%s", keyword)
        return {
            "pipeline_status": "failed",
            "error_log": [f"Curation failed: {type(e).__name__}: {e!s}"],
            "curated_topics": [],
        }
