"""Token usage collector using ContextVar for per-node accumulation.

Usage pattern (called by node_wrapper):
    reset_token_collector()     # start of node
    ...                         # LLM calls invoke record_token_usage()
    tokens = harvest_tokens()   # end of node — returns and clears
"""

from __future__ import annotations

import logging
from contextvars import ContextVar

from editorial_ai.observability.models import TokenUsage

logger = logging.getLogger(__name__)

_token_usage_var: ContextVar[list[TokenUsage]] = ContextVar(
    "_token_usage_var", default=[]
)


def reset_token_collector() -> None:
    """Reset the token collector to an empty list. Called at start of each node."""
    _token_usage_var.set([])


def record_token_usage(
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    model_name: str | None = None,
) -> None:
    """Append a TokenUsage entry to the current context.

    Fire-and-forget: logs warning on failure, never raises.
    """
    try:
        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            model_name=model_name,
        )
        current = _token_usage_var.get()
        # ContextVar default returns the same list object, so we need
        # to create a new list if it's the default empty list to avoid
        # cross-context contamination.
        if not current:
            current = [usage]
            _token_usage_var.set(current)
        else:
            current.append(usage)
    except Exception:
        logger.warning("Failed to record token usage", exc_info=True)


def harvest_tokens() -> list[TokenUsage]:
    """Return accumulated token usages and clear the collector.

    Called at end of each node by the wrapper.
    """
    try:
        tokens = _token_usage_var.get()
        result = list(tokens)  # copy
        _token_usage_var.set([])
        return result
    except Exception:
        logger.warning("Failed to harvest tokens", exc_info=True)
        return []
