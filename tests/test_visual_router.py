"""Unit tests for the multi-tier visual routing engine and automatic failover cascade."""

import os
import pytest
from unittest.mock import patch, MagicMock

from core.models import (
    StoryboardBeat,
    VisualStrategyRoute,
    Genre,
    ImageRole,
    ImageAsset,
)
from core.visual_router import route_and_execute_beat, select_beat_strategy


def test_select_beat_strategy():
    assert select_beat_strategy(Genre.RIDDLE, "Hook Question") == VisualStrategyRoute.PROGRAMMATIC_HYBRID
    assert select_beat_strategy(Genre.CINEMATIC_STORY, "Street Chase") == VisualStrategyRoute.FLAT_RATE_DIFFUSION


def test_visual_router_serverless_tier(tmp_path):
    beat = StoryboardBeat(
        beat_index=0,
        name="Test Serverless Beat",
        duration_sec=3.0,
        visual_prompt="Neon alleyway",
        visual_strategy=VisualStrategyRoute.FLAT_RATE_DIFFUSION
    )
    dest_mp4 = str(tmp_path / "serverless_out.mp4")

    mock_sl_client = MagicMock()
    mock_sl_client.is_available.return_value = True
    mock_sl_client.execute_video_job.return_value = dest_mp4

    res = route_and_execute_beat(
        beat=beat,
        output_video_path=dest_mp4,
        backend="serverless",
        serverless_client=mock_sl_client
    )

    assert res == dest_mp4
    mock_sl_client.execute_video_job.assert_called_once()


def test_visual_router_serverless_failover_to_pod(tmp_path):
    beat = StoryboardBeat(
        beat_index=1,
        name="Test Failover Beat",
        duration_sec=3.0,
        visual_prompt="Neon alleyway",
        visual_strategy=VisualStrategyRoute.FLAT_RATE_DIFFUSION
    )
    dest_mp4 = str(tmp_path / "failover_out.mp4")

    # Serverless fails
    mock_sl_client = MagicMock()
    mock_sl_client.is_available.return_value = True
    mock_sl_client.execute_video_job.side_effect = RuntimeError("Serverless 503 out of capacity")

    # Pod succeeds
    mock_pod_client = MagicMock()
    mock_pod_client.is_available.return_value = True
    mock_pod_client.execute_video_workflow.return_value = dest_mp4

    res = route_and_execute_beat(
        beat=beat,
        output_video_path=dest_mp4,
        backend="auto",
        serverless_client=mock_sl_client,
        comfy_client=mock_pod_client
    )

    assert res == dest_mp4
    mock_pod_client.execute_video_workflow.assert_called_once()


def test_visual_router_failover_to_local_mock(tmp_path):
    beat = StoryboardBeat(
        beat_index=2,
        name="Test Local Mock Beat",
        duration_sec=3.0,
        visual_prompt="Dark alleyway",
        visual_strategy=VisualStrategyRoute.FLAT_RATE_DIFFUSION
    )
    dest_mp4 = str(tmp_path / "local_mock.mp4")

    # Local backend selected
    res = route_and_execute_beat(
        beat=beat,
        output_video_path=dest_mp4,
        backend="local"
    )

    assert res == dest_mp4
    assert len(beat.image_assets) > 0
    assert beat.image_assets[0].role == ImageRole.START_FRAME
