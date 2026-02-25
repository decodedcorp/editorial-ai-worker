"""Tests for the admin API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from editorial_ai.api.app import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_NOW = datetime.now(UTC).isoformat()

_SAMPLE_CONTENT = {
    "id": "00000000-0000-0000-0000-000000000001",
    "thread_id": "test-thread-1",
    "status": "pending",
    "title": "Test Article",
    "keyword": "fashion",
    "layout_json": {"title": "Test Article", "blocks": []},
    "review_summary": "Looks good",
    "rejection_reason": None,
    "admin_feedback": None,
    "created_at": _NOW,
    "updated_at": _NOW,
    "published_at": None,
}


@pytest.fixture()
def mock_graph():
    """Mock CompiledStateGraph with async ainvoke."""
    graph = MagicMock()
    graph.ainvoke = AsyncMock(return_value={})
    return graph


@pytest.fixture()
async def client(mock_graph):
    """AsyncClient that bypasses lifespan and injects mock graph."""
    # Bypass lifespan entirely -- set app.state directly
    app.state.graph = mock_graph
    app.state.checkpointer = MagicMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# List contents
# ---------------------------------------------------------------------------


@patch("editorial_ai.api.routes.admin.list_contents_count", new_callable=AsyncMock)
@patch("editorial_ai.api.routes.admin.list_contents", new_callable=AsyncMock)
async def test_list_contents_empty(
    mock_list: AsyncMock, mock_count: AsyncMock, client: AsyncClient
):
    mock_list.return_value = []
    mock_count.return_value = 0

    resp = await client.get("/api/contents")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@patch("editorial_ai.api.routes.admin.list_contents_count", new_callable=AsyncMock)
@patch("editorial_ai.api.routes.admin.list_contents", new_callable=AsyncMock)
async def test_list_contents_with_status_filter(
    mock_list: AsyncMock, mock_count: AsyncMock, client: AsyncClient
):
    mock_list.return_value = [_SAMPLE_CONTENT]
    mock_count.return_value = 1

    resp = await client.get("/api/contents?status=pending")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["status"] == "pending"
    mock_list.assert_called_once_with(status="pending", limit=50, offset=0)


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------


@patch("editorial_ai.api.routes.admin.get_content_by_id", new_callable=AsyncMock)
async def test_get_content_not_found(mock_get: AsyncMock, client: AsyncClient):
    mock_get.return_value = None
    resp = await client.get("/api/contents/nonexistent-id")
    assert resp.status_code == 404


@patch("editorial_ai.api.routes.admin.get_content_by_id", new_callable=AsyncMock)
async def test_get_content_found(mock_get: AsyncMock, client: AsyncClient):
    mock_get.return_value = _SAMPLE_CONTENT
    resp = await client.get(f"/api/contents/{_SAMPLE_CONTENT['id']}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Test Article"


# ---------------------------------------------------------------------------
# Reject validation
# ---------------------------------------------------------------------------


async def test_reject_without_reason_returns_422(client: AsyncClient):
    """Pydantic validation: reason is required for reject."""
    resp = await client.post(
        "/api/contents/some-id/reject",
        json={},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Approve
# ---------------------------------------------------------------------------


@patch("editorial_ai.api.routes.admin.update_content_status", new_callable=AsyncMock)
@patch("editorial_ai.api.routes.admin.get_content_by_id", new_callable=AsyncMock)
async def test_approve_content(
    mock_get: AsyncMock,
    mock_update: AsyncMock,
    client: AsyncClient,
    mock_graph: MagicMock,
):
    mock_get.return_value = _SAMPLE_CONTENT
    approved_content = {**_SAMPLE_CONTENT, "status": "approved"}
    mock_update.return_value = approved_content

    resp = await client.post(
        f"/api/contents/{_SAMPLE_CONTENT['id']}/approve",
        json={"feedback": "Great work"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
    mock_graph.ainvoke.assert_called_once()
    mock_update.assert_called_once_with(
        _SAMPLE_CONTENT["id"], "approved", admin_feedback="Great work"
    )


# ---------------------------------------------------------------------------
# Reject (full flow)
# ---------------------------------------------------------------------------


@patch("editorial_ai.api.routes.admin.update_content_status", new_callable=AsyncMock)
@patch("editorial_ai.api.routes.admin.get_content_by_id", new_callable=AsyncMock)
async def test_reject_content(
    mock_get: AsyncMock,
    mock_update: AsyncMock,
    client: AsyncClient,
    mock_graph: MagicMock,
):
    mock_get.return_value = _SAMPLE_CONTENT
    rejected_content = {
        **_SAMPLE_CONTENT,
        "status": "rejected",
        "rejection_reason": "Low quality",
    }
    mock_update.return_value = rejected_content

    resp = await client.post(
        f"/api/contents/{_SAMPLE_CONTENT['id']}/reject",
        json={"reason": "Low quality"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
    mock_graph.ainvoke.assert_called_once()
    mock_update.assert_called_once_with(
        _SAMPLE_CONTENT["id"], "rejected", rejection_reason="Low quality"
    )


# ---------------------------------------------------------------------------
# API key enforcement
# ---------------------------------------------------------------------------


@patch("editorial_ai.api.deps.settings")
async def test_api_key_required_when_configured(mock_settings: MagicMock):
    """When ADMIN_API_KEY is set, requests without key return 401."""
    mock_settings.admin_api_key = "secret-key"

    # Create a fresh client for this test to pick up mocked settings
    app.state.graph = MagicMock()
    app.state.checkpointer = MagicMock()
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as ac:
        resp = await ac.get("/api/contents")
        assert resp.status_code == 401


@patch("editorial_ai.api.routes.admin.list_contents_count", new_callable=AsyncMock)
@patch("editorial_ai.api.routes.admin.list_contents", new_callable=AsyncMock)
@patch("editorial_ai.api.deps.settings")
async def test_api_key_accepted_when_correct(
    mock_settings: MagicMock,
    mock_list: AsyncMock,
    mock_count: AsyncMock,
):
    """When correct key is provided, request succeeds."""
    mock_settings.admin_api_key = "secret-key"
    mock_list.return_value = []
    mock_count.return_value = 0

    app.state.graph = MagicMock()
    app.state.checkpointer = MagicMock()
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as ac:
        resp = await ac.get(
            "/api/contents", headers={"X-API-Key": "secret-key"}
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Pipeline trigger
# ---------------------------------------------------------------------------


@patch("editorial_ai.api.routes.pipeline.uuid")
async def test_trigger_pipeline(
    mock_uuid: MagicMock, client: AsyncClient, mock_graph: MagicMock
):
    mock_uuid.uuid4.return_value = "test-uuid-1234"

    resp = await client.post(
        "/api/pipeline/trigger",
        json={"seed_keyword": "spring fashion"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["thread_id"] == "test-uuid-1234"
    assert "admin gate" in data["message"].lower()
    mock_graph.ainvoke.assert_called_once()
