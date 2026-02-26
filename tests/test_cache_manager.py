"""Tests for CacheManager: get_or_create, threshold, key scoping, error handling."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.genai import types

from editorial_ai.caching.cache_manager import (
    CHARS_PER_TOKEN_ESTIMATE,
    MIN_CACHE_TOKENS,
    CacheManager,
)


@pytest.fixture
def mock_client():
    """Create a mock google-genai Client with caches API."""
    client = MagicMock()
    # Sync caches API
    client.caches = MagicMock()
    # Async caches API
    client.aio = MagicMock()
    client.aio.caches = MagicMock()
    client.aio.caches.create = AsyncMock()
    return client


@pytest.fixture
def cache_manager(mock_client):
    return CacheManager(mock_client)


def _long_content(n_chars: int = 20000) -> str:
    """Generate content exceeding the minimum token threshold."""
    return "x" * n_chars


class TestGetOrCreateBelowThreshold:
    @pytest.mark.asyncio
    async def test_short_string_returns_none(self, cache_manager):
        """Content below MIN_CACHE_TOKENS * CHARS_PER_TOKEN_ESTIMATE returns None."""
        short = "a" * (MIN_CACHE_TOKENS * CHARS_PER_TOKEN_ESTIMATE - 1)
        result = await cache_manager.get_or_create(
            cache_key="test-key",
            model="gemini-2.0-flash",
            contents=short,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_short_content_list_returns_none(self, cache_manager):
        """Content list below threshold returns None."""
        short_text = "a" * 100
        content_list = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=short_text)],
            )
        ]
        result = await cache_manager.get_or_create(
            cache_key="test-key",
            model="gemini-2.0-flash",
            contents=content_list,
        )
        assert result is None


class TestGetOrCreateCreatesCache:
    @pytest.mark.asyncio
    async def test_creates_cache_and_returns_name(self, cache_manager, mock_client):
        """Sufficient content creates cache and returns cache name."""
        mock_cache = MagicMock()
        mock_cache.name = "cachedContents/abc123"
        mock_client.aio.caches.create.return_value = mock_cache

        result = await cache_manager.get_or_create(
            cache_key="test-key",
            model="gemini-2.0-flash",
            contents=_long_content(),
        )
        assert result == "cachedContents/abc123"
        mock_client.aio.caches.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_creates_cache_with_system_instruction(self, cache_manager, mock_client):
        """System instruction is set on config when provided."""
        mock_cache = MagicMock()
        mock_cache.name = "cachedContents/abc123"
        mock_client.aio.caches.create.return_value = mock_cache

        result = await cache_manager.get_or_create(
            cache_key="test-key",
            model="gemini-2.0-flash",
            contents=_long_content(),
            system_instruction="You are a reviewer.",
        )
        assert result == "cachedContents/abc123"


class TestGetOrCreateReusesExisting:
    @pytest.mark.asyncio
    async def test_second_call_reuses_cached(self, cache_manager, mock_client):
        """Second call with same key returns cached name without creating."""
        mock_cache = MagicMock()
        mock_cache.name = "cachedContents/abc123"
        mock_client.aio.caches.create.return_value = mock_cache
        # First call creates
        mock_client.caches.get.return_value = mock_cache

        content = _long_content()
        await cache_manager.get_or_create(
            cache_key="test-key", model="gemini-2.0-flash", contents=content
        )
        # Second call reuses
        result = await cache_manager.get_or_create(
            cache_key="test-key", model="gemini-2.0-flash", contents=content
        )
        assert result == "cachedContents/abc123"
        # create called only once (first time)
        assert mock_client.aio.caches.create.call_count == 1
        # get called once to verify existing cache
        mock_client.caches.get.assert_called_once_with(name="cachedContents/abc123")


class TestGetOrCreateRecreatesExpired:
    @pytest.mark.asyncio
    async def test_expired_cache_recreates(self, cache_manager, mock_client):
        """If cache.get fails (expired), creates a new one."""
        mock_cache = MagicMock()
        mock_cache.name = "cachedContents/first"
        mock_client.aio.caches.create.return_value = mock_cache

        content = _long_content()
        # First call creates
        await cache_manager.get_or_create(
            cache_key="test-key", model="gemini-2.0-flash", contents=content
        )

        # Simulate expiration: get raises
        mock_client.caches.get.side_effect = Exception("404 Not Found")
        new_cache = MagicMock()
        new_cache.name = "cachedContents/second"
        mock_client.aio.caches.create.return_value = new_cache

        result = await cache_manager.get_or_create(
            cache_key="test-key", model="gemini-2.0-flash", contents=content
        )
        assert result == "cachedContents/second"
        assert mock_client.aio.caches.create.call_count == 2


class TestGetOrCreateFireAndForget:
    @pytest.mark.asyncio
    async def test_creation_exception_returns_none(self, cache_manager, mock_client):
        """Cache creation exception returns None (doesn't raise)."""
        mock_client.aio.caches.create.side_effect = Exception("API error")

        result = await cache_manager.get_or_create(
            cache_key="test-key",
            model="gemini-2.0-flash",
            contents=_long_content(),
        )
        assert result is None


class TestEstimateChars:
    def test_string_input(self, cache_manager):
        """String input returns len."""
        assert cache_manager._estimate_chars("hello") == 5

    def test_content_list(self, cache_manager):
        """Content list sums part text lengths."""
        content_list = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text="hello"),
                    types.Part.from_text(text="world"),
                ],
            ),
            types.Content(
                role="user",
                parts=[types.Part.from_text(text="foo")],
            ),
        ]
        assert cache_manager._estimate_chars(content_list) == 13  # 5+5+3


class TestClear:
    @pytest.mark.asyncio
    async def test_clear_resets_active(self, cache_manager, mock_client):
        """Clear empties active caches, forcing re-creation on next call."""
        mock_cache = MagicMock()
        mock_cache.name = "cachedContents/abc123"
        mock_client.aio.caches.create.return_value = mock_cache

        content = _long_content()
        await cache_manager.get_or_create(
            cache_key="test-key", model="gemini-2.0-flash", contents=content
        )

        cache_manager.clear()

        # After clear, next call should create (not reuse)
        new_cache = MagicMock()
        new_cache.name = "cachedContents/new123"
        mock_client.aio.caches.create.return_value = new_cache

        result = await cache_manager.get_or_create(
            cache_key="test-key", model="gemini-2.0-flash", contents=content
        )
        assert result == "cachedContents/new123"
        assert mock_client.aio.caches.create.call_count == 2
