"""Unit tests for StoryboardSessionManager (persistence, history, and delta invalidation)."""

import os
import shutil
import pytest
from core.models import (
    DirectorMasterPlan,
    SceneBeatPlan,
    ConditioningMode,
    ApprovalStatus,
    Genre
)
from core.session_manager import StoryboardSessionManager


@pytest.fixture
def temp_sessions_dir(tmp_path):
    dir_path = str(tmp_path / "sessions")
    os.makedirs(dir_path, exist_ok=True)
    yield dir_path
    shutil.rmtree(dir_path, ignore_errors=True)


@pytest.fixture
def sample_plan():
    return DirectorMasterPlan(
        title="Test Story",
        genre=Genre.CINEMATIC_STORY,
        total_duration_sec=7.5,
        scenes=[
            SceneBeatPlan(
                beat_index=1,
                name="Scene 1",
                duration_sec=3.5,
                conditioning_mode=ConditioningMode.START_FRAME_ONLY,
                visual_prompt="Astronaut on Mars red terrain",
                dialogue_text="Walking on Mars"
            ),
            SceneBeatPlan(
                beat_index=2,
                name="Scene 2",
                duration_sec=4.0,
                conditioning_mode=ConditioningMode.START_AND_END_FRAME,
                visual_prompt="Holding ancient crystal",
                dialogue_text="Crystal discovered"
            )
        ]
    )


def test_create_and_load_session(temp_sessions_dir, sample_plan):
    manager = StoryboardSessionManager(temp_sessions_dir)
    session = manager.create_session("Astronaut discovery", sample_plan)

    assert session.session_id is not None
    assert session.approval_status == ApprovalStatus.PENDING_REVIEW
    assert len(session.plan.scenes) == 2

    loaded = manager.load_session(session.session_id)
    assert loaded is not None
    assert loaded.session_id == session.session_id
    assert loaded.initial_prompt == "Astronaut discovery"
    assert loaded.plan.title == "Test Story"


def test_record_turn_and_update_status(temp_sessions_dir, sample_plan):
    manager = StoryboardSessionManager(temp_sessions_dir)
    session = manager.create_session("Astronaut discovery", sample_plan)

    updated = manager.record_turn(
        session_id=session.session_id,
        user_message="Change scene 2 crystal to purple",
        modified_beats=[2],
        summary_of_changes="Modified scene 2 visual prompt to purple crystal"
    )

    assert updated is not None
    assert updated.approval_status == ApprovalStatus.MODIFICATIONS_REQUESTED
    assert len(updated.history) == 1
    assert updated.history[0].user_message == "Change scene 2 crystal to purple"
    assert updated.history[0].modified_beats == [2]


def test_invalidate_beat_keyframe(temp_sessions_dir, sample_plan, tmp_path):
    manager = StoryboardSessionManager(temp_sessions_dir)
    dummy_keyframe = str(tmp_path / "keyframe_beat_2.jpg")
    with open(dummy_keyframe, "w") as f:
        f.write("image data")

    sample_plan.scenes[1].keyframe_image_path = dummy_keyframe
    session = manager.create_session("Astronaut discovery", sample_plan)

    assert os.path.exists(dummy_keyframe)

    success = manager.invalidate_beat_keyframe(session.session_id, beat_index=2)
    assert success is True
    assert not os.path.exists(dummy_keyframe)

    loaded = manager.load_session(session.session_id)
    assert loaded.plan.scenes[1].keyframe_image_path is None
