"""Curation service using native google-genai SDK with Google Search Grounding.

Two-step Gemini pattern:
1. Grounded research call — uses Google Search tool for real-time data
2. Structured extraction call — parses research into CuratedTopic JSON

Uses the native google-genai SDK (NOT langchain-google-genai) for direct
access to grounding metadata and search tool configuration.
"""

import json
import logging
import re

from google import genai
from google.genai import errors, types
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from editorial_ai.config import settings
from editorial_ai.models.curation import CuratedTopic, CurationResult, GroundingSource
from editorial_ai.prompts.curation import (
    build_extraction_prompt,
    build_subtopic_expansion_prompt,
    build_trend_research_prompt,
)

logger = logging.getLogger(__name__)

# Retry decorator for Gemini API calls
retry_on_api_error = retry(
    retry=retry_if_exception_type((errors.ClientError, errors.ServerError)),
    wait=wait_exponential(multiplier=1, min=1, max=60),
    stop=stop_after_attempt(3),
    reraise=True,
)


def get_genai_client() -> genai.Client:
    """Create a google-genai Client using project settings.

    When GOOGLE_GENAI_USE_VERTEXAI is True, uses Vertex AI with ADC.
    Otherwise falls back to Gemini Developer API with API key.
    """
    if settings.google_genai_use_vertexai:
        return genai.Client(
            vertexai=True,
            project=settings.gcp_project_id,
            location=settings.gcp_location,
        )
    if settings.google_api_key is None:
        raise ValueError("GOOGLE_API_KEY required for curation service")
    return genai.Client(api_key=settings.google_api_key)


def _strip_markdown_fences(text: str) -> str:
    """Strip markdown code fences (```json ... ```) from response text."""
    stripped = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
    stripped = re.sub(r"\n?```\s*$", "", stripped)
    return stripped.strip()


def _extract_grounding_sources(response: types.GenerateContentResponse) -> list[GroundingSource]:
    """Extract grounding source URLs from Gemini response metadata.

    Safely navigates the nested metadata structure with None checks at each level.
    """
    sources: list[GroundingSource] = []
    try:
        candidates = response.candidates
        if not candidates:
            return sources
        candidate = candidates[0]
        metadata = candidate.grounding_metadata
        if metadata is None:
            return sources
        chunks = metadata.grounding_chunks
        if not chunks:
            return sources
        for chunk in chunks:
            if chunk.web is not None:
                sources.append(
                    GroundingSource(
                        url=chunk.web.uri or "",
                        title=chunk.web.title,
                    )
                )
    except (AttributeError, IndexError):
        logger.warning("Failed to extract grounding sources from response metadata")
    return sources


class CurationService:
    """Service for curating fashion trend topics using Gemini + Google Search Grounding.

    Implements a two-step pattern:
    1. Grounded research call for real-time trend data
    2. Structured JSON extraction from research text
    """

    def __init__(
        self,
        client: genai.Client,
        *,
        model: str | None = None,
        relevance_threshold: float = 0.6,
    ) -> None:
        self.client = client
        self.model = model or settings.default_model
        self.relevance_threshold = relevance_threshold

    @retry_on_api_error
    async def research_trend(
        self, keyword: str, *, db_context: str = ""
    ) -> tuple[str, list[GroundingSource]]:
        """Step 1: Grounded Gemini call for trend research.

        Returns the raw research text and extracted grounding source URLs.
        When db_context is provided, it's injected into the prompt so the model
        anchors its research to available DB data.
        """
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=build_trend_research_prompt(keyword, db_context=db_context),
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.7,
            ),
        )
        text = response.text or ""
        sources = _extract_grounding_sources(response)
        return text, sources

    @retry_on_api_error
    async def expand_subtopics(self, keyword: str, trend_background: str) -> list[str]:
        """Extract sub-topic keywords from initial research.

        Returns a list of 3-7 sub-topic keyword strings.
        """
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=build_subtopic_expansion_prompt(keyword, trend_background),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3,
            ),
        )
        try:
            raw_text = response.text or "[]"
            subtopics = json.loads(_strip_markdown_fences(raw_text))
            if not isinstance(subtopics, list):
                logger.warning("Subtopic response is not a list, returning empty")
                return []
            # Cap at 7 sub-topics
            return [str(s) for s in subtopics[:7]]
        except (json.JSONDecodeError, TypeError):
            logger.warning("Failed to parse subtopic JSON response")
            return []

    @retry_on_api_error
    async def extract_topic(
        self,
        keyword: str,
        raw_research: str,
        sources: list[GroundingSource],
    ) -> CuratedTopic:
        """Step 2: Structured JSON extraction from grounded research text.

        Parses the research text into a CuratedTopic model. Falls back to
        low_quality=True with defaults if parsing fails.
        """
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=build_extraction_prompt(keyword, raw_research),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
        raw_text = response.text or "{}"
        # Try parsing, with markdown fence fallback
        for text_candidate in [raw_text, _strip_markdown_fences(raw_text)]:
            try:
                topic = CuratedTopic.model_validate_json(text_candidate)
                # Attach grounding sources (override any parsed sources)
                topic.sources = sources
                return topic
            except Exception:  # noqa: BLE001
                continue

        # All parsing attempts failed — return low-quality fallback
        logger.warning("Failed to parse CuratedTopic JSON for keyword=%s, using fallback", keyword)
        return CuratedTopic(
            keyword=keyword,
            trend_background=raw_research[:500],
            related_keywords=[],
            celebrities=[],
            brands_products=[],
            seasonality="unknown",
            sources=sources,
            relevance_score=0.3,
            low_quality=True,
        )

    async def curate_topic(self, keyword: str) -> CuratedTopic | None:
        """Full pipeline for one topic: research_trend -> extract_topic.

        Returns None if the pipeline fails completely.
        """
        try:
            raw_research, sources = await self.research_trend(keyword)
            topic = await self.extract_topic(keyword, raw_research, sources)
            # Mark as low quality if no grounding sources
            if not sources:
                topic.low_quality = True
            return topic
        except Exception:  # noqa: BLE001
            logger.exception("curate_topic failed for keyword=%s", keyword)
            return None

    async def curate_seed(self, seed_keyword: str) -> CurationResult:
        """Entry point for the LangGraph curation node.

        1. Fetch DB context (available artists/brands) for grounded research
        2. Research the seed keyword for initial background
        3. Expand into sub-topic keywords
        4. Curate each keyword (seed + sub-topics) sequentially
        5. Filter by relevance threshold
        6. Return aggregated CurationResult
        """
        # Step 0: Build DB context for prompt grounding
        db_context = await _build_db_context()

        # Step 1: Initial research on seed keyword
        raw_research, seed_sources = await self.research_trend(
            seed_keyword, db_context=db_context
        )

        # Step 2: Expand sub-topics
        subtopics = await self.expand_subtopics(seed_keyword, raw_research)

        # Step 3: Curate each keyword sequentially (avoid rate limits)
        all_keywords = [seed_keyword] + subtopics
        raw_topics: list[CuratedTopic] = []

        for kw in all_keywords:
            if kw == seed_keyword:
                # Use already-fetched research for seed keyword
                topic = await self.extract_topic(kw, raw_research, seed_sources)
                if not seed_sources:
                    topic.low_quality = True
                raw_topics.append(topic)
            else:
                # Full pipeline for sub-topics
                sub_topic = await self.curate_topic(kw)
                if sub_topic is not None:
                    raw_topics.append(sub_topic)

        # Step 4: Filter by relevance threshold
        total_generated = len(raw_topics)
        filtered_topics = [
            t for t in raw_topics if t.relevance_score >= self.relevance_threshold
        ]

        return CurationResult(
            seed_keyword=seed_keyword,
            topics=filtered_topics,
            total_generated=total_generated,
            total_filtered=len(filtered_topics),
        )


async def _build_db_context() -> str:
    """Build a summary of available DB data for curation prompt grounding.

    Queries posts and solutions to provide artists, groups, and top brands
    so the AI researches trends relevant to our actual content.
    """
    try:
        from editorial_ai.services.supabase_client import get_supabase_client

        client = await get_supabase_client()

        # Get artist/group distribution
        artists_resp = await (
            client.table("posts")
            .select("artist_name, group_name")
            .eq("status", "active")
            .not_.is_("artist_name", "null")
            .limit(500)
            .execute()
        )

        # Count by group and artist
        group_artists: dict[str, set[str]] = {}
        for row in artists_resp.data:
            group = row.get("group_name") or "Solo"
            artist = row.get("artist_name", "")
            if artist:
                group_artists.setdefault(group, set()).add(artist)

        # Get top brands from solutions
        brands_resp = await (
            client.table("solutions")
            .select("title")
            .not_.is_("title", "null")
            .neq("title", "")
            .limit(200)
            .execute()
        )

        brand_counts: dict[str, int] = {}
        for row in brands_resp.data:
            title = row.get("title", "")
            # Extract first word as brand approximation
            brand = title.split(" ")[0] if title else ""
            if len(brand) > 2:
                brand_counts[brand] = brand_counts.get(brand, 0) + 1

        top_brands = sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        # Build context string
        lines = ["아티스트/그룹:"]
        for group, artists in sorted(group_artists.items(), key=lambda x: len(x[1]), reverse=True):
            artists_str = ", ".join(sorted(artists))
            lines.append(f"  - {group}: {artists_str}")

        lines.append(f"\n주요 브랜드 (상품 {len(brands_resp.data)}건):")
        for brand, count in top_brands:
            lines.append(f"  - {brand} ({count}건)")

        lines.append(f"\n총 포스트: {len(artists_resp.data)}건 (street style 중심)")

        return "\n".join(lines)
    except Exception:  # noqa: BLE001
        logger.warning("Failed to build DB context for curation, proceeding without it")
        return ""
