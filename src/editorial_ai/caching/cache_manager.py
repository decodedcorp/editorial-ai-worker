"""Context caching manager for Gemini API.

Wraps google-genai client.caches API with:
- get_or_create pattern (reuse existing cache within a pipeline run)
- Minimum token threshold check (2048 tokens)
- TTL-based lifecycle (3600s default)
- Fire-and-forget error handling (never breaks pipeline)
"""

from __future__ import annotations

import logging

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Minimum tokens for cache to be worthwhile (below this, implicit caching handles it)
MIN_CACHE_TOKENS = 2048
# Rough chars-to-tokens ratio for threshold estimation (conservative)
CHARS_PER_TOKEN_ESTIMATE = 4


class CacheManager:
    """Manages explicit context caches for pipeline LLM calls."""

    def __init__(self, client: genai.Client) -> None:
        self._client = client
        self._active_caches: dict[str, str] = {}  # cache_key -> cache.name

    async def get_or_create(
        self,
        cache_key: str,
        model: str,
        contents: list[types.Content] | str,
        *,
        system_instruction: str | None = None,
        ttl: str = "3600s",
    ) -> str | None:
        """Get existing cache or create new one. Returns cache name or None.

        Returns None if:
        - Content is below minimum token threshold
        - Cache creation fails (fire-and-forget)
        - Cache already expired and re-creation fails
        """
        try:
            # Estimate token count from content length
            content_chars = self._estimate_chars(contents)
            if content_chars < MIN_CACHE_TOKENS * CHARS_PER_TOKEN_ESTIMATE:
                logger.debug(
                    "Content below cache threshold (%d chars < %d min), skipping cache for key=%s",
                    content_chars,
                    MIN_CACHE_TOKENS * CHARS_PER_TOKEN_ESTIMATE,
                    cache_key,
                )
                return None

            # Check existing cache
            if cache_key in self._active_caches:
                try:
                    # Verify cache still exists (may have expired)
                    self._client.caches.get(name=self._active_caches[cache_key])
                    logger.debug("Reusing existing cache for key=%s", cache_key)
                    return self._active_caches[cache_key]
                except Exception:
                    logger.debug("Cached entry expired for key=%s, recreating", cache_key)
                    del self._active_caches[cache_key]

            # Normalize contents to list[Content]
            if isinstance(contents, str):
                content_list = [
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=contents)],
                    )
                ]
            else:
                content_list = contents

            # Create cache
            config = types.CreateCachedContentConfig(
                contents=content_list,
                display_name=cache_key,
                ttl=ttl,
            )
            if system_instruction:
                config.system_instruction = system_instruction

            cache = await self._client.aio.caches.create(
                model=model,
                config=config,
            )
            self._active_caches[cache_key] = cache.name
            logger.info("Created cache for key=%s, name=%s", cache_key, cache.name)
            return cache.name

        except Exception:
            logger.warning(
                "Cache creation failed for key=%s, proceeding without cache",
                cache_key,
                exc_info=True,
            )
            return None

    def _estimate_chars(self, contents: list[types.Content] | str) -> int:
        """Rough character count estimation for threshold check."""
        if isinstance(contents, str):
            return len(contents)
        total = 0
        for content in contents:
            if hasattr(content, "parts") and content.parts:
                for part in content.parts:
                    if hasattr(part, "text") and part.text:
                        total += len(part.text)
        return total

    def clear(self) -> None:
        """Clear active cache references (does not delete server-side caches -- TTL handles that)."""
        self._active_caches.clear()


_manager_instance: CacheManager | None = None


def get_cache_manager(client: genai.Client | None = None) -> CacheManager:
    """Get or create singleton CacheManager."""
    global _manager_instance  # noqa: PLW0603
    if _manager_instance is None:
        if client is None:
            from editorial_ai.services.curation_service import get_genai_client

            client = get_genai_client()
        _manager_instance = CacheManager(client)
    return _manager_instance
