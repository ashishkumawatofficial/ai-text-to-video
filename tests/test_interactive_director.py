"""Unit tests for InteractiveDirector (storyboard planning, approval gate, delta editing, and project conversion)."""

import os
import shutil
import pytest
from core.models import (
    ApprovalStatus,
    Genre,
    ConditioningMode,
    ReferenceAsset,
    ModelCascadeConfig,
    ModelProvider
)
from core.session_manager import StoryboardSessionManager
from core.interactive_director import InteractiveDirector
from core.story_writer import StoryWriterGateway


@pytest.fixture
def temp_dir(tmp_path):
    dir_path = str(tmp_path / "interactive_test_sessions")
    os.makedirs(dir_path, exist_ok=True)
    yield dir_path
    shutil.rmtree(dir_path, ignore_errors=True)


@pytest.fixture
def offline_director(temp_dir):
    session_manager = StoryboardSessionManager(temp_dir)
    cfg = ModelCascadeConfig(provider=ModelProvider.OFFLINE)
    writer = StoryWriterGateway(cfg)
    return InteractiveDirector(session_manager, story_writer=writer, comfy_client=None)


def test_create_storyboard_halts_at_pending_review(offline_director):
    director = offline_director

    session = director.create_storyboard("A brave astronaut discovering an ancient crystal on Mars")

    assert session is not None
    assert session.approval_status == ApprovalStatus.PENDING_REVIEW
    assert session.plan.genre == Genre.CINEMATIC_STORY
    assert len(session.plan.scenes) >= 2

    # Check keyframe synthesis
    assert session.plan.scenes[0].keyframe_image_path is not None
    assert session.plan.scenes[1].keyframe_image_path is not None
    assert os.path.exists(session.plan.scenes[0].keyframe_image_path)
    assert os.path.exists(session.plan.scenes[1].keyframe_image_path)


def test_conversational_delta_modification(offline_director):
    director = offline_director

    session = director.create_storyboard("A brave astronaut discovering an ancient crystal on Mars")
    original_scene1_prompt = session.plan.scenes[0].visual_prompt
    original_scene1_keyframe = session.plan.scenes[0].keyframe_image_path

    # Apply surgical delta modification targeting Scene 2
    updated = director.apply_modification(
        session_id=session.session_id,
        instruction="modify 2 make the crystal glowing purple and remove voiceover"
    )

    assert updated is not None
    assert updated.approval_status == ApprovalStatus.MODIFICATIONS_REQUESTED
    assert len(updated.history) == 1

    # Verify Scene 2 was modified
    scene2 = updated.plan.scenes[1]
    assert "purple" in scene2.visual_prompt.lower()
    assert scene2.dialogue_text is None
    assert scene2.keyframe_image_path is not None

    # Verify Scene 1 was NOT altered
    scene1 = updated.plan.scenes[0]
    assert scene1.visual_prompt == original_scene1_prompt
    assert scene1.keyframe_image_path == original_scene1_keyframe
    assert scene1.dialogue_text is not None


def test_approve_session_and_convert_to_project(offline_director):
    director = offline_director

    session = director.create_storyboard("Cyberpunk detective in neon rain")
    approved = director.approve_session(session.session_id)

    assert approved.approval_status == ApprovalStatus.APPROVED

    project = director.convert_plan_to_video_project(approved.plan)
    assert project.title == approved.plan.title
    assert project.genre == Genre.CINEMATIC_STORY
    assert len(project.scenes) >= 2
    assert len(project.scenes[0].image_assets) >= 1


def test_create_storyboard_with_aspect_ratio_16_9(offline_director):
    from PIL import Image

    director = offline_director

    session = director.create_storyboard(
        prompt="A colossal space freighter docking over Saturn",
        aspect_ratio="16:9",
    )

    assert session.plan.aspect_ratio == "16:9"
    assert session.plan.width == 1920
    assert session.plan.height == 1080

    # Verify synthesized keyframe dimensions match 1920x1080
    keyframe_path = session.plan.scenes[0].keyframe_image_path
    assert keyframe_path is not None and os.path.exists(keyframe_path)
    with Image.open(keyframe_path) as img:
        assert img.size == (1920, 1080)

    # Verify project conversion preserves dimensions
    project = director.convert_plan_to_video_project(session.plan)
    assert project.aspect_ratio == "16:9"
    assert project.width == 1920
    assert project.height == 1080

