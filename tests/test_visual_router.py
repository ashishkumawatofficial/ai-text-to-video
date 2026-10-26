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


def test_visual_router_channel_2_arbitrage(tmp_path):
    from unittest.mock import AsyncMock
    from core.models import RenderingJobTicket, JobExecutionStatus, ProviderId

    beat = StoryboardBeat(
        beat_index=3,
        name="Channel 2 Beat",
        duration_sec=5.0,
        visual_prompt="Cyberpunk street in rain",
        visual_strategy=VisualStrategyRoute.FLAT_RATE_DIFFUSION
    )
    dest_mp4 = str(tmp_path / "channel2_out.mp4")

    mock_engine = MagicMock()
    mock_ticket = RenderingJobTicket(
        project_id="proj_default",
        beat_index=3,
        provider_id=ProviderId.FAL_AI,
        provider_task_id="task_123",
        model_id="kling-v1.5",
        status=JobExecutionStatus.COMPLETED,
        output_video_path=dest_mp4,
        actual_billed_usd=0.07,
    )
    mock_engine.get_ranked_quotes = AsyncMock(return_value=[])
    mock_engine.execute_with_cascade = AsyncMock(return_value=mock_ticket)

    res = route_and_execute_beat(
        beat=beat,
        output_video_path=dest_mp4,
        backend="channel_2",
        model_id="kling-v1.5",
        arbitrage_engine=mock_engine,
    )

    assert res == dest_mp4
    assert beat.output_video_path == dest_mp4
    mock_engine.execute_with_cascade.assert_called_once()


def test_visual_router_channel_2_cascade_to_local_on_error(tmp_path):
    from unittest.mock import AsyncMock

    beat = StoryboardBeat(
        beat_index=4,
        name="Channel 2 Fail Beat",
        duration_sec=5.0,
        visual_prompt="Cyberpunk neon city",
        visual_strategy=VisualStrategyRoute.FLAT_RATE_DIFFUSION
    )
    dest_mp4 = str(tmp_path / "cascade_local.mp4")

    mock_engine = MagicMock()
    mock_engine.get_ranked_quotes = AsyncMock(return_value=[])
    mock_engine.execute_with_cascade = AsyncMock(side_effect=RuntimeError("All providers 500 error"))

    res = route_and_execute_beat(
        beat=beat,
        output_video_path=dest_mp4,
        backend="channel_2",
        model_id="kling-v1.5",
        arbitrage_engine=mock_engine,
    )

    # Cascades safely to Tier 3 local plate generator
    assert res == dest_mp4
    assert len(beat.image_assets) > 0
    assert beat.image_assets[0].role == ImageRole.START_FRAME


def test_channel_2_failure_never_calls_runpod(tmp_path):
    """Ensures strict isolation: Channel 2 failures MUST NEVER route to Channel 1 (RunPod/ComfyUI)."""
    from unittest.mock import AsyncMock, MagicMock

    beat = StoryboardBeat(
        beat_index=5,
        name="Channel 2 Strict Isolation Beat",
        duration_sec=5.0,
        visual_prompt="Cyberpunk neon city",
        visual_strategy=VisualStrategyRoute.FLAT_RATE_DIFFUSION
    )
    dest_mp4 = str(tmp_path / "strict_isolation.mp4")

    mock_engine = MagicMock()
    mock_engine.execute_with_cascade = AsyncMock(side_effect=RuntimeError("All API providers 500 down"))

    mock_serverless = MagicMock()
    mock_serverless.is_available.return_value = True

    mock_comfy = MagicMock()
    mock_comfy.is_available.return_value = True

    route_and_execute_beat(
        beat=beat,
        output_video_path=dest_mp4,
        backend="channel_2",
        model_id="kling-v1.5",
        arbitrage_engine=mock_engine,
        serverless_client=mock_serverless,
        comfy_client=mock_comfy,
    )

    # Must NEVER call RunPod Serverless or ComfyUI!
    mock_serverless.run_job.assert_not_called()
    mock_comfy.execute_video_workflow.assert_not_called()


