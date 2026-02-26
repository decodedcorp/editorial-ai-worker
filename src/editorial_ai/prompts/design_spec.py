"""Prompt builder for AI-driven design spec generation.

Builds a system prompt that instructs Gemini to generate a DesignSpec JSON
matching the Pydantic schema, using only curated Google Fonts.
"""

from __future__ import annotations


def build_design_spec_prompt(keyword: str, category: str | None = None) -> str:
    """Build a prompt for Gemini to generate a DesignSpec JSON.

    Args:
        keyword: The curated keyword / editorial topic.
        category: Optional content category for additional context.

    Returns:
        A prompt string that produces valid DesignSpec JSON.
    """
    category_line = f"\nContent category: {category}" if category else ""

    return f"""You are a creative director for a high-end fashion editorial magazine.
Generate a design specification (theme) for an editorial about: "{keyword}"{category_line}

Output ONLY valid JSON matching this exact schema:

{{
  "font_pairing": {{
    "headline_font": "<Google Font name for headlines>",
    "body_font": "<Google Font name for body text>",
    "accent_font": "<Google Font name for pull quotes, or null>"
  }},
  "color_palette": {{
    "primary": "<hex color>",
    "secondary": "<hex color>",
    "accent": "<hex color>",
    "background": "<hex color, default #ffffff>",
    "text": "<hex color, default #1a1a1a>",
    "muted": "<hex color, default #6b7280>"
  }},
  "layout_density": "<compact | normal | spacious>",
  "mood": "<1-2 word mood descriptor, e.g. 'elegant minimal', 'bold urban'>",
  "hero_aspect_ratio": "<CSS aspect-ratio: 16/9, 4/3, 3/2, or 21/9>",
  "drop_cap": <true or false>
}}

FONT RULES — choose ONLY from these curated Google Fonts:
  Serif: Playfair Display, Lora, Noto Serif KR, DM Serif Display, Cormorant Garamond
  Sans-serif: Gothic A1, Noto Sans KR, Inter, Montserrat, Raleway

DESIGN GUIDELINES:
- Choose fonts that match the mood/tone of the keyword
- Pick colors that evoke the right editorial atmosphere for "{keyword}"
- Use layout_density to control whitespace: compact for dense info, spacious for luxury
- Hero aspect ratio: 16/9 (standard), 4/3 (portrait-leaning), 3/2 (classic photo), 21/9 (cinematic)
- drop_cap=true for classic editorial feel, false for modern/minimal
- mood should be a concise 1-2 word descriptor capturing the visual feeling

Output JSON only, no markdown fences, no explanation."""
