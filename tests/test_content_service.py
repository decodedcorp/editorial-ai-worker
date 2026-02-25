"""Unit tests for content_service with mocked Supabase client."""

from unittest.mock import AsyncMock, MagicMock, patch

from editorial_ai.services.content_service import (
    get_content_by_id,
    get_content_by_thread_id,
    list_contents_by_status,
    save_pending_content,
    update_content_status,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_CONTENT = {
    "id": "content-uuid-1",
    "thread_id": "thread-abc",
    "status": "pending",
    "title": "Spring Fashion Trends",
    "keyword": "spring fashion",
    "layout_json": {"title": "Spring Fashion Trends", "blocks": []},
    "review_summary": "All criteria passed.",
    "rejection_reason": None,
    "admin_feedback": None,
    "created_at": "2026-02-25T00:00:00Z",
    "updated_at": "2026-02-25T00:00:00Z",
    "published_at": None,
}


def _mock_response(data: dict | list | None) -> MagicMock:
    """Create a mock APIResponse with given data."""
    resp = MagicMock()
    resp.data = data
    return resp


def _build_mock_client(response_data: dict | list | None) -> MagicMock:
    """Build a mock Supabase AsyncClient with chainable query builder."""
    mock_client = MagicMock()
    builder = MagicMock()

    # All builder methods return the builder for chaining
    builder.select.return_value = builder
    builder.eq.return_value = builder
    builder.limit.return_value = builder
    builder.order.return_value = builder
    builder.maybe_single.return_value = builder
    builder.upsert.return_value = builder
    builder.update.return_value = builder

    # execute() is async
    builder.execute = AsyncMock(return_value=_mock_response(response_data))

    mock_client.table.return_value = builder
    return mock_client


# ---------------------------------------------------------------------------
# save_pending_content
# ---------------------------------------------------------------------------


@patch("editorial_ai.services.content_service.get_supabase_client")
async def test_save_pending_content_creates_upsert(mock_get_client: AsyncMock) -> None:
    mock_client = _build_mock_client([SAMPLE_CONTENT])
    mock_get_client.return_value = mock_client

    result = await save_pending_content(
        thread_id="thread-abc",
        layout_json={"title": "Spring Fashion Trends", "blocks": []},
        title="Spring Fashion Trends",
        keyword="spring fashion",
        review_summary="All criteria passed.",
    )

    # Verify upsert was called with correct payload
    builder = mock_client.table.return_value
    builder.upsert.assert_called_once()
    call_args = builder.upsert.call_args
    payload = call_args[0][0]
    assert payload["thread_id"] == "thread-abc"
    assert payload["status"] == "pending"
    assert payload["title"] == "Spring Fashion Trends"
    assert payload["keyword"] == "spring fashion"
    assert payload["review_summary"] == "All criteria passed."
    assert call_args[1]["on_conflict"] == "thread_id"
    assert result == SAMPLE_CONTENT


# ---------------------------------------------------------------------------
# update_content_status
# ---------------------------------------------------------------------------


@patch("editorial_ai.services.content_service.get_supabase_client")
async def test_update_content_status_approved(mock_get_client: AsyncMock) -> None:
    approved = {**SAMPLE_CONTENT, "status": "approved"}
    mock_client = _build_mock_client([approved])
    mock_get_client.return_value = mock_client

    result = await update_content_status("content-uuid-1", "approved")

    builder = mock_client.table.return_value
    builder.update.assert_called_once()
    update_data = builder.update.call_args[0][0]
    assert update_data["status"] == "approved"
    assert "published_at" not in update_data
    assert result == approved


@patch("editorial_ai.services.content_service.get_supabase_client")
async def test_update_content_status_rejected_includes_reason(
    mock_get_client: AsyncMock,
) -> None:
    rejected = {**SAMPLE_CONTENT, "status": "rejected", "rejection_reason": "Low quality"}
    mock_client = _build_mock_client([rejected])
    mock_get_client.return_value = mock_client

    result = await update_content_status(
        "content-uuid-1", "rejected", rejection_reason="Low quality"
    )

    builder = mock_client.table.return_value
    update_data = builder.update.call_args[0][0]
    assert update_data["status"] == "rejected"
    assert update_data["rejection_reason"] == "Low quality"
    assert result == rejected


@patch("editorial_ai.services.content_service.get_supabase_client")
async def test_update_content_status_published_sets_published_at(
    mock_get_client: AsyncMock,
) -> None:
    published = {**SAMPLE_CONTENT, "status": "published"}
    mock_client = _build_mock_client([published])
    mock_get_client.return_value = mock_client

    result = await update_content_status("content-uuid-1", "published")

    builder = mock_client.table.return_value
    update_data = builder.update.call_args[0][0]
    assert update_data["status"] == "published"
    assert update_data["published_at"] == "now()"
    assert result == published


# ---------------------------------------------------------------------------
# list_contents_by_status
# ---------------------------------------------------------------------------


@patch("editorial_ai.services.content_service.get_supabase_client")
async def test_list_contents_by_status_passes_filter(
    mock_get_client: AsyncMock,
) -> None:
    mock_client = _build_mock_client([SAMPLE_CONTENT])
    mock_get_client.return_value = mock_client

    results = await list_contents_by_status("pending")

    builder = mock_client.table.return_value
    builder.eq.assert_called_with("status", "pending")
    assert len(results) == 1
    assert results[0] == SAMPLE_CONTENT


# ---------------------------------------------------------------------------
# get_content_by_thread_id
# ---------------------------------------------------------------------------


@patch("editorial_ai.services.content_service.get_supabase_client")
async def test_get_content_by_thread_id_found(mock_get_client: AsyncMock) -> None:
    mock_client = _build_mock_client(SAMPLE_CONTENT)
    mock_get_client.return_value = mock_client

    result = await get_content_by_thread_id("thread-abc")

    builder = mock_client.table.return_value
    builder.eq.assert_called_with("thread_id", "thread-abc")
    assert result == SAMPLE_CONTENT


@patch("editorial_ai.services.content_service.get_supabase_client")
async def test_get_content_by_thread_id_not_found(mock_get_client: AsyncMock) -> None:
    mock_client = _build_mock_client(None)
    mock_get_client.return_value = mock_client

    result = await get_content_by_thread_id("nonexistent")
    assert result is None


# ---------------------------------------------------------------------------
# get_content_by_id
# ---------------------------------------------------------------------------


@patch("editorial_ai.services.content_service.get_supabase_client")
async def test_get_content_by_id_found(mock_get_client: AsyncMock) -> None:
    mock_client = _build_mock_client(SAMPLE_CONTENT)
    mock_get_client.return_value = mock_client

    result = await get_content_by_id("content-uuid-1")

    builder = mock_client.table.return_value
    builder.eq.assert_called_with("id", "content-uuid-1")
    assert result == SAMPLE_CONTENT
