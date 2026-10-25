"""End-to-end integration test for Feature 007: Multi-Character Dialogue Attribution & Motion Synthesis."""

import os
import re
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from core.models import (
    ApprovalStatus,
    Genre,
    DirectorMasterPlan,
    SceneBeatPlan,
    StoryboardSession,
    StoryboardBeat,
    VideoProject,
    RenderOutput,
    SubtitleWordToken,
    SubtitleTrack,
    CharacterProfile,
)
from core.session_manager import StoryboardSessionManager
from core.interactive_director import InteractiveDirector
from core.audio_engine import synthesize_scene_dialogue, stitch_beat_audio_tracks


@pytest.mark.asyncio
async def test_multi_character_audio_pipeline_e2e(tmp_path):
    """Verify that multiple speaking characters produce distinct audio tracks and stitched master audio."""
    temp_dir = str(tmp_path / "audio_out")
    os.makedirs(temp_dir, exist_ok=True)

    # 1. Synthesize Scene 1 (Character 1: Daisy the Cow)
    daisy_vo = str(tmp_path / "vo_daisy.mp3")
    audio1, dur1, sub1 = await synthesize_scene_dialogue(
        text="The meadow grass is crispy fresh today!",
        output_audio_path=daisy_vo,
        speaker="Daisy",
        voice_persona="cartoon_animal",
        whisper_model_size="tiny",
    )
    assert os.path.exists(audio1)
    assert dur1 > 0.5
    assert len(sub1.words) > 0

    # 2. Synthesize Scene 2 (Character 2: Barnaby the Bull)
    barnaby_vo = str(tmp_path / "vo_barnaby.mp3")
    audio2, dur2, sub2 = await synthesize_scene_dialogue(
        text="Indeed, but keep watch for the farmer's tractor.",
        output_audio_path=barnaby_vo,
        speaker="Barnaby",
        voice_persona="male_casual",
        whisper_model_size="tiny",
    )
    assert os.path.exists(audio2)
    assert dur2 > 0.5
    assert len(sub2.words) > 0

    # 3. Stitch multi-speaker tracks into master voiceover
    master_vo = str(tmp_path / "master_composite_vo.mp3")
    beat_tracks = [(audio1, 0.0), (audio2, dur1)]
    stitched_path = stitch_beat_audio_tracks(beat_tracks, dur1 + dur2 + 1.0, master_vo)
    assert os.path.exists(stitched_path)
    assert os.path.getsize(stitched_path) > 0


@pytest.mark.asyncio
async def test_interactive_director_multi_character_render_lifecycle(tmp_path):
    """Verify that InteractiveDirector renders a multi-character session with timeline-sequenced audio."""
    sessions_dir = str(tmp_path / "sessions")
    session_manager = StoryboardSessionManager(sessions_dir=sessions_dir)
    director = InteractiveDirector(session_manager=session_manager, comfy_client=None)

    # Create dummy keyframe images
    kf1 = str(tmp_path / "kf1.png")
    kf2 = str(tmp_path / "kf2.png")
    from PIL import Image
    Image.new("RGB", (1280, 720), color="green").save(kf1)
    Image.new("RGB", (1280, 720), color="blue").save(kf2)

    # Create dummy beat video clips
    vid1 = str(tmp_path / "vid1.mp4")
    vid2 = str(tmp_path / "vid2.mp4")
    with open(vid1, "wb") as f:
        f.write(b"dummy mp4 video 1")
    with open(vid2, "wb") as f:
        f.write(b"dummy mp4 video 2")

    plan = DirectorMasterPlan(
        title="Bovine Conversations",
        concept="Two cows discussing the weather",
        genre=Genre.CINEMATIC_STORY,
        aspect_ratio="16:9",
        width=1280,
        height=720,
        total_duration_sec=7.0,
        characters=[
            CharacterProfile(name="Daisy", visual_anchor="spotted cow", voice_persona="cartoon_animal"),
            CharacterProfile(name="Barnaby", visual_anchor="brown bull", voice_persona="male_casual"),
        ],
        scenes=[
            SceneBeatPlan(
                beat_index=0,
                duration_sec=3.5,
                visual_prompt="Subject: Daisy the spotted cow grazing peacefully. Secondary: Chewing green grass. Environment: Sun-drenched rolling meadow. Camera: Slow forward push-in.",
                dialogue_text="Moo! The meadow grass is crispy fresh today!",
                speaker="Daisy",
                voice_persona="cartoon_animal",
                keyframe_image_path=kf1,
            ),
            SceneBeatPlan(
                beat_index=1,
                duration_sec=3.5,
                visual_prompt="Subject: Barnaby the brown bull snorting alertly. Secondary: Swishing his tail. Environment: Distant tractor kicking up dust. Camera: Low angle static wide shot.",
                dialogue_text="Indeed Daisy, but the farmer is heading this way.",
                speaker="Barnaby",
                voice_persona="male_casual",
                keyframe_image_path=kf2,
            ),
        ]
    )

    session = session_manager.create_session(
        initial_prompt="Two cows discussing the weather",
        plan=plan
    )
    session_manager.set_approval_status(session.session_id, ApprovalStatus.APPROVED)
    approved_session = session_manager.load_session(session.session_id)

    # Mock video generation & Remotion render to keep test fast and zero-cost
    with patch("core.visual_router.route_and_execute_beat") as mock_route, \
         patch("core.runpod_serverless.ensure_video_duration_coverage", side_effect=lambda p, d: p), \
         patch("core.remotion_bridge.render_project_to_video") as mock_remotion:

        mock_route.side_effect = [vid1, vid2]
        final_mp4 = str(tmp_path / "final_output.mp4")
        with open(final_mp4, "wb") as f:
            f.write(b"final rendered mp4")
        mock_remotion.return_value = final_mp4

        output = await director.render_approved_session(
            session=approved_session,
            output_path=final_mp4,
            whisper_model="tiny",
            backend="local",
        )

        assert output is not None
        assert output.file_path == final_mp4
        assert output.duration_sec == 7.0
        assert mock_route.call_count == 2
        assert mock_remotion.called
