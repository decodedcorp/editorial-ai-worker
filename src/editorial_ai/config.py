"""Application settings loaded from .env file or environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings. Loaded from .env file or environment variables."""

    # LLM Provider
    google_api_key: str | None = Field(default=None, alias="GOOGLE_API_KEY")
    gcp_project_id: str | None = Field(default=None, alias="GOOGLE_CLOUD_PROJECT")
    gcp_location: str = Field(default="us-central1", alias="GOOGLE_CLOUD_LOCATION")
    google_genai_use_vertexai: bool | None = Field(
        default=None, alias="GOOGLE_GENAI_USE_VERTEXAI"
    )
    default_model: str = "gemini-2.5-flash"

    # LangSmith
    langsmith_tracing: bool = Field(default=False, alias="LANGSMITH_TRACING")
    langsmith_api_key: str | None = Field(default=None, alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field(
        default="editorial-ai-worker", alias="LANGSMITH_PROJECT"
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "populate_by_name": True}


settings = Settings()
