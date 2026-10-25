"""Integration test for Feature 004: Dynamic AI Story Writer & Aspect Ratio Staging."""

import os
import pytest
from PIL import Image

from core.models import (
    ApprovalStatus,
    Genre,
    NarrativeInputMode,
    VideoAspectRatio,
    ModelCascadeConfig,
    ModelProvider
)
from core.session_manager import StoryboardSessionManager
from core.interactive_director import InteractiveDirector
from core.remotion_bridge import build_remotion_props


def test_dynamic_storyboard_aspect_ratio_16_9_flow(tmp_path):
    """Verify that an aspect-ratio 16:9 story produces native widescreen Remotion props and plates."""
    sessions_dir = str(tmp_path / "sessions")
    session_manager = StoryboardSessionManager(sessions_dir=sessions_dir)
    director = InteractiveDirector(session_manager=session_manager)

    # 1. Synthesize dynamic storyboard with 16:9 aspect ratio
    prompt = "A high-tech research vessel discovering an uncharted abyssal trench in Europa's ocean"
    session = director.create_storyboard(
        prompt=prompt,
        aspect_ratio="16:9",
    )

    assert session is not None
    assert session.approval_status == ApprovalStatus.PENDING_REVIEW
    assert session.plan.aspect_ratio == "16:9"
    assert session.plan.width == 1920
    assert session.plan.height == 1080

    # Verify scene prompts have widescreen composition tokens
    assert len(session.plan.scenes) >= 2
    for scene in session.plan.scenes:
        assert "16:9" in scene.visual_prompt.lower() or "widescreen" in scene.visual_prompt.lower()
        assert scene.keyframe_image_path is not None
        assert os.path.exists(scene.keyframe_image_path)
        with Image.open(scene.keyframe_image_path) as img:
            assert img.size == (1920, 1080)

    # 2. Approve session and convert to VideoProject
    approved = director.approve_session(session.session_id)
    assert approved.approval_status == ApprovalStatus.APPROVED

    project = director.convert_plan_to_video_project(approved.plan)
    assert project.aspect_ratio == "16:9"
    assert project.width == 1920
    assert project.height == 1080

    # 3. Build Remotion universal props payload and assert exact canvas dimensions
    props = build_remotion_props(project)
    assert props["width"] == 1920
    assert props["height"] == 1080
    assert props["genre"] == Genre.CINEMATIC_STORY.value
    assert len(props["scenes"]) == len(session.plan.scenes)


def test_dynamic_script_ingestion_and_dialogue_preservation(tmp_path):
    """Verify that long-form scripts preserve 100% of spoken lines across segmented beats."""
    sessions_dir = str(tmp_path / "sessions_script")
    session_manager = StoryboardSessionManager(sessions_dir=sessions_dir)
    director = InteractiveDirector(session_manager=session_manager)

    full_script = (
        "Commander Hayes gripped the helm as alarms wailed across the bridge. "
        "Shields down to twelve percent, hold your stations! "
        "The flagship leveled its main cannons directly at the reactor core. "
        "Fire all defensive batteries on my mark! "
        "The enemy formation shattered into radiant plasma. "
        "Report all casualties, we secured the quadrant."
    )

    session = director.create_storyboard(
        prompt=full_script,
        input_mode="script_adaptation",
        aspect_ratio="9:16",
    )

    assert session is not None
    assert len(session.plan.scenes) >= 3

    # Check dialogue coverage
    combined_dialogue = " ".join(s.dialogue_text for s in session.plan.scenes if s.dialogue_text)
    assert "Shields down to twelve percent" in combined_dialogue
    assert "Fire all defensive batteries" in combined_dialogue
    assert "we secured the quadrant" in combined_dialogue
