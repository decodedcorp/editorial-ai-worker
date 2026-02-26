"""JSONL file storage for node execution logs.

All operations are fire-and-forget: failures log warnings but never raise.
One JSONL file per thread: data/logs/{thread_id}.jsonl
"""

from __future__ import annotations

import logging
from pathlib import Path

from editorial_ai.observability.models import NodeRunLog

logger = logging.getLogger(__name__)


def _log_dir() -> Path:
    """Return the log directory, creating it if needed."""
    d = Path("data/logs")
    d.mkdir(parents=True, exist_ok=True)
    return d


def _log_path(thread_id: str) -> Path:
    """Return the JSONL file path for a given thread."""
    return _log_dir() / f"{thread_id}.jsonl"


def append_node_log(log: NodeRunLog) -> None:
    """Append one NodeRunLog as a JSON line to the thread's JSONL file.

    Fire-and-forget: logs warning on failure, never raises.
    """
    try:
        path = _log_path(log.thread_id)
        with open(path, "a", encoding="utf-8") as f:
            f.write(log.model_dump_json() + "\n")
    except Exception:
        logger.warning(
            "Failed to append node log for thread %s", log.thread_id, exc_info=True
        )


def read_node_logs(thread_id: str) -> list[NodeRunLog]:
    """Read all NodeRunLog entries from a thread's JSONL file.

    Returns empty list if file doesn't exist or on any error. Never raises.
    """
    try:
        path = _log_path(thread_id)
        if not path.exists():
            return []
        logs: list[NodeRunLog] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    logs.append(NodeRunLog.model_validate_json(line))
        return logs
    except Exception:
        logger.warning(
            "Failed to read node logs for thread %s", thread_id, exc_info=True
        )
        return []
