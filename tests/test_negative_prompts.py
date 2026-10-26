"""Unit tests for Context-Aware Dynamic Negative Prompt Formulation."""

import pytest
from core.models import Genre, NegativePromptStrategy
from core.prompt_adapter import NegativePromptCompiler


def test_cinematic_story_excludes_anti_photographic_tags():
    """Verify that cinematic photorealism never penalizes realistic photography in negatives."""
    neg = NegativePromptCompiler.build_negative_prompt(
        genre=Genre.CINEMATIC_STORY,
        art_style="photorealistic cinematic 35mm",
        strategy=NegativePromptStrategy.CINEMATIC_REALISTIC,
    )
    assert "realistic photography" not in neg
    assert "photorealistic" not in neg
    assert "cgi" in neg
    assert "3d render" in neg
    assert "plastic skin" in neg
    assert "distorted anatomy" in neg


def test_animated_style_penalizes_photorealism():
    """Verify that 3D animation and cartoon styles penalize photorealism and live action."""
    neg = NegativePromptCompiler.build_negative_prompt(
        genre=Genre.CINEMATIC_STORY,
        art_style="3D Pixar-inspired cartoon style",
        strategy=NegativePromptStrategy.ANIMATED_STYLIZED,
    )
    assert "photorealistic" in neg
    assert "live action" in neg
    assert "real life footage" in neg


def test_riddle_genre_penalizes_clutter_and_low_contrast():
    """Verify that riddles and visual puzzles penalize cluttered backgrounds and visual noise."""
    neg = NegativePromptCompiler.build_negative_prompt(
        genre=Genre.RIDDLE,
        strategy=NegativePromptStrategy.CLEAN_GRAPHICS,
    )
    assert "cluttered background" in neg
    assert "low contrast" in neg
    assert "visual noise" in neg


def test_custom_negative_overrides_default():
    """Verify that an explicit custom negative prompt takes precedence."""
    custom = "custom bad hands, text artifacts, custom watermark"
    neg = NegativePromptCompiler.build_negative_prompt(
        genre=Genre.CINEMATIC_STORY,
        custom_negative=custom,
    )
    assert neg == custom
