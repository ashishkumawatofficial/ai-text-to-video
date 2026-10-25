"""End-to-end integration test for Feature 003: Interactive Storyboard & Multi-Modal Director."""

import os
import pytest
from core.models import (
    ApprovalStatus,
    ConditioningMode,
    ReferenceAsset,
    Genre,
    VisualStrategyRoute,
    ModelCascadeConfig,
    ModelProvider
)
from core.session_manager import StoryboardSessionManager
from core.interactive_director import InteractiveDirector
from core.conditioning_engine import ConditioningEngine
from core.story_writer import StoryWriterGateway


def test_interactive_director_full_lifecycle(tmp_path):
    sessions_dir = str(tmp_path / "sessions")
    session_manager = StoryboardSessionManager(sessions_dir=sessions_dir)
    cfg = ModelCascadeConfig(provider=ModelProvider.OFFLINE)
    writer = StoryWriterGateway(cfg)
    director = InteractiveDirector(session_manager=session_manager, story_writer=writer, comfy_client=None)

    # 1. Create Storyboard
    prompt = "A brave astronaut discovering an ancient crystal on Mars"
    session = director.create_storyboard(prompt=prompt)

    assert session is not None
    assert session.approval_status == ApprovalStatus.PENDING_REVIEW
    assert len(session.plan.scenes) == 2
    assert session.plan.genre == Genre.CINEMATIC_STORY
    assert session.plan.total_duration_sec == 7.5

    beat1_orig_keyframe = session.plan.scenes[0].keyframe_image_path
    beat1_orig_dialogue = session.plan.scenes[0].dialogue_text
    beat2_orig_keyframe = session.plan.scenes[1].keyframe_image_path
    assert os.path.exists(beat1_orig_keyframe)
    assert os.path.exists(beat2_orig_keyframe)

    # 2. Conversational Delta Modification
    mod_instruction = "modify 2 make the crystal glowing purple and remove the voiceover"
    updated_session = director.apply_modification(session.session_id, mod_instruction)

    assert updated_session is not None
    assert updated_session.approval_status == ApprovalStatus.MODIFICATIONS_REQUESTED
    assert len(updated_session.history) == 1
    assert updated_session.history[0].modified_beats == [2]

    # Beat 1 MUST remain untouched
    assert updated_session.plan.scenes[0].keyframe_image_path == beat1_orig_keyframe
    assert updated_session.plan.scenes[0].dialogue_text == beat1_orig_dialogue

    # Beat 2 MUST have updated visual and muted dialogue
    assert "purple" in updated_session.plan.scenes[1].visual_prompt
    assert updated_session.plan.scenes[1].dialogue_text is None
    assert updated_session.plan.scenes[1].keyframe_image_path != beat2_orig_keyframe

    # 3. Approval Gate
    approved_session = director.approve_session(session.session_id)
    assert approved_session.approval_status == ApprovalStatus.APPROVED

    # 4. Project Conversion
    project = director.convert_plan_to_video_project(approved_session.plan)
    assert project.title == approved_session.plan.title
    assert project.genre == Genre.CINEMATIC_STORY
    assert len(project.scenes) == 2
    assert project.scenes[1].dialogue_text is None
    assert project.scenes[0].image_assets[0].file_path == beat1_orig_keyframe


def test_multi_modal_character_ingestion_and_conditioning(tmp_path):
    sessions_dir = str(tmp_path / "sessions")
    session_manager = StoryboardSessionManager(sessions_dir=sessions_dir)
    cfg = ModelCascadeConfig(provider=ModelProvider.OFFLINE)
    writer = StoryWriterGateway(cfg)
    director = InteractiveDirector(session_manager=session_manager, story_writer=writer, comfy_client=None)

    # Mock character plate
    char_plate = str(tmp_path / "detective_headshot.jpg")
    with open(char_plate, "wb") as f:
        f.write(b"dummy image data")

    references = {
        "detective_ren": ReferenceAsset(
            tag="detective_ren",
            role="character",
            file_path=char_plate
        )
    }

    prompt = "Detective Ren corners an android in the rain. Action strike then arrest."
    session = director.create_storyboard(
        prompt=prompt,
        references=references,
        genre_override=Genre.ACTION
    )

    assert session.approval_status == ApprovalStatus.PENDING_REVIEW
    beats = session.plan.scenes
    assert len(beats) >= 2

    # Beat 1 binds character plate and uses START_FRAME_ONLY
    assert beats[0].conditioning_mode == ConditioningMode.START_FRAME_ONLY
    assert beats[0].start_frame_path == char_plate
    assert "detective_ren" in beats[0].character_references

    # Beat 2 with whip pan is classified as HARD_CUT
    assert beats[1].conditioning_mode == ConditioningMode.HARD_CUT

    # Convert to project
    project = director.convert_plan_to_video_project(session.plan)
    assert project.genre == Genre.ACTION
    assert project.scenes[0].visual_strategy == VisualStrategyRoute.FLAT_RATE_DIFFUSION
