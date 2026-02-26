"""Node wrapper decorator for LangGraph node observability instrumentation.

Wraps each pipeline node to capture:
- Timing (started_at, ended_at, duration_ms)
- State snapshots (input/output as JSON-safe dicts)
- Token usage (harvested from ContextVar collector)
- Error details (type, message, traceback)

All instrumentation is fire-and-forget: wrapper failures never interrupt
pipeline execution. Node errors ARE re-raised after logging.
"""

from __future__ import annotations

import asyncio
import functools
import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Any

from editorial_ai.observability.collector import harvest_tokens, reset_token_collector
from editorial_ai.observability.models import NodeRunLog
from editorial_ai.observability.storage import append_node_log

logger = logging.getLogger(__name__)


def _safe_serialize(obj: Any) -> dict | None:
    """Convert an object to a JSON-safe dict.

    Handles Pydantic models, bytes, datetimes, etc. via ``default=str``.
    Returns ``{"_serialization_error": ...}`` on failure rather than raising.
    """
    try:
        return json.loads(json.dumps(obj, default=str))  # type: ignore[return-value]
    except Exception as exc:  # noqa: BLE001
        return {"_serialization_error": str(exc)}


def node_wrapper(node_name: str):
    """Decorator factory that wraps a LangGraph node function with observability.

    Usage::

        wrapped = node_wrapper("curation")(curation_node)
    """

    def decorator(fn):  # noqa: ANN001, ANN202
        if asyncio.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(state: dict, *args: Any, **kwargs: Any) -> Any:
                # --- Instrumentation pre-flight ---
                try:
                    reset_token_collector()
                except Exception:  # noqa: BLE001
                    logger.warning("node_wrapper: reset_token_collector failed", exc_info=True)

                started_at = datetime.now(timezone.utc)
                input_state = _safe_serialize(state)

                # --- Execute the node ---
                error_to_raise: BaseException | None = None
                result: Any = None
                try:
                    result = await fn(state, *args, **kwargs)
                except BaseException as exc:
                    error_to_raise = exc

                # --- Instrumentation post-flight ---
                try:
                    ended_at = datetime.now(timezone.utc)
                    token_usage = harvest_tokens()
                    output_state = _safe_serialize(result) if error_to_raise is None else None

                    # Build error fields
                    error_type: str | None = None
                    error_message: str | None = None
                    error_tb: str | None = None
                    if error_to_raise is not None:
                        error_type = type(error_to_raise).__name__
                        error_message = str(error_to_raise)
                        tb_lines = traceback.format_exc().strip().splitlines()
                        error_tb = "\n".join(tb_lines[:5])

                    log = NodeRunLog(
                        thread_id=state.get("thread_id", "unknown") if isinstance(state, dict) else "unknown",
                        node_name=node_name,
                        status="error" if error_to_raise else "success",
                        started_at=started_at,
                        ended_at=ended_at,
                        token_usage=token_usage,
                        input_state=input_state,
                        output_state=output_state,
                        error_type=error_type,
                        error_message=error_message,
                        error_traceback=error_tb,
                    )
                    append_node_log(log)
                except Exception:  # noqa: BLE001
                    logger.warning(
                        "node_wrapper: post-flight instrumentation failed for node=%s",
                        node_name,
                        exc_info=True,
                    )

                # --- Re-raise node errors ---
                if error_to_raise is not None:
                    raise error_to_raise

                return result

            return async_wrapper

        else:
            # Sync node support (wrap in async for uniform handling)
            @functools.wraps(fn)
            async def sync_wrapper(state: dict, *args: Any, **kwargs: Any) -> Any:
                try:
                    reset_token_collector()
                except Exception:  # noqa: BLE001
                    logger.warning("node_wrapper: reset_token_collector failed", exc_info=True)

                started_at = datetime.now(timezone.utc)
                input_state = _safe_serialize(state)

                error_to_raise: BaseException | None = None
                result: Any = None
                try:
                    result = fn(state, *args, **kwargs)
                except BaseException as exc:
                    error_to_raise = exc

                try:
                    ended_at = datetime.now(timezone.utc)
                    token_usage = harvest_tokens()
                    output_state = _safe_serialize(result) if error_to_raise is None else None

                    error_type: str | None = None
                    error_message: str | None = None
                    error_tb: str | None = None
                    if error_to_raise is not None:
                        error_type = type(error_to_raise).__name__
                        error_message = str(error_to_raise)
                        tb_lines = traceback.format_exc().strip().splitlines()
                        error_tb = "\n".join(tb_lines[:5])

                    log = NodeRunLog(
                        thread_id=state.get("thread_id", "unknown") if isinstance(state, dict) else "unknown",
                        node_name=node_name,
                        status="error" if error_to_raise else "success",
                        started_at=started_at,
                        ended_at=ended_at,
                        token_usage=token_usage,
                        input_state=input_state,
                        output_state=output_state,
                        error_type=error_type,
                        error_message=error_message,
                        error_traceback=error_tb,
                    )
                    append_node_log(log)
                except Exception:  # noqa: BLE001
                    logger.warning(
                        "node_wrapper: post-flight instrumentation failed for node=%s",
                        node_name,
                        exc_info=True,
                    )

                if error_to_raise is not None:
                    raise error_to_raise

                return result

            return sync_wrapper

    return decorator
