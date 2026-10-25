"""Unit tests for ConditioningEngine (frame conditioning classification & reference binding)."""

import pytest
from core.models import (
    SceneBeatPlan,
    DirectorMasterPlan,
    ConditioningMode,
    ReferenceAsset,
    Genre
)
from core.conditioning_engine import ConditioningEngine


def test_classify_scene1_default_and_pure_t2v():
    beat1 = SceneBeatPlan(
        beat_index=1,
        name="The Call",
        duration_sec=3.5,
        visual_prompt="Astronaut stepping out onto red Martian sand",
        dialogue_text="First step"
    )
    # Default for scene 1 with subject
    mode1 = ConditioningEngine.classify_beat_conditioning(beat1, previous_beat=None)
    assert mode1 == ConditioningMode.START_FRAME_ONLY

    # Pure ambient/fluid scene 1
    beat_ambient = SceneBeatPlan(
        beat_index=1,
        name="Nebula Dust",
        duration_sec=3.0,
        visual_prompt="Cosmic nebula clouds drifting in deep space",
        dialogue_text=None
    )
    mode_ambient = ConditioningEngine.classify_beat_conditioning(beat_ambient, previous_beat=None)
    assert mode_ambient == ConditioningMode.PURE_T2V


def test_classify_continuous_chaining_vs_hard_cut():
    beat1 = SceneBeatPlan(
        beat_index=1,
        name="Walking",
        duration_sec=3.5,
        visual_prompt="Astronaut walking across desert",
        camera_movement="slow_push_in"
    )

    # Continuous action
    beat2_continuous = SceneBeatPlan(
        beat_index=2,
        name="Lifting",
        duration_sec=4.0,
        visual_prompt="Astronaut continues lifting the ancient glowing crystal",
        camera_movement="slow_push_in"
    )
    mode2 = ConditioningEngine.classify_beat_conditioning(beat2_continuous, previous_beat=beat1)
    assert mode2 == ConditioningMode.CHAIN_FROM_PREVIOUS

    # Hard editorial cut
    beat2_cut = SceneBeatPlan(
        beat_index=2,
        name="Reaction",
        duration_sec=3.0,
        visual_prompt="Whip pan cut to extreme close-up of visor reflections",
        camera_movement="whip_pan_right"
    )
    mode_cut = ConditioningEngine.classify_beat_conditioning(beat2_cut, previous_beat=beat1)
    assert mode_cut == ConditioningMode.HARD_CUT


def test_classify_explicit_boundary_frames():
    beat = SceneBeatPlan(
        beat_index=1,
        name="Transformation",
        duration_sec=3.0,
        visual_prompt="Sword drawing"
    )
    # Start and End frame provided
    mode_both = ConditioningEngine.classify_beat_conditioning(
        beat,
        previous_beat=None,
        explicit_start_frame="path/start.jpg",
        explicit_end_frame="path/end.jpg"
    )
    assert mode_both == ConditioningMode.START_AND_END_FRAME

    # Only Start frame provided
    mode_start = ConditioningEngine.classify_beat_conditioning(
        beat,
        previous_beat=None,
        explicit_start_frame="path/start.jpg"
    )
    assert mode_start == ConditioningMode.START_FRAME_ONLY


def test_bind_references_to_plan():
    plan = DirectorMasterPlan(
        title="Cyber Detective",
        genre=Genre.CINEMATIC_STORY,
        total_duration_sec=7.0,
        scenes=[
            SceneBeatPlan(
                beat_index=1,
                name="Rainy Street",
                duration_sec=3.5,
                visual_prompt="Detective Ren stands in neon rain in Sector 4",
                dialogue_text="Shadows in the rain"
            ),
            SceneBeatPlan(
                beat_index=2,
                name="Discovery",
                duration_sec=3.5,
                visual_prompt="Close up of cyber chip in dark alley",
                dialogue_text="The chip is found"
            )
        ]
    )

    references = {
        "detective_ren": ReferenceAsset(
            tag="detective_ren",
            file_path="assets/detective.jpg",
            role="character",
            description="cyberpunk trenchcoat detective"
        ),
        "sector_4": ReferenceAsset(
            tag="sector_4",
            file_path="assets/city.jpg",
            role="environment",
            description="neon rainy city alley"
        )
    }

    updated_plan = ConditioningEngine.bind_references_to_plan(plan, references)

    assert "detective_ren" in updated_plan.scenes[0].character_references
    assert updated_plan.scenes[0].environment_reference == "sector_4"
