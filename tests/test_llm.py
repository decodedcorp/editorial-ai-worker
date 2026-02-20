"""Unit tests for LLM factory function."""

from unittest.mock import patch

import pytest
from langchain_google_genai import ChatGoogleGenerativeAI

from editorial_ai.llm import create_llm


@pytest.fixture(autouse=True)
def _fake_api_key() -> None:
    """Provide a dummy API key so ChatGoogleGenerativeAI can be instantiated."""
    with patch("editorial_ai.llm.settings") as mock_settings:
        mock_settings.google_api_key = "fake-key-for-unit-test"
        mock_settings.default_model = "gemini-2.5-flash"
        mock_settings.gcp_project_id = None
        mock_settings.gcp_location = "us-central1"
        yield


def test_create_llm_default():
    """create_llm() returns a ChatGoogleGenerativeAI instance with default settings."""
    llm = create_llm()
    assert isinstance(llm, ChatGoogleGenerativeAI)
    assert llm.temperature == 0.7


def test_create_llm_custom_model():
    """create_llm(model=...) reflects the specified model name."""
    llm = create_llm(model="gemini-2.5-pro")
    assert "gemini-2.5-pro" in llm.model


def test_create_llm_custom_temperature():
    """create_llm(temperature=...) reflects the specified temperature."""
    llm = create_llm(temperature=0.2)
    assert llm.temperature == 0.2
