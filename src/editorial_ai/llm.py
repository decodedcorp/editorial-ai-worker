"""LLM instance factory for Gemini models."""

from langchain_google_genai import ChatGoogleGenerativeAI

from editorial_ai.config import settings


def create_llm(
    model: str | None = None,
    temperature: float = 0.7,
) -> ChatGoogleGenerativeAI:
    """Create a ChatGoogleGenerativeAI instance.

    Backend is determined automatically by environment variables:
    - GOOGLE_API_KEY only -> Gemini Developer API
    - GOOGLE_GENAI_USE_VERTEXAI=true -> Vertex AI
    """
    return ChatGoogleGenerativeAI(
        model=model or settings.default_model,
        temperature=temperature,
        api_key=settings.google_api_key,
        project=settings.gcp_project_id,
        location=settings.gcp_location,
    )
