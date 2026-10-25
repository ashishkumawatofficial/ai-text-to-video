"""Integration tests for the RunPod Serverless parallel dispatch flow."""

import os
import base64
import pytest
from unittest.mock import patch, MagicMock

from core.models import (
    DirectorMasterPlan,
    SceneBeat,
    StoryboardSession,
    VideoAspectRatio,
)
from core.interactive_director import InteractiveDirector


@pytest.mark.asyncio
async def test_serverless_parallel_flow_integration(tmp_path):
    # 1. Create a 3-beat storyboard session
    beats = [
        SceneBeat(
            beat_index=0,
            name="Neon Alley Arrival",
            duration_sec=3.0,
            visual_prompt="Detective standing in neon rain alley",
            dialogue_text="The city never sleeps."
        ),
        SceneBeat(
            beat_index=1,
            name="Clue Discovered",
            duration_sec=3.0,
            visual_prompt="Close up of cybernetic footprint in puddle",
            dialogue_text="He was here."
        ),
        SceneBeat(
            beat_index=2,
            name="The Confrontation",
            duration_sec=3.0,
            visual_prompt="Silhouette stepping out from fog",
            dialogue_text="End of the line."
        ),
    ]

    plan = DirectorMasterPlan(
        title="Serverless Test Noir",
        genre="cinematic_story",
        aspect_ratio="16:9",
        scenes=beats,
        total_duration_sec=9.0
    )
    session = StoryboardSession(
        initial_prompt="Cyberpunk test",
        plan=plan
    )

    fake_video = b"\x00\x00\x00\x1cftypisom\x00\x00\x02\x00"
    b64_str = f"data:video/mp4;base64,{base64.b64encode(fake_video).decode('utf-8')}"

    # 2. Mock Serverless run and poll endpoints
    with patch("core.runpod_serverless.RunPodServerlessClient.is_available", return_value=True), \
         patch("requests.post") as mock_post, \
         patch("requests.get") as mock_get, \
         patch("core.audio_engine.generate_narration_with_subtitles") as mock_vo, \
         patch("core.remotion_bridge.render_project_to_video") as mock_render:

        # Mock voiceover
        mock_vo.return_value = (None, MagicMock(words=[]))

        # Mock run job response
        run_resp = MagicMock()
        run_resp.status_code = 200
        run_resp.json.side_effect = [
            {"id": "job_01", "status": "IN_QUEUE"},
            {"id": "job_02", "status": "IN_QUEUE"},
            {"id": "job_03", "status": "IN_QUEUE"},
        ]
        mock_post.return_value = run_resp

        # Mock poll job response
        poll_resp = MagicMock()
        poll_resp.status_code = 200
        poll_resp.json.return_value = {
            "status": "COMPLETED",
            "executionTime": 15000,
            "output": {"videos": [{"data": b64_str}]}
        }
        mock_get.return_value = poll_resp

        director = InteractiveDirector()
        out_video = str(tmp_path / "serverless_final.mp4")

        # Run synthesis with serverless backend
        result = await director.render_approved_session(
            session=session,
            output_path=out_video,
            backend="serverless"
        )

        assert result is not None
        mock_render.assert_called_once()
        # Verify that all 3 beats received output video paths
        for b in session.plan.scenes:
            assert b.output_video_path is not None
            assert os.path.exists(b.output_video_path)
