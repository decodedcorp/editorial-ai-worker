"""Unit tests for Supabase service layer with mocked client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from editorial_ai.models.celeb import Celeb
from editorial_ai.models.post import Post
from editorial_ai.models.product import Product
from editorial_ai.services.celeb_service import get_celeb_by_id, search_celebs
from editorial_ai.services.post_service import get_post_by_id, list_posts
from editorial_ai.services.product_service import get_product_by_id, search_products

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_CELEB = {
    "id": "celeb-1",
    "name": "김태희",
    "name_en": "Kim Tae-hee",
    "category": "actress",
    "profile_image_url": None,
    "description": "Korean actress",
    "tags": ["actress", "fashion"],
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": None,
}

SAMPLE_PRODUCT = {
    "id": "prod-1",
    "name": "Classic Trench Coat",
    "brand": "Burberry",
    "category": "outerwear",
    "price": 2500000,
    "image_url": None,
    "description": "Iconic trench coat",
    "product_url": "https://example.com/product/1",
    "tags": ["outerwear", "classic"],
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": None,
}

SAMPLE_POST = {
    "id": "post-1",
    "title": "Spring Fashion Trends 2025",
    "content": "Lorem ipsum",
    "status": "published",
    "celeb_id": "celeb-1",
    "thumbnail_url": None,
    "tags": ["spring", "trends"],
    "created_at": "2025-03-01T00:00:00Z",
    "updated_at": None,
    "published_at": "2025-03-01T12:00:00Z",
}


def _mock_response(data: dict | list | None) -> MagicMock:
    """Create a mock APIResponse with given data."""
    resp = MagicMock()
    resp.data = data
    return resp


def _build_mock_client(response_data: dict | list | None) -> MagicMock:
    """Build a mock Supabase AsyncClient with chainable query builder.

    The chain: client.table(...).select(...).eq(...).limit(...).execute()
    All builder methods return the same builder mock so chaining works.
    execute() is async and returns the mock response.

    Uses MagicMock (not AsyncMock) for the client because table() is synchronous.
    """
    mock_client = MagicMock()
    builder = MagicMock()

    # Make all builder methods return the builder itself (for chaining)
    builder.select.return_value = builder
    builder.eq.return_value = builder
    builder.ilike.return_value = builder
    builder.limit.return_value = builder
    builder.order.return_value = builder
    builder.maybe_single.return_value = builder

    # execute() is async and returns the response
    builder.execute = AsyncMock(return_value=_mock_response(response_data))

    mock_client.table.return_value = builder
    return mock_client


# ---------------------------------------------------------------------------
# Celeb service tests
# ---------------------------------------------------------------------------


@patch("editorial_ai.services.celeb_service.get_supabase_client")
async def test_get_celeb_by_id_found(mock_get_client: AsyncMock) -> None:
    mock_get_client.return_value = _build_mock_client(SAMPLE_CELEB)
    result = await get_celeb_by_id("celeb-1")
    assert result is not None
    assert isinstance(result, Celeb)
    assert result.id == "celeb-1"
    assert result.name == "김태희"


@patch("editorial_ai.services.celeb_service.get_supabase_client")
async def test_get_celeb_by_id_not_found(mock_get_client: AsyncMock) -> None:
    mock_get_client.return_value = _build_mock_client(None)
    result = await get_celeb_by_id("nonexistent")
    assert result is None


@patch("editorial_ai.services.celeb_service.get_supabase_client")
async def test_search_celebs_returns_list(mock_get_client: AsyncMock) -> None:
    mock_get_client.return_value = _build_mock_client([SAMPLE_CELEB])
    results = await search_celebs("김")
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0].name == "김태희"


@patch("editorial_ai.services.celeb_service.get_supabase_client")
async def test_search_celebs_empty(mock_get_client: AsyncMock) -> None:
    mock_get_client.return_value = _build_mock_client([])
    results = await search_celebs("xyz")
    assert results == []


# ---------------------------------------------------------------------------
# Product service tests
# ---------------------------------------------------------------------------


@patch("editorial_ai.services.product_service.get_supabase_client")
async def test_get_product_by_id_found(mock_get_client: AsyncMock) -> None:
    mock_get_client.return_value = _build_mock_client(SAMPLE_PRODUCT)
    result = await get_product_by_id("prod-1")
    assert result is not None
    assert isinstance(result, Product)
    assert result.brand == "Burberry"


@patch("editorial_ai.services.product_service.get_supabase_client")
async def test_get_product_by_id_not_found(mock_get_client: AsyncMock) -> None:
    mock_get_client.return_value = _build_mock_client(None)
    result = await get_product_by_id("nonexistent")
    assert result is None


@patch("editorial_ai.services.product_service.get_supabase_client")
async def test_search_products_returns_list(mock_get_client: AsyncMock) -> None:
    mock_get_client.return_value = _build_mock_client([SAMPLE_PRODUCT])
    results = await search_products("Trench")
    assert len(results) == 1
    assert results[0].name == "Classic Trench Coat"


@patch("editorial_ai.services.product_service.get_supabase_client")
async def test_search_products_empty(mock_get_client: AsyncMock) -> None:
    mock_get_client.return_value = _build_mock_client([])
    results = await search_products("nonexistent")
    assert results == []


# ---------------------------------------------------------------------------
# Post service tests
# ---------------------------------------------------------------------------


@patch("editorial_ai.services.post_service.get_supabase_client")
async def test_get_post_by_id_found(mock_get_client: AsyncMock) -> None:
    mock_get_client.return_value = _build_mock_client(SAMPLE_POST)
    result = await get_post_by_id("post-1")
    assert result is not None
    assert isinstance(result, Post)
    assert result.title == "Spring Fashion Trends 2025"


@patch("editorial_ai.services.post_service.get_supabase_client")
async def test_get_post_by_id_not_found(mock_get_client: AsyncMock) -> None:
    mock_get_client.return_value = _build_mock_client(None)
    result = await get_post_by_id("nonexistent")
    assert result is None


@patch("editorial_ai.services.post_service.get_supabase_client")
async def test_list_posts_returns_list(mock_get_client: AsyncMock) -> None:
    mock_get_client.return_value = _build_mock_client([SAMPLE_POST])
    results = await list_posts(limit=5)
    assert len(results) == 1
    assert results[0].status == "published"


@patch("editorial_ai.services.post_service.get_supabase_client")
async def test_list_posts_empty(mock_get_client: AsyncMock) -> None:
    mock_get_client.return_value = _build_mock_client([])
    results = await list_posts()
    assert results == []


# ---------------------------------------------------------------------------
# Integration test stubs (require live Supabase — run with: uv run pytest -m integration)
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_search_celebs_integration() -> None:
    """Read-only test against real Supabase. Run manually with: uv run pytest -m integration"""
    results = await search_celebs("김", limit=5)
    assert isinstance(results, list)


@pytest.mark.integration
async def test_search_products_integration() -> None:
    """Read-only test against real Supabase."""
    results = await search_products("코트", limit=5)
    assert isinstance(results, list)


@pytest.mark.integration
async def test_list_posts_integration() -> None:
    """Read-only test against real Supabase."""
    results = await list_posts(limit=5)
    assert isinstance(results, list)
