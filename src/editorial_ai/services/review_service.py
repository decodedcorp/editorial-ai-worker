"""Review service implementing hybrid Pydantic + LLM-as-a-Judge evaluation.

Evaluation pipeline:
1. Format validation -- deterministic via Pydantic MagazineLayout.model_validate()
2. Semantic evaluation -- LLM-as-a-Judge for hallucination, fact_accuracy, content_completeness
3. Overall result -- aggregates all criteria, any failure = overall fail
"""

import json
import logging

from google import genai
from google.genai import types
from pydantic import ValidationError

from editorial_ai.config import settings
from editorial_ai.models.layout import BodyTextBlock, MagazineLayout
from editorial_ai.observability import record_token_usage
from editorial_ai.models.review import CriterionResult, ReviewResult
from editorial_ai.prompts.review import build_review_prompt
from editorial_ai.services.curation_service import (
    _strip_markdown_fences,
    get_genai_client,
    retry_on_api_error,
)

logger = logging.getLogger(__name__)

# Re-export for convenience
__all__ = ["ReviewService", "get_genai_client"]


class ReviewService:
    """Hybrid review service: deterministic format check + LLM semantic evaluation.

    Format validation uses Pydantic MagazineLayout schema (no LLM).
    Semantic evaluation uses Gemini with temperature=0.0 for deterministic scoring.
    """

    def __init__(self, client: genai.Client, *, model: str | None = None) -> None:
        self.client = client
        self.model = model or settings.default_model

    def validate_format(self, draft: dict) -> CriterionResult:
        """Deterministic format validation via Pydantic MagazineLayout.

        Checks:
        1. Schema validity (all required fields, correct types)
        2. Structural requirements (non-empty title, body_text block exists)
        """
        # Step 1: Pydantic schema validation
        try:
            layout = MagazineLayout.model_validate(draft)
        except ValidationError as e:
            return CriterionResult(
                criterion="format",
                passed=False,
                reason=f"Schema validation failed: {e.error_count()} error(s) -- {e.errors()[0]['msg']}",
                severity="critical",
            )

        # Step 2: Structural checks
        if not layout.title or not layout.title.strip():
            return CriterionResult(
                criterion="format",
                passed=False,
                reason="Title is empty or whitespace-only",
                severity="critical",
            )

        has_body_text = any(isinstance(b, BodyTextBlock) for b in layout.blocks)
        if not has_body_text:
            return CriterionResult(
                criterion="format",
                passed=False,
                reason="No body_text block found in layout blocks",
                severity="critical",
            )

        return CriterionResult(
            criterion="format",
            passed=True,
            reason="Schema valid, structure complete",
            severity="minor",
        )

    @retry_on_api_error
    async def evaluate_with_llm(
        self, draft_json: str, curated_topics_json: str
    ) -> list[CriterionResult]:
        """LLM-as-a-Judge for hallucination, fact_accuracy, content_completeness.

        Calls Gemini with structured output and temperature=0.0 for deterministic
        evaluation. Returns only semantic criteria (excludes format).
        """
        prompt = build_review_prompt(draft_json, curated_topics_json)

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ReviewResult,
                temperature=0.0,
            ),
        )
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            record_token_usage(
                prompt_tokens=getattr(response.usage_metadata, "prompt_token_count", 0) or 0,
                completion_tokens=getattr(response.usage_metadata, "candidates_token_count", 0) or 0,
                total_tokens=getattr(response.usage_metadata, "total_token_count", 0) or 0,
                model_name=self.model,
            )

        raw_text = response.text or "{}"
        result = ReviewResult.model_validate_json(_strip_markdown_fences(raw_text))

        # Return only non-format criteria (format is handled by Pydantic)
        return [c for c in result.criteria if c.criterion != "format"]

    async def evaluate(
        self, draft: dict, curated_topics: list[dict]
    ) -> ReviewResult:
        """Full evaluation entry point: format (Pydantic) + LLM (semantic).

        Steps:
        1. Deterministic format validation via validate_format()
        2. LLM semantic evaluation via evaluate_with_llm()
        3. Combine all criteria and compute overall pass/fail
        """
        # Step 1: Deterministic format check
        format_result = self.validate_format(draft)

        # Step 2: LLM semantic evaluation
        draft_json = json.dumps(draft, ensure_ascii=False)
        topics_json = json.dumps(curated_topics, ensure_ascii=False)
        llm_criteria = await self.evaluate_with_llm(draft_json, topics_json)

        # Step 3: Combine all criteria
        all_criteria = [format_result] + llm_criteria

        # Step 4: Compute overall pass (all must pass)
        overall_passed = all(c.passed for c in all_criteria)

        # Step 5: Build suggestions from failed criteria
        suggestions = [c.reason for c in all_criteria if not c.passed]

        # Step 6: Build summary
        if overall_passed:
            summary = "All evaluation criteria passed. Draft is ready for publication."
        else:
            failed_names = [c.criterion for c in all_criteria if not c.passed]
            summary = f"Review failed on: {', '.join(failed_names)}. Revision needed."

        return ReviewResult(
            passed=overall_passed,
            criteria=all_criteria,
            summary=summary,
            suggestions=suggestions,
        )
