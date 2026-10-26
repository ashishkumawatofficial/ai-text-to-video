"""Unit tests for model-aware prompt adaptation, character limit budgeting, and semantic compression."""

import pytest
from core.models import VideoGenerationModality, VideoAudioMode
from core.prompt_adapter import PromptAdapter


@pytest.fixture
def adapter():
    return PromptAdapter()


def test_prompt_fits_under_limit_unchanged(adapter):
    short_prompt = "A detective walking down a misty neon-lit alleyway, cinematic tracking shot."
    res = adapter.adapt_prompt(
        prompt=short_prompt,
        model_id="kling-v1.5",
        modality=VideoGenerationModality.TEXT_TO_VIDEO,
    )
    assert res.char_count == len(short_prompt)
    assert not res.is_compressed
    assert res.adapted_prompt == short_prompt


def test_prompt_compressed_for_runway_gen3(adapter):
    # Long prompt > 1,500 characters with redundant filler
    base_story = "Detective Evelyn Vance investigates a glowing encrypted terminal inside a rain-drenched cyberpunk warehouse. "
    filler = "Ultra-realistic, hyper-detailed, 8k resolution, award winning, masterpiece, trending on artstation, unreal engine 5 render, cinematic lighting, sharp focus, ray tracing, photorealistic, intricate details. "
    background = "In the far background, neon signs flicker in kanji characters while holographic advertisements glitch intermittently against the chrome metal scaffolding. Steam billows from industrial exhaust vents above. "
    
    long_prompt = (base_story * 4) + (filler * 5) + (background * 3)
    assert len(long_prompt) > 1500

    res = adapter.adapt_prompt(
        prompt=long_prompt,
        model_id="runway-gen3-alpha",  # hard limit 1,000 chars
        modality=VideoGenerationModality.TEXT_TO_VIDEO,
    )

    assert res.char_count <= 1000
    assert res.is_compressed
    assert "Detective Evelyn Vance" in res.adapted_prompt
    # Redundant filler should be stripped
    assert "trending on artstation" not in res.adapted_prompt


def test_open_weights_token_budgeting_cogvideox_and_wan(adapter):
    long_prompt = ("A high-speed cybernetic drone weaves through towering concrete skyscrapers at dusk, dodging automated laser grid defenses. " * 12).strip()
    assert len(long_prompt) > 1200

    # CogVideoX has a 750 char limit (226 tokens)
    res_cog = adapter.adapt_prompt(
        prompt=long_prompt,
        model_id="cogvideox-5b",
        modality=VideoGenerationModality.TEXT_TO_VIDEO,
    )
    assert res_cog.char_count <= 750
    assert res_cog.is_compressed

    # Wan 2.1 has a 1,200 char limit (512 tokens)
    res_wan = adapter.adapt_prompt(
        prompt=long_prompt,
        model_id="wan-2.1-t2v-14b",
        modality=VideoGenerationModality.TEXT_TO_VIDEO,
    )
    assert res_wan.char_count <= 1200


def test_model_switching_expands_budget(adapter):
    prompt_2000 = ("A majestic mechanical dragon soaring through aurora borealis clouds. " * 28).strip()
    prompt_2000 = prompt_2000[:2200].strip()

    # Kling 1.0 has 1,500 limit -> will be compressed
    res_1 = adapter.adapt_prompt(
        prompt=prompt_2000,
        model_id="kling-v1.0",
    )
    assert res_1.char_count <= 1500
    assert res_1.is_compressed

    # Kling 1.5 has 3,072 limit -> fits without compression
    res_2 = adapter.adapt_prompt(
        prompt=prompt_2000,
        model_id="kling-v1.5",
    )
    assert res_2.char_count == len(prompt_2000)
    assert not res_2.is_compressed


def test_kinetic_i2v_transform_preserves_action_prepositions(adapter):
    """Verify that action prepositions ('strikes with glowing sword') are preserved while static attire is pruned."""
    prompt = "A cybernetic ninja wearing black silk robe strikes with glowing energy blade against the robotic guard."
    res = adapter.adapt_prompt(
        prompt=prompt,
        model_id="kling-v1.5",
        modality=VideoGenerationModality.IMAGE_TO_VIDEO,
    )
    # Attire stripped
    assert "wearing black silk robe" not in res.adapted_prompt
    # Action preposition preserved
    assert "strikes with glowing energy blade" in res.adapted_prompt


def test_kinetic_i2v_transform_injects_fallback_for_purely_static_prompt(adapter):
    """Verify that when a prompt has no motion verbs, a safe kinetic motion is injected."""
    prompt = "A serene mountain lake surrounded by pine trees standing in front of rocky peaks"
    res = adapter.adapt_prompt(
        prompt=prompt,
        model_id="kling-v1.5",
        modality=VideoGenerationModality.IMAGE_TO_VIDEO,
    )
    assert "camera" in res.adapted_prompt.lower() or "motion" in res.adapted_prompt.lower()
