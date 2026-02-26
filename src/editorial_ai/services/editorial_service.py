"""Editorial service implementing the 3-step content generation pipeline.

Pipeline steps:
1. Generate editorial content via Gemini structured output
2. Generate layout design image via Nano Banana (Gemini image model)
3. Parse layout image to block structure via Gemini Vision AI
4. Merge content into layout blocks

Uses the native google-genai SDK (NOT langchain-google-genai) for direct
access to structured output, image generation, and vision capabilities.
"""

import logging
from copy import deepcopy
from typing import Any

from google import genai
from google.genai import types
from pydantic import ValidationError

from editorial_ai.config import settings
from editorial_ai.models.editorial import (
    EditorialContent,
)
from editorial_ai.observability import record_token_usage
from editorial_ai.models.layout import (
    BodyTextBlock,
    CelebFeatureBlock,
    CelebItem,
    CreditsBlock,
    HashtagBarBlock,
    HeadlineBlock,
    HeroBlock,
    MagazineLayout,
    ProductItem,
    ProductShowcaseBlock,
    PullQuoteBlock,
    create_default_template,
)
from editorial_ai.prompts.editorial import (
    build_content_generation_prompt,
    build_content_generation_prompt_with_feedback,
    build_layout_image_prompt,
    build_layout_parsing_prompt,
    build_output_repair_prompt,
)
from editorial_ai.services.curation_service import (
    _strip_markdown_fences,
    get_genai_client,
    retry_on_api_error,
)

logger = logging.getLogger(__name__)

# Block types available for layout parsing
BLOCK_TYPES = [
    "hero",
    "headline",
    "body_text",
    "image_gallery",
    "pull_quote",
    "product_showcase",
    "celeb_feature",
    "divider",
    "hashtag_bar",
    "credits",
]

# Re-export for convenience
__all__ = ["EditorialService", "get_genai_client"]


class EditorialService:
    """Service for generating editorial content and magazine layouts.

    Implements the 3-step pipeline:
    1. Gemini structured output -> EditorialContent
    2. Nano Banana image generation -> layout design image
    3. Gemini Vision -> parse layout image to block structure
    Then merges content into layout blocks.
    """

    def __init__(
        self,
        client: genai.Client,
        *,
        content_model: str | None = None,
        image_model: str | None = None,
        max_repair_attempts: int | None = None,
    ) -> None:
        self.client = client
        self.content_model = content_model or settings.editorial_model
        self.image_model = image_model or settings.nano_banana_model
        self.max_repair_attempts = (
            max_repair_attempts
            if max_repair_attempts is not None
            else settings.editorial_max_repair_attempts
        )
        self._image_model_available = True  # circuit breaker for image gen

    @retry_on_api_error
    async def generate_content(
        self,
        keyword: str,
        trend_context: str,
        *,
        feedback_history: list[dict] | None = None,
        previous_draft: dict | None = None,
    ) -> EditorialContent:
        """Step 1: Generate editorial content via Gemini structured output.

        Returns an EditorialContent model with title, body, quotes, etc.
        On parse failure, attempts markdown fence stripping then repair loop.

        When feedback_history is provided (retry iteration), uses feedback-aware
        prompt that prepends review failures before generation instructions.
        """
        if feedback_history:
            prompt = build_content_generation_prompt_with_feedback(
                keyword, trend_context, feedback_history, previous_draft
            )
        else:
            prompt = build_content_generation_prompt(keyword, trend_context)

        response = await self.client.aio.models.generate_content(
            model=self.content_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=EditorialContent,
                temperature=0.7,
            ),
        )
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            record_token_usage(
                prompt_tokens=getattr(response.usage_metadata, "prompt_token_count", 0) or 0,
                completion_tokens=getattr(response.usage_metadata, "candidates_token_count", 0) or 0,
                total_tokens=getattr(response.usage_metadata, "total_token_count", 0) or 0,
                model_name=self.content_model,
            )

        raw_json = response.text or "{}"

        # Try direct parse, then stripped, then repair
        for text_candidate in [raw_json, _strip_markdown_fences(raw_json)]:
            try:
                return EditorialContent.model_validate_json(
                    text_candidate,
                )
            except ValidationError:
                continue

        # All direct parsing failed — try repair loop
        return await self._validate_with_repair(
            raw_json,
            EditorialContent,
            "EditorialContent",
        )

    async def generate_layout_image(
        self,
        keyword: str,
        title: str,
        num_sections: int,
    ) -> bytes | None:
        """Step 2: Generate a magazine layout design image via Nano Banana.

        Returns image bytes on success, None on failure.
        Caller should fall back to default template on None.
        """
        if not self._image_model_available:
            logger.debug(
                "Skipping Nano Banana (model unavailable), using default template for keyword=%s",
                keyword,
            )
            return None

        prompt = build_layout_image_prompt(keyword, title, num_sections)

        try:
            response = await self.client.aio.models.generate_content(
                model=self.image_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                    temperature=1.0,
                ),
            )
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                record_token_usage(
                    prompt_tokens=getattr(response.usage_metadata, "prompt_token_count", 0) or 0,
                    completion_tokens=getattr(response.usage_metadata, "candidates_token_count", 0) or 0,
                    total_tokens=getattr(response.usage_metadata, "total_token_count", 0) or 0,
                    model_name=self.image_model,
                )

            candidates = response.candidates
            if not candidates:
                logger.warning(
                    "Nano Banana returned no candidates for keyword=%s",
                    keyword,
                )
                return None

            parts = candidates[0].content.parts
            if not parts:
                return None

            for part in parts:
                if part.inline_data is not None:
                    return part.inline_data.data  # type: ignore[return-value]

            logger.warning(
                "No image data in Nano Banana response for keyword=%s",
                keyword,
            )
            return None
        except Exception as exc:  # noqa: BLE001
            exc_str = str(exc).lower()
            if "404" in exc_str or "not found" in exc_str or "not supported" in exc_str:
                self._image_model_available = False
                logger.warning(
                    "Nano Banana model '%s' not available (404/not supported). "
                    "Disabling image generation for this session. Falling back to default template.",
                    self.image_model,
                )
            else:
                logger.warning(
                    "Nano Banana layout generation failed for keyword=%s",
                    keyword,
                    exc_info=True,
                )
            return None

    async def parse_layout_image(
        self,
        image_bytes: bytes,
        keyword: str,
    ) -> list[dict[str, Any]] | None:
        """Step 3: Parse layout image to block structure via Gemini Vision.

        Returns a list of block definitions like [{"type": "hero", "order": 0}, ...]
        or None on failure.
        """
        prompt = build_layout_parsing_prompt(keyword, BLOCK_TYPES)

        try:
            response = await self.client.aio.models.generate_content(
                model=self.content_model,
                contents=[
                    prompt,
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type="image/png",
                    ),
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,
                ),
            )
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                record_token_usage(
                    prompt_tokens=getattr(response.usage_metadata, "prompt_token_count", 0) or 0,
                    completion_tokens=getattr(response.usage_metadata, "candidates_token_count", 0) or 0,
                    total_tokens=getattr(response.usage_metadata, "total_token_count", 0) or 0,
                    model_name=self.content_model,
                )

            raw_text = response.text or "[]"
            import json

            for text_candidate in [
                raw_text,
                _strip_markdown_fences(raw_text),
            ]:
                try:
                    parsed = json.loads(text_candidate)
                    if isinstance(parsed, list):
                        return parsed  # type: ignore[return-value]
                except (json.JSONDecodeError, TypeError):
                    continue

            logger.warning(
                "Vision parse did not return a list for keyword=%s",
                keyword,
            )
            return None
        except Exception:  # noqa: BLE001
            logger.warning(
                "Vision layout parsing failed for keyword=%s",
                keyword,
                exc_info=True,
            )
            return None

    async def repair_output(
        self,
        model_class_name: str,
        raw_json: str,
        error_msg: str,
    ) -> str:
        """Attempt to repair malformed JSON using Gemini.

        Returns the corrected JSON string. Single attempt, no retry.
        """
        prompt = build_output_repair_prompt(
            model_class_name,
            raw_json,
            error_msg,
        )

        response = await self.client.aio.models.generate_content(
            model=self.content_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            record_token_usage(
                prompt_tokens=getattr(response.usage_metadata, "prompt_token_count", 0) or 0,
                completion_tokens=getattr(response.usage_metadata, "candidates_token_count", 0) or 0,
                total_tokens=getattr(response.usage_metadata, "total_token_count", 0) or 0,
                model_name=self.content_model,
            )

        return response.text or "{}"

    async def _validate_with_repair(
        self,
        raw_json: str,
        model_cls: type[Any],
        model_name: str,
    ) -> Any:
        """Validate JSON against a Pydantic model, retrying with repair on failure.

        Loops up to max_repair_attempts, calling repair_output each time.
        Returns validated model instance or raises last ValidationError.
        """
        last_error: ValidationError | None = None
        current_json = raw_json

        for attempt in range(self.max_repair_attempts + 1):
            try:
                return model_cls.model_validate_json(current_json)
            except ValidationError as e:
                last_error = e
                if attempt < self.max_repair_attempts:
                    logger.info(
                        "Repair attempt %d/%d for %s",
                        attempt + 1,
                        self.max_repair_attempts,
                        model_name,
                    )
                    current_json = await self.repair_output(
                        model_name,
                        current_json,
                        str(e),
                    )
                    # Strip fences from repair response too
                    current_json = _strip_markdown_fences(current_json)

        raise last_error  # type: ignore[misc]

    def merge_content_into_layout(
        self,
        content: EditorialContent,
        layout: MagazineLayout,
    ) -> MagazineLayout:
        """Merge EditorialContent fields into MagazineLayout blocks.

        Maps content fields to blocks by type. Returns a new MagazineLayout
        (does not mutate input).
        """
        new_layout = deepcopy(layout)
        pull_quote_idx = 0

        for block in new_layout.blocks:
            if isinstance(block, HeroBlock):
                block.overlay_title = content.title
                block.overlay_subtitle = content.subtitle
            elif isinstance(block, HeadlineBlock):
                block.text = content.title
            elif isinstance(block, BodyTextBlock):
                block.paragraphs = content.body_paragraphs
            elif isinstance(block, PullQuoteBlock):
                if pull_quote_idx < len(content.pull_quotes):
                    block.quote = content.pull_quotes[pull_quote_idx]
                    pull_quote_idx += 1
            elif isinstance(block, ProductShowcaseBlock):
                block.products = [
                    ProductItem(
                        name=pm.name,
                        brand=pm.brand,
                        description=pm.context,
                    )
                    for pm in content.product_mentions
                ]
            elif isinstance(block, CelebFeatureBlock):
                block.celebs = [
                    CelebItem(
                        name=cm.name,
                        description=cm.context,
                    )
                    for cm in content.celeb_mentions
                ]
            elif isinstance(block, HashtagBarBlock):
                block.hashtags = content.hashtags
            elif isinstance(block, CreditsBlock):
                block.entries = content.credits

        return new_layout

    async def create_editorial(
        self,
        keyword: str,
        trend_context: str,
        *,
        feedback_history: list[dict] | None = None,
        previous_draft: dict | None = None,
    ) -> MagazineLayout:
        """Full pipeline entry point for editorial generation.

        Steps:
        a. Generate content via generate_content()
        b. Try generate_layout_image() -> if succeeds, parse_layout_image()
        c. If layout image OR parsing fails: use default template
        d. If layout image AND parsing succeed: build layout from parsed blocks
        e. Merge content into layout
        f. Return final MagazineLayout

        When feedback_history is provided (retry iteration), passes it through
        to generate_content for feedback-aware prompt construction.
        """
        # Step 1: Generate editorial content
        content = await self.generate_content(
            keyword,
            trend_context,
            feedback_history=feedback_history,
            previous_draft=previous_draft,
        )

        # Step 2 + 3: Try Nano Banana + Vision pipeline
        layout: MagazineLayout | None = None

        image_bytes = await self.generate_layout_image(
            keyword,
            content.title,
            num_sections=8,
        )

        if image_bytes is not None:
            parsed_blocks = await self.parse_layout_image(
                image_bytes,
                keyword,
            )
            if parsed_blocks is not None:
                layout = self._build_layout_from_parsed(
                    keyword,
                    content.title,
                    parsed_blocks,
                )

        # Fallback to default template
        if layout is None:
            layout = create_default_template(keyword, content.title)

        # Step 4: Merge content into layout
        return self.merge_content_into_layout(content, layout)

    def _build_layout_from_parsed(
        self,
        keyword: str,
        title: str,
        parsed_blocks: list[dict[str, Any]],
    ) -> MagazineLayout:
        """Build a MagazineLayout from Vision-parsed block definitions.

        Each parsed block is {"type": "hero", "order": 0, ...}.
        Creates appropriate block instances with empty/default content.
        """
        from editorial_ai.models.layout import (
            CreditEntry,
            DividerBlock,
            ImageGalleryBlock,
        )

        block_builders: dict[str, Any] = {
            "hero": lambda: HeroBlock(image_url=""),
            "headline": lambda: HeadlineBlock(text=""),
            "body_text": lambda: BodyTextBlock(paragraphs=[]),
            "image_gallery": lambda: ImageGalleryBlock(images=[]),
            "pull_quote": lambda: PullQuoteBlock(quote=""),
            "product_showcase": lambda: ProductShowcaseBlock(products=[]),
            "celeb_feature": lambda: CelebFeatureBlock(celebs=[]),
            "divider": lambda: DividerBlock(),
            "hashtag_bar": lambda: HashtagBarBlock(hashtags=[]),
            "credits": lambda: CreditsBlock(
                entries=[CreditEntry(role="AI Editor", name="decoded editorial")],
            ),
        }

        # Sort by order and build blocks
        sorted_blocks = sorted(
            parsed_blocks,
            key=lambda b: b.get("order", 0),
        )

        blocks = []
        for pb in sorted_blocks:
            block_type = pb.get("type", "")
            builder = block_builders.get(block_type)
            if builder:
                blocks.append(builder())

        if not blocks:
            return create_default_template(keyword, title)

        return MagazineLayout(
            keyword=keyword,
            title=title,
            blocks=blocks,
            metadata=[],
        )
