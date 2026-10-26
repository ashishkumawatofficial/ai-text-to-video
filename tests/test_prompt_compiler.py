"""Contract and unit tests for Late-Stage Render-Time Prompt Compilation."""

import json
import os
import pytest
from core.models import (
    VideoGenerationModality,
    VideoAudioMode,
    Genre,
    CompiledRenderPrompt,
)
from core.prompt_adapter import PromptCompiler, NegativePromptCompiler


def test_prompt_compiler_contract_schema_validation():
    """Verify CompiledRenderPrompt conforms to prompt_compiler_contract.json schema."""
    contract_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "specs",
            "011-prompt-synthesis-upgrade",
            "contracts",
            "prompt_compiler_contract.json",
        )
    )
    assert os.path.exists(contract_path)
    with open(contract_path, "r") as f:
        schema = json.load(f)

    compiler = PromptCompiler()
    compiled = compiler.compile_beat(
        prompt="A brave knight strides through a misty enchanted forest with glowing trees",
        model_id="kling-v1.5",
        modality=VideoGenerationModality.TEXT_TO_VIDEO,
        audio_mode=VideoAudioMode.EXTERNAL_SYNTHESIS,
        genre=Genre.CINEMATIC_STORY,
    )

    data = compiled.model_dump()
    for req in schema["required"]:
        assert req in data
    assert data["character_count"] == len(data["positive_prompt"])
    assert data["token_budget_safe"] is True


def test_prompt_compiler_minimax_audio_syntax():
    """Verify minimax-h3 receives <d> tags when native audio is active."""
    compiler = PromptCompiler()
    compiled = compiler.compile_beat(
        prompt="Detective walks into the smoky office and shuts the blinds",
        model_id="minimax-h3",
        modality=VideoGenerationModality.IMAGE_TO_VIDEO,
        audio_mode=VideoAudioMode.NATIVE_CLIP_AUDIO,
        dialogue_text="We have a serious problem here.",
    )
    assert "<d>We have a serious problem here.</d>" in compiled.positive_prompt
    assert compiled.audio_markup_applied is True
    assert compiled.is_kinetic_filtered is True


def test_prompt_compiler_kling_audio_syntax():
    """Verify kling-v2.0 receives Spoken line format when native audio is active."""
    compiler = PromptCompiler()
    compiled = compiler.compile_beat(
        prompt="Astronaut floating in deep space looking back at Earth",
        model_id="kling-v2.0",
        modality=VideoGenerationModality.TEXT_TO_VIDEO,
        audio_mode=VideoAudioMode.NATIVE_CLIP_AUDIO,
        dialogue_text="Ground control, do you copy?",
    )
    assert 'Spoken line: "Ground control, do you copy?"' in compiled.positive_prompt
    assert compiled.audio_markup_applied is True


def test_prompt_compiler_character_budgeting_runway():
    """Verify prompt adapts within Runway's compact safe character limits."""
    compiler = PromptCompiler()
    long_prompt = "A high-speed cybernetic vehicle chasing rogue drones through rain-soaked skyscrapers. " * 25
    compiled = compiler.compile_beat(
        prompt=long_prompt,
        model_id="runway-gen3-alpha",
        modality=VideoGenerationModality.TEXT_TO_VIDEO,
    )
    assert len(compiled.positive_prompt) <= 1000
    assert compiled.token_budget_safe is True
