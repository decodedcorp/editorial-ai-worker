"""Design spec generation service using native google-genai SDK.

Calls Gemini to generate a DesignSpec JSON from a keyword, with structured
output via response_schema. Falls back to default_design_spec() on any failure.
"""

from __future__ import annotations

import logging

from google import genai
from google.genai import types

from editorial_ai.config import settings
from editorial_ai.models.design_spec import DesignSpec, default_design_spec
from editorial_ai.observability import record_token_usage
from editorial_ai.prompts.design_spec import build_design_spec_prompt
from editorial_ai.services.curation_service import get_genai_client

logger = logging.getLogger(__name__)


class DesignSpecService:
    """Service for generating design specifications via Gemini.

    Uses structured JSON output (response_schema) for reliable parsing.
    Falls back to default_design_spec() on any failure.
    """

    def __init__(
        self,
        client: genai.Client | None = None,
        model_name: str | None = None,
    ) -> None:
        self.client = client or get_genai_client()
        self.model_name = model_name or settings.default_model

    async def generate_spec(
        self,
        keyword: str,
        category: str | None = None,
    ) -> DesignSpec:
        """Generate a DesignSpec for the given keyword via Gemini.

        Args:
            keyword: The editorial keyword/topic.
            category: Optional content category.

        Returns:
            A DesignSpec instance (AI-generated or default fallback).
        """
        try:
            prompt = build_design_spec_prompt(keyword, category)
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=DesignSpec,
                    temperature=0.7,
                ),
            )

            # Record token usage
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                record_token_usage(
                    prompt_tokens=getattr(response.usage_metadata, "prompt_token_count", 0) or 0,
                    completion_tokens=getattr(
                        response.usage_metadata, "candidates_token_count", 0
                    )
                    or 0,
                    total_tokens=getattr(response.usage_metadata, "total_token_count", 0) or 0,
                    model_name=self.model_name,
                )

            raw_text = response.text or "{}"
            spec = DesignSpec.model_validate_json(raw_text)
            logger.info("Generated design spec for keyword=%s, mood=%s", keyword, spec.mood)
            return spec

        except Exception:  # noqa: BLE001
            logger.warning(
                "Failed to generate design spec for keyword=%s, using default",
                keyword,
                exc_info=True,
            )
            return default_design_spec()
