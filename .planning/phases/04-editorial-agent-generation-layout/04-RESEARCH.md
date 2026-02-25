# Phase 4: Editorial Agent - Generation + Layout - Research

**Researched:** 2026-02-25
**Domain:** Gemini structured output, Nano Banana image generation, Magazine Layout JSON schema design, Vision-to-JSON parsing
**Confidence:** MEDIUM

## Summary

Phase 4 implements an editorial node that takes curated keywords + trend context from Phase 3, generates editorial content via Gemini structured output, generates a magazine layout design image via Nano Banana (Gemini 2.5 Flash Image), then parses that image into a structured Magazine Layout JSON. The JSON schema serves as the contract for the frontend renderer (decoded-editorial).

The core technical pipeline has three distinct steps: (1) LLM editorial content generation with Gemini structured output, (2) Nano Banana layout image generation, and (3) Vision AI parsing of the layout image into JSON structure. The existing project already uses the native `google-genai` SDK (v1.64.0) which supports all three capabilities -- structured output via `response_schema` + `response_mime_type`, image generation via `response_modalities=["IMAGE"]`, and vision understanding by passing images to `generate_content`.

The key risk is Step 3: converting a generated layout image into reliable JSON structure. This is a novel pipeline pattern where a Gemini vision call must interpret a generated magazine layout and map it to a predefined block schema. Confidence in this step is LOW; a robust fallback to default templates is essential.

**Primary recommendation:** Use the native `google-genai` SDK for all three steps (content generation, image generation, vision parsing). Use a block-based schema with predefined section types. Design the schema to be renderable without Nano Banana (pure template fallback). Build the OutputFixingParser equivalent as a lightweight custom retry loop since `langchain` (full package) is not installed and adding it as a dependency is unnecessary.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `google-genai` | 1.64.0 | Gemini structured output, Nano Banana image gen, Vision parsing | Already installed; native SDK supports all three capabilities needed; proven in curation service |
| `pydantic` | 2.12.5 | Magazine Layout JSON schema, validation, versioning | Already installed; `response_schema` accepts Pydantic types directly; `model_validate_json()` for parsing |
| `langgraph` | 1.0.9 | Editorial node orchestration | Already the pipeline framework |
| `Pillow` (PIL) | - | Image handling for Nano Banana response | Needed to handle `part.inline_data` from image generation responses; convert to bytes for vision input |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `tenacity` | 9.1.4 | Retry for API calls and output repair | Already installed (transitive); wrap generation + parsing calls |
| `langchain-google-genai` | 4.2.1 | Existing LLM factory (`create_llm`) | NOT used in this phase; editorial service uses native SDK directly like curation service |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom output repair loop | LangChain `OutputFixingParser` | Would require adding `langchain` as full dependency; custom loop is simpler and follows project pattern from curation service |
| Native `google-genai` for structured output | `langchain-google-genai` `.with_structured_output()` | LangChain wrapper adds complexity; native SDK `response_schema` accepts Pydantic directly; curation service already proved the native SDK pattern |
| Gemini Vision for layout parsing | Dedicated layout parsing service | External services add latency and cost; Gemini vision is already available through the SDK and can output structured JSON |
| Block-based schema | Free-form CSS/layout coordinates | Free-form requires complex frontend renderer; block-based is simpler, more reliable, and easier to validate |

**Installation:**
```bash
uv add Pillow
```

## Architecture Patterns

### Recommended Project Structure
```
src/editorial_ai/
├── models/
│   └── editorial.py         # MagazineLayout, Section, Block Pydantic models
├── nodes/
│   └── editorial.py         # LangGraph editorial node (calls service, writes state)
├── services/
│   └── editorial_service.py # 3-step pipeline: content gen + layout gen + vision parse
├── prompts/
│   └── editorial.py         # Prompt templates for content gen, layout gen, vision parse
├── templates/
│   └── default_layouts.py   # Fallback layout templates when Nano Banana fails
├── llm.py                   # Existing (unchanged)
├── state.py                 # Add editorial output fields
└── graph.py                 # Wire real editorial node
```

### Pattern 1: Three-Step Editorial Pipeline
**What:** Sequential pipeline within the editorial service: (1) Generate editorial content as structured JSON, (2) Generate layout image via Nano Banana, (3) Parse layout image to JSON via Vision AI, (4) Merge content into layout structure.
**When to use:** Every editorial generation call.
**Example:**
```python
# Source: native google-genai SDK docs + project curation_service.py pattern
class EditorialService:
    def __init__(self, client: genai.Client, *, model: str | None = None):
        self.client = client
        self.model = model or settings.default_model
        self.image_model = "gemini-2.5-flash-image"

    async def generate_editorial(
        self, keyword: str, context: list[dict]
    ) -> MagazineLayout:
        # Step 1: Generate editorial content
        content = await self._generate_content(keyword, context)

        # Step 2: Generate layout image via Nano Banana
        layout_image = await self._generate_layout_image(keyword, content)

        # Step 3: Parse layout image to JSON structure
        if layout_image:
            layout = await self._parse_layout_image(layout_image, content)
        else:
            layout = self._get_default_layout(content)

        return layout
```

### Pattern 2: Gemini Native Structured Output with Pydantic
**What:** Pass Pydantic model class directly to `response_schema` in the native google-genai SDK. The response text is valid JSON matching the schema.
**When to use:** Editorial content generation (Step 1) and Vision layout parsing (Step 3).
**Example:**
```python
# Source: google-genai SDK docs, geminibyexample.com/020-structured-output
from google.genai import types

response = await self.client.aio.models.generate_content(
    model=self.model,
    contents=prompt,
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=EditorialContent,  # Pydantic model class
        temperature=0.7,
    ),
)
# Parse response
content = EditorialContent.model_validate_json(response.text)
```

**Important:** `response_schema` in google-genai SDK v1.64.0 accepts `Union[dict, type, Schema, GenericAlias, UnionType]`. Pydantic BaseModel subclasses are accepted as `type`. However, `response.parsed` is NOT available in v1.64.0; use `response.text` + `model_validate_json()`.

### Pattern 3: Nano Banana Image Generation
**What:** Use `gemini-2.5-flash-image` model with `response_modalities=["IMAGE"]` to generate magazine layout designs.
**When to use:** Step 2 of the pipeline -- after content is generated, before layout parsing.
**Example:**
```python
# Source: google-genai SDK docs, dev.to Nano Banana tutorial
from google.genai import types
from PIL import Image
from io import BytesIO

response = await self.client.aio.models.generate_content(
    model="gemini-2.5-flash-image",
    contents=layout_prompt,
    config=types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=types.ImageConfig(aspect_ratio="9:16"),  # portrait magazine
    ),
)

# Extract image from response parts
for part in response.candidates[0].content.parts:
    if part.inline_data is not None:
        image_bytes = part.inline_data.data
        image = Image.open(BytesIO(image_bytes))
        return image_bytes  # pass to vision parsing step
```

### Pattern 4: Vision AI Layout Parsing (Image -> JSON)
**What:** Pass the generated layout image back to Gemini with a structured output config to extract layout structure as JSON.
**When to use:** Step 3 -- converting the Nano Banana design image into structured Layout JSON.
**Example:**
```python
# Source: google-genai SDK image understanding docs
from google.genai import types

response = await self.client.aio.models.generate_content(
    model=self.model,  # gemini-2.5-flash for vision
    contents=[
        vision_parse_prompt,
        types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
    ],
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=LayoutStructure,  # Pydantic model for layout blocks
        temperature=0.0,  # deterministic parsing
    ),
)
layout = LayoutStructure.model_validate_json(response.text)
```

**Critical note:** Vision + structured output CAN be combined (unlike grounding + structured output in Phase 3). This is because vision understanding is a native model capability, not a tool.

### Pattern 5: Custom Output Repair Loop
**What:** Lightweight retry pattern that catches Pydantic validation errors and sends the error + malformed output back to Gemini for correction. Replaces `OutputFixingParser` without needing the full `langchain` package.
**When to use:** When structured output fails validation.
**Example:**
```python
# Custom repair loop (replaces LangChain OutputFixingParser)
async def generate_with_repair(
    self,
    client: genai.Client,
    model: str,
    contents: str | list,
    schema: type[BaseModel],
    *,
    max_retries: int = 2,
    config_overrides: dict | None = None,
) -> BaseModel:
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema,
        temperature=0.0,
        **(config_overrides or {}),
    )

    response = await client.aio.models.generate_content(
        model=model, contents=contents, config=config,
    )

    for attempt in range(max_retries + 1):
        try:
            return schema.model_validate_json(response.text)
        except ValidationError as e:
            if attempt == max_retries:
                raise
            # Send error back for repair
            repair_prompt = (
                f"The following JSON failed validation:\n{response.text}\n\n"
                f"Errors:\n{e}\n\nFix the JSON to match the schema."
            )
            response = await client.aio.models.generate_content(
                model=model, contents=repair_prompt, config=config,
            )
    raise RuntimeError("Unreachable")
```

### Anti-Patterns to Avoid
- **Combining grounding tools with structured output:** Gemini 2.5 cannot use Google Search Grounding and `response_schema` simultaneously. Phase 4 does NOT need grounding (content comes from curation context), so this is not an issue here.
- **Overly complex Pydantic schema for Gemini:** Deeply nested schemas with many optional fields can cause Gemini to produce invalid output. Keep the schema relatively flat with clear field descriptions.
- **Relying solely on Nano Banana output:** The layout image parsing is inherently unreliable. Always have a fallback template path.
- **Storing full content in LangGraph state:** Follow the lean state principle. Store only the draft ID or a reference; persist the full Layout JSON externally.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Image generation | Custom image API integration | `google-genai` SDK with `gemini-2.5-flash-image` | SDK handles all authentication, response parsing, image format conversion |
| JSON validation | Custom JSON validator | Pydantic `model_validate_json()` | Pydantic provides type coercion, field validation, clear error messages |
| Retry with backoff | Custom sleep loops | `tenacity` decorators | Already installed; handles jitter, exponential backoff, exception filtering |
| Image byte handling | Manual base64 decode | `part.inline_data.data` + PIL | SDK returns raw bytes directly; PIL handles all image format details |
| Schema versioning | Custom version tracking | Pydantic `schema_version` field + model inheritance | Pydantic discriminated unions can handle schema migration |

**Key insight:** The native `google-genai` SDK handles all three major operations (structured output, image generation, vision understanding) through the same `generate_content` API. No additional libraries needed for the core pipeline.

## Common Pitfalls

### Pitfall 1: Vision Parsing Produces Inconsistent Layout Structures
**What goes wrong:** The same layout image can produce different JSON structures across multiple parsing attempts. Section counts, types, and positions vary.
**Why it happens:** Vision AI interpretation of layout designs is inherently subjective. The model may identify 3 sections one time and 5 the next.
**How to avoid:** (1) Use a constrained Pydantic schema with `response_schema` to force consistent structure. (2) Use very specific vision prompts that enumerate exactly what to look for. (3) Set `temperature=0.0` for deterministic parsing. (4) Validate and fill in any gaps with template defaults.
**Warning signs:** Test the same image multiple times and compare outputs. If they differ significantly, the prompt needs improvement.

### Pitfall 2: Nano Banana Layout Quality Varies Widely
**What goes wrong:** Some generated layouts look like professional magazine spreads; others are incoherent or text-heavy mockups.
**Why it happens:** Image generation is stochastic. Prompt engineering heavily affects quality. Fashion editorial layout is a niche domain.
**How to avoid:** (1) Develop detailed prompts with specific layout instructions (grid, section placement, whitespace). (2) Iterate on prompts with test runs. (3) Always have the template fallback ready. (4) Consider a "quality gate" -- if the vision parser can't extract a valid structure, use the template.
**Warning signs:** Generated images that contain lots of placeholder text, overlapping elements, or no clear section boundaries.

### Pitfall 3: Gemini Structured Output Schema Limitations
**What goes wrong:** Complex Pydantic schemas with `Union` types, deeply nested optionals, or `dict[str, Any]` fields cause Gemini to output invalid JSON or fail silently.
**Why it happens:** The Gemini structured output engine has limitations on schema complexity. Known issue: `dict[str, Any]` is not supported (github.com/googleapis/python-genai/issues/1113).
**How to avoid:** (1) Keep schemas relatively flat. (2) Use specific types instead of `Any`. (3) Use `list[SpecificModel]` instead of `dict[str, Any]`. (4) Use `Literal` types for discriminated fields. (5) Test the schema with the actual API before building the full pipeline.
**Warning signs:** `response.text` returns empty or partially filled JSON; Pydantic validation catches unexpected types.

### Pitfall 4: Image Generation Response Handling
**What goes wrong:** Assuming `response.candidates[0].content.parts[0]` always contains an image. The response may contain text parts, no parts, or error candidates.
**Why it happens:** Image generation can fail silently or return safety-filtered responses.
**How to avoid:** (1) Always iterate through `response.parts` and check for `part.inline_data`. (2) Handle the case where no image is generated (fallback to template). (3) Check `response.candidates` is not empty. (4) Catch `ValueError` from `as_image()` calls.
**Warning signs:** `NoneType` errors when accessing response parts; empty candidates list.

### Pitfall 5: Lean State Violation
**What goes wrong:** Storing the full Magazine Layout JSON (which can be large with image references) directly in LangGraph state.
**Why it happens:** Convenience of having everything in state.
**How to avoid:** Follow the project's lean state principle (established in Phase 1). Store only a `current_draft_id` in state. Persist the full Layout JSON to Supabase or a separate store. The editorial node returns the draft ID.
**Warning signs:** State size growing beyond the ~10KB threshold established in Phase 2.

## Magazine Layout JSON Schema Design

### Recommendation: Block-Based Schema

After researching fashion magazine layout patterns, the recommendation is a **block-based schema** over free-form layout coordinates. Rationale:

1. **Renderable by simple frontend:** Blocks map to React components; free-form coordinates require a canvas renderer
2. **Reliable Gemini output:** Blocks are enumerable types that structured output handles well; pixel coordinates are noisy
3. **Template fallback friendly:** Default templates are simply predefined block sequences
4. **Validatable:** Each block type has a known structure; Pydantic discriminated unions work naturally

### Recommended Section/Block Types

Based on fashion magazine layout pattern research:

| Block Type | Purpose | Example Content |
|------------|---------|-----------------|
| `hero` | Full-width hero image with overlay text | Main editorial title + hero image placeholder |
| `headline` | Large typography section | Editorial title, subtitle, author attribution |
| `body_text` | Body copy paragraph(s) | Main editorial text (500 chars max) |
| `image_gallery` | Grid or carousel of images | Celebrity/product image placeholders |
| `pull_quote` | Highlighted quote or callout | Key statement from the editorial |
| `product_showcase` | Product cards with details | Product image placeholder + name + brand |
| `celeb_feature` | Celebrity spotlight section | Celeb image placeholder + name + description |
| `divider` | Visual separator | Line, whitespace, or decorative element |
| `hashtag_bar` | Trending hashtags/keywords | Related hashtags from curation |
| `credits` | Attribution and sources | Sources, photographer credits |

### Schema Structure (Pydantic)

```python
from pydantic import BaseModel, Field
from typing import Literal

class ImagePlaceholder(BaseModel):
    """Placeholder for an image to be filled in Phase 5 from Supabase."""
    placeholder_id: str  # unique ID for this placeholder
    role: Literal["hero", "product", "celeb", "gallery", "background"]
    alt_text: str  # descriptive text for the image
    aspect_ratio: str = "1:1"  # suggested aspect ratio

class TextContent(BaseModel):
    """A piece of text content within a block."""
    text: str
    style: Literal["title", "subtitle", "body", "caption", "quote", "hashtag"] = "body"

class Block(BaseModel):
    """A single layout block in the magazine layout."""
    block_type: Literal[
        "hero", "headline", "body_text", "image_gallery",
        "pull_quote", "product_showcase", "celeb_feature",
        "divider", "hashtag_bar", "credits",
    ]
    order: int  # sequence position
    texts: list[TextContent] = Field(default_factory=list)
    images: list[ImagePlaceholder] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)  # NOTE: may need to be list[KeyValue] for Gemini compat

class MagazineLayout(BaseModel):
    """Complete magazine editorial layout."""
    schema_version: str = "1.0"
    keyword: str
    title: str
    subtitle: str = ""
    language: str = "ko"
    blocks: list[Block]
    generated_at: str  # ISO timestamp
    layout_source: Literal["nanobanana", "template"] = "template"
```

**WARNING:** The `metadata: dict[str, str]` field may cause issues with Gemini structured output (see Pitfall 3). If problems arise, replace with `metadata: list[KeyValuePair]` where `KeyValuePair` has `key: str` and `value: str` fields.

## Code Examples

### Complete Editorial Content Generation (Step 1)
```python
# Source: project curation_service.py pattern + google-genai structured output docs
from google.genai import types
from editorial_ai.models.editorial import EditorialContent

async def _generate_content(
    self, keyword: str, curated_topics: list[dict]
) -> EditorialContent:
    """Generate editorial text content from keyword and curation context."""
    prompt = build_editorial_prompt(keyword, curated_topics)

    response = await self.client.aio.models.generate_content(
        model=self.model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=EditorialContent,
            temperature=0.7,
        ),
    )

    try:
        return EditorialContent.model_validate_json(response.text)
    except ValidationError:
        # Attempt repair
        return await self._repair_output(response.text, EditorialContent)
```

### Nano Banana Layout Generation (Step 2)
```python
# Source: google-genai SDK image generation docs
async def _generate_layout_image(
    self, keyword: str, content: EditorialContent
) -> bytes | None:
    """Generate a magazine layout design image using Nano Banana."""
    prompt = build_layout_prompt(keyword, content)

    try:
        response = await self.client.aio.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio="9:16"),
            ),
        )

        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                return part.inline_data.data
        return None  # No image in response
    except Exception:
        logger.warning("Nano Banana layout generation failed for keyword=%s", keyword)
        return None
```

### Vision Layout Parsing (Step 3)
```python
# Source: google-genai image understanding + structured output docs
from editorial_ai.models.editorial import LayoutStructure

async def _parse_layout_image(
    self, image_bytes: bytes, content: EditorialContent
) -> LayoutStructure:
    """Parse a layout design image into structured JSON using Gemini Vision."""
    prompt = build_vision_parse_prompt(content)

    response = await self.client.aio.models.generate_content(
        model=self.model,
        contents=[
            prompt,
            types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=LayoutStructure,
            temperature=0.0,
        ),
    )

    return LayoutStructure.model_validate_json(response.text)
```

### Editorial Node (LangGraph Integration)
```python
# Source: project curation.py node pattern
from editorial_ai.services.editorial_service import EditorialService, get_genai_client
from editorial_ai.state import EditorialPipelineState

async def editorial_node(state: EditorialPipelineState) -> dict:
    """LangGraph node: generate editorial content from curated topics."""
    curated_topics = state.get("curated_topics") or []
    if not curated_topics:
        return {
            "pipeline_status": "failed",
            "error_log": ["Editorial generation failed: no curated topics"],
        }

    try:
        service = EditorialService(get_genai_client())
        # Generate for the first/primary topic
        primary_topic = curated_topics[0]
        layout = await service.generate_editorial(
            keyword=primary_topic["keyword"],
            context=curated_topics,
        )
        # Persist layout and get draft ID (placeholder for now)
        draft_id = f"draft_{primary_topic['keyword']}_{layout.generated_at}"
        return {
            "pipeline_status": "reviewing",
            "current_draft_id": draft_id,
        }
    except Exception as e:
        logger.exception("Editorial node failed")
        return {
            "pipeline_status": "failed",
            "error_log": [f"Editorial failed: {type(e).__name__}: {e!s}"],
        }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LangChain `OutputFixingParser` from `langchain` package | Native SDK `response_schema` + custom repair loop | 2025-2026 | Gemini native structured output is now reliable enough that full LangChain dependency is unnecessary |
| Manual JSON schema dict for Gemini | Pass Pydantic model directly to `response_schema` | 2025 (google-genai SDK) | SDK auto-converts Pydantic models; no manual schema dict needed |
| Separate image generation APIs (Imagen, DALL-E) | Gemini 2.5 Flash Image (Nano Banana) via same SDK | 2025 | Single SDK handles text, image gen, and vision; no additional API keys or libraries |
| CSS-based layout specification | Block-based JSON schema | Current best practice for AI-generated layouts | Blocks are more reliably generated by LLMs; CSS coordinates are too noisy |

## Open Questions

1. **Nano Banana layout parsing reliability**
   - What we know: Gemini Vision can parse images to JSON with structured output. It works well for documents and UI mockups.
   - What's unclear: How reliably it can parse a *generated* magazine layout image into a consistent block structure. The image itself is AI-generated and may lack clear boundaries.
   - Recommendation: Build and test the full pipeline early. If vision parsing is unreliable (>30% failure rate), consider an alternative approach: use Gemini to generate the layout structure directly as JSON (skipping the image generation step) and use Nano Banana only for decorative/background elements.
   - Confidence: LOW

2. **Pillow dependency**
   - What we know: PIL/Pillow is needed to handle image bytes from Nano Banana responses.
   - What's unclear: Whether `part.inline_data.data` returns raw bytes that can be directly passed to Vision without PIL conversion.
   - Recommendation: Add Pillow as dependency. Even if raw bytes work, PIL is useful for saving debug images and format conversion.
   - Confidence: MEDIUM

3. **`dict[str, str]` in Pydantic schema for Gemini**
   - What we know: There is a known issue (googleapis/python-genai#1113) where `dict[str, Any]` in Pydantic models causes schema validation errors with Gemini.
   - What's unclear: Whether `dict[str, str]` (with specific value type) is also affected.
   - Recommendation: Start with `dict[str, str]` for metadata fields. If it fails, convert to `list[KeyValuePair]`. Test early.
   - Confidence: LOW

4. **Content + Layout merge strategy**
   - What we know: Steps produce separate outputs (editorial text content + layout structure from vision). They need to be merged.
   - What's unclear: The exact merging algorithm -- how to map content pieces to layout blocks.
   - Recommendation: Design the content generation prompt to produce content keyed by block type. The merge step matches content to layout blocks by type.
   - Confidence: MEDIUM

5. **Async Nano Banana API availability**
   - What we know: The curation service uses `client.aio.models.generate_content` for async calls.
   - What's unclear: Whether image generation via `gemini-2.5-flash-image` is supported through the async API.
   - Recommendation: Assume it works (same API pattern). Test early and fall back to sync if needed.
   - Confidence: MEDIUM

## Sources

### Primary (HIGH confidence)
- google-genai SDK v1.64.0 installed locally -- verified `GenerateContentConfig` fields: `response_schema`, `response_mime_type`, `response_modalities`, `image_config` all present
- [Gemini Structured Output docs](https://ai.google.dev/gemini-api/docs/structured-output) -- `response_schema` accepts Pydantic types, `response_mime_type="application/json"`
- [Gemini Image Generation docs](https://ai.google.dev/gemini-api/docs/image-generation) -- Nano Banana model `gemini-2.5-flash-image`, response parts with `inline_data`
- [Gemini Image Understanding docs](https://ai.google.dev/gemini-api/docs/image-understanding) -- Vision + structured output can be combined; `types.Part.from_bytes()` for image input
- Project codebase: `curation_service.py` -- proven pattern for native SDK usage, async calls, structured output parsing

### Secondary (MEDIUM confidence)
- [Gemini by Example: Structured Output](https://geminibyexample.com/020-structured-output/) -- confirmed `response.parsed` NOT available, use `response.text` + `model_validate_json()`
- [Dev.to Nano Banana Tutorial](https://dev.to/googleai/how-to-build-with-nano-banana-complete-developer-tutorial-646) -- image response handling pattern
- [Nano Banana Magazine Mockup Prompts](https://nanobanana.pro/magazine-mockup-prompt) -- prompt engineering patterns for magazine layouts
- Fashion magazine layout design research -- block-based patterns (hero, gallery, pull quote, etc.)

### Tertiary (LOW confidence)
- [googleapis/python-genai#1113](https://github.com/googleapis/python-genai/issues/1113) -- `dict[str, Any]` schema issue (may or may not affect `dict[str, str]`)
- [LangChain OutputFixingParser](https://python.langchain.com/api_reference/langchain/output_parsers/langchain.output_parsers.fix.OutputFixingParser.html) -- reviewed for design inspiration; not usable without adding `langchain` dependency
- Vision-to-JSON layout parsing reliability -- no authoritative source found; based on general Gemini vision capabilities

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already installed or well-documented; native SDK capabilities verified locally
- Architecture: MEDIUM - three-step pipeline pattern is sound but vision parsing step (Step 3) is novel and unverified
- Schema design: MEDIUM - block-based approach is well-established pattern; specific block types informed by fashion editorial research
- Pitfalls: MEDIUM - identified from similar projects and known SDK issues; some pitfalls are speculative

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (30 days -- SDK is relatively stable; Nano Banana features may evolve)
