"""Unit tests for ModelRouter config loading, resolve, upgrade conditions, and fallback."""

import textwrap
from pathlib import Path

import pytest

from editorial_ai.routing.model_router import ModelRouter, RoutingDecision


@pytest.fixture
def tmp_config(tmp_path: Path) -> Path:
    """Create a temporary YAML config for isolated testing."""
    config = textwrap.dedent("""\
        defaults:
          model: "gemini-2.5-flash"

        nodes:
          simple_node:
            default_model: "gemini-2.5-flash-lite"
          complex_node:
            default_model: "gemini-2.5-flash"
          upgradeable_node:
            default_model: "gemini-2.5-flash"
            upgrade_model: "gemini-2.5-pro"
            upgrade_conditions:
              min_revision_count: 2
    """)
    config_path = tmp_path / "test_routing_config.yaml"
    config_path.write_text(config)
    return config_path


@pytest.fixture
def router(tmp_config: Path) -> ModelRouter:
    return ModelRouter(config_path=tmp_config)


def test_resolve_default_model(router: ModelRouter) -> None:
    """Flash-Lite nodes return correct model."""
    decision = router.resolve("simple_node")
    assert decision.model == "gemini-2.5-flash-lite"
    assert decision.reason == "default"


def test_resolve_complex_model(router: ModelRouter) -> None:
    """Flash nodes return correct model."""
    decision = router.resolve("complex_node")
    assert decision.model == "gemini-2.5-flash"
    assert decision.reason == "default"


def test_resolve_upgrade_condition(router: ModelRouter) -> None:
    """revision_count >= 2 triggers Pro upgrade."""
    decision = router.resolve("upgradeable_node", revision_count=2)
    assert decision.model == "gemini-2.5-pro"
    assert decision.reason == "upgrade:revision>=2"

    decision_high = router.resolve("upgradeable_node", revision_count=5)
    assert decision_high.model == "gemini-2.5-pro"


def test_resolve_no_upgrade_below_threshold(router: ModelRouter) -> None:
    """revision_count < 2 stays at Flash."""
    decision = router.resolve("upgradeable_node", revision_count=0)
    assert decision.model == "gemini-2.5-flash"
    assert decision.reason == "default"

    decision_one = router.resolve("upgradeable_node", revision_count=1)
    assert decision_one.model == "gemini-2.5-flash"


def test_resolve_unknown_node_fallback(router: ModelRouter) -> None:
    """Unknown node returns fallback model."""
    decision = router.resolve("nonexistent_node")
    assert decision.model == "gemini-2.5-flash"
    assert decision.reason == "fallback"


def test_routing_decision_has_reason(router: ModelRouter) -> None:
    """Reason string is populated correctly for all cases."""
    assert router.resolve("simple_node").reason == "default"
    assert router.resolve("nonexistent_node").reason == "fallback"
    assert router.resolve("upgradeable_node", revision_count=3).reason == "upgrade:revision>=2"


def test_custom_config_path(tmp_path: Path) -> None:
    """Can load from a custom path with different defaults."""
    config = textwrap.dedent("""\
        defaults:
          model: "custom-fallback-model"
        nodes:
          my_node:
            default_model: "my-custom-model"
    """)
    config_path = tmp_path / "custom.yaml"
    config_path.write_text(config)

    router = ModelRouter(config_path=config_path)
    assert router.fallback_model == "custom-fallback-model"
    assert router.resolve("my_node").model == "my-custom-model"
    assert router.resolve("unknown").model == "custom-fallback-model"


def test_production_config_loads() -> None:
    """Production routing_config.yaml loads without error and has expected nodes."""
    router = ModelRouter()  # Uses default config path
    # Check a few known nodes from the production config
    assert router.resolve("curation_subtopics").model == "gemini-2.5-flash-lite"
    assert router.resolve("editorial_content").model == "gemini-2.5-flash"
    assert router.resolve("editorial_content", revision_count=2).model == "gemini-2.5-pro"
    assert router.resolve("review", revision_count=3).model == "gemini-2.5-pro"
    assert router.fallback_model == "gemini-2.5-flash"
