"""Config-driven model router for dynamic Gemini model selection.

Maps pipeline node names to Gemini models based on task complexity,
with conditional upgrade to higher-tier models on retries.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = Path(__file__).parent / "routing_config.yaml"


@dataclass
class ModelRoute:
    default_model: str
    upgrade_model: str | None = None
    upgrade_conditions: dict = field(default_factory=dict)


@dataclass
class RoutingDecision:
    model: str
    reason: str  # "default", "upgrade:revision>=2", "fallback"


class ModelRouter:
    """Resolves (node_name, context) -> model_name from YAML config."""

    def __init__(self, config_path: Path | str | None = None) -> None:
        path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
        with open(path) as f:
            raw = yaml.safe_load(f)

        self._fallback_model = raw.get("defaults", {}).get("model", "gemini-2.5-flash")
        self._routes: dict[str, ModelRoute] = {}

        for node_name, cfg in raw.get("nodes", {}).items():
            self._routes[node_name] = ModelRoute(
                default_model=cfg["default_model"],
                upgrade_model=cfg.get("upgrade_model"),
                upgrade_conditions=cfg.get("upgrade_conditions", {}),
            )

    def resolve(
        self,
        node_name: str,
        *,
        revision_count: int = 0,
    ) -> RoutingDecision:
        """Resolve a model for the given node and context.

        Returns a RoutingDecision with model name and reason string.
        """
        route = self._routes.get(node_name)
        if not route:
            return RoutingDecision(model=self._fallback_model, reason="fallback")

        # Check upgrade conditions
        if route.upgrade_model and route.upgrade_conditions:
            min_rev = route.upgrade_conditions.get("min_revision_count")
            if min_rev is not None and revision_count >= min_rev:
                return RoutingDecision(
                    model=route.upgrade_model,
                    reason=f"upgrade:revision>={min_rev}",
                )

        return RoutingDecision(model=route.default_model, reason="default")

    @property
    def fallback_model(self) -> str:
        return self._fallback_model


# Module-level singleton
_router_instance: ModelRouter | None = None


def get_model_router() -> ModelRouter:
    """Get or create the singleton ModelRouter."""
    global _router_instance
    if _router_instance is None:
        _router_instance = ModelRouter()
    return _router_instance
