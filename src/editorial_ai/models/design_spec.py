"""Pydantic models for AI-generated design specifications.

DesignSpec captures the visual identity for each editorial: fonts, colors,
layout density, mood, and hero aspect ratio. Generated dynamically by Gemini
from the curated keyword so every piece of content has a unique theme.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class FontPairing(BaseModel):
    """Google Fonts font pairing for editorial typography."""

    model_config = ConfigDict(from_attributes=True)

    headline_font: str
    body_font: str
    accent_font: str | None = None


class ColorPalette(BaseModel):
    """Hex color palette for editorial theming."""

    model_config = ConfigDict(from_attributes=True)

    primary: str
    secondary: str
    accent: str
    background: str = "#ffffff"
    text: str = "#1a1a1a"
    muted: str = "#6b7280"


class DesignSpec(BaseModel):
    """Complete design specification for a magazine editorial.

    Generated per-keyword by Gemini, consumed by the frontend renderer
    to apply dynamic theming (fonts, colors, spacing, mood).
    """

    model_config = ConfigDict(from_attributes=True)

    font_pairing: FontPairing
    color_palette: ColorPalette
    layout_density: Literal["compact", "normal", "spacious"]
    mood: str
    hero_aspect_ratio: str = "16/9"
    drop_cap: bool = True


def default_design_spec() -> DesignSpec:
    """Return a sensible default DesignSpec for fallback scenarios."""
    return DesignSpec(
        font_pairing=FontPairing(
            headline_font="Georgia",
            body_font="Pretendard",
            accent_font=None,
        ),
        color_palette=ColorPalette(
            primary="#1a1a2e",
            secondary="#16213e",
            accent="#e94560",
            background="#ffffff",
            text="#1a1a1a",
            muted="#6b7280",
        ),
        layout_density="normal",
        mood="elegant editorial",
        hero_aspect_ratio="16/9",
        drop_cap=True,
    )
