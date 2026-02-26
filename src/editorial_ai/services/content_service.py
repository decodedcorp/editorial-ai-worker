"""CRUD service for editorial contents using local JSON file storage.

Stores content as individual JSON files in data/contents/{id}.json.
PRD Supabase is read-only (reference only) — generated content is saved locally.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_CONTENTS_DIR = Path("data/contents")


def _ensure_dir() -> Path:
    _CONTENTS_DIR.mkdir(parents=True, exist_ok=True)
    return _CONTENTS_DIR


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _all_contents() -> list[dict]:
    """Load all content files, sorted by created_at desc."""
    d = _ensure_dir()
    items: list[dict] = []
    for p in d.glob("*.json"):
        item = _load(p)
        if item:
            items.append(item)
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items


# --- Public API (same signatures as before, kept async for compatibility) ---


async def save_pending_content(
    thread_id: str,
    layout_json: dict,
    title: str,
    keyword: str,
    review_summary: str | None = None,
) -> dict:
    """Save or update pending content for a given thread (upsert on thread_id).

    Idempotent: if content for the thread already exists, it overwrites.
    """
    d = _ensure_dir()

    # Check if thread_id already exists (upsert)
    existing = await get_content_by_thread_id(thread_id)
    if existing:
        content_id = existing["id"]
        now = _now_iso()
        existing.update(
            {
                "status": "pending",
                "title": title,
                "keyword": keyword,
                "layout_json": layout_json,
                "review_summary": review_summary,
                "updated_at": now,
            }
        )
        _save(d / f"{content_id}.json", existing)
        return existing

    # New content
    content_id = str(uuid.uuid4())
    now = _now_iso()
    data = {
        "id": content_id,
        "thread_id": thread_id,
        "status": "pending",
        "title": title,
        "keyword": keyword,
        "layout_json": layout_json,
        "review_summary": review_summary,
        "rejection_reason": None,
        "admin_feedback": None,
        "created_at": now,
        "updated_at": now,
        "published_at": None,
    }
    _save(d / f"{content_id}.json", data)
    logger.info("Saved pending content: id=%s, thread_id=%s", content_id, thread_id)
    return data


async def update_content_status(
    content_id: str,
    status: str,
    *,
    rejection_reason: str | None = None,
    admin_feedback: str | None = None,
) -> dict:
    """Update the status of a content entry."""
    d = _ensure_dir()
    path = d / f"{content_id}.json"
    data = _load(path)
    if not data:
        raise FileNotFoundError(f"Content {content_id} not found")

    data["status"] = status
    data["updated_at"] = _now_iso()
    if rejection_reason is not None:
        data["rejection_reason"] = rejection_reason
    if admin_feedback is not None:
        data["admin_feedback"] = admin_feedback
    if status == "published":
        data["published_at"] = _now_iso()

    _save(path, data)
    return data


async def get_content_by_id(content_id: str) -> dict | None:
    """Fetch a single content entry by its UUID."""
    return _load(_ensure_dir() / f"{content_id}.json")


async def get_content_by_thread_id(thread_id: str) -> dict | None:
    """Fetch a single content entry by LangGraph thread_id."""
    for item in _all_contents():
        if item.get("thread_id") == thread_id:
            return item
    return None


async def list_contents(
    *, status: str | None = None, limit: int = 50, offset: int = 0
) -> list[dict]:
    """List content entries, optionally filtered by status, ordered by created_at desc."""
    items = _all_contents()
    if status is not None:
        items = [i for i in items if i.get("status") == status]
    return items[offset : offset + limit]


async def list_contents_count(*, status: str | None = None) -> int:
    """Count content entries, optionally filtered by status."""
    items = _all_contents()
    if status is not None:
        items = [i for i in items if i.get("status") == status]
    return len(items)
