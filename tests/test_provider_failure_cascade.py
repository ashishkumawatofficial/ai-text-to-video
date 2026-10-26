"""Unit tests for provider 5xx infrastructure failure and zero-cost cascading."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

from core.models import (
    ProviderId,
    VideoGenerationRequest,
    VideoModelProfile,
    VideoModelFamily,
    RenderingJobTicket,
    JobExecutionStatus,
)
from core.providers.base_provider import ProviderInfrastructureError
from core.cost_arbitrage import CostArbitrageEngine


@pytest.fixture
def test_request():
    profile = VideoModelProfile(
        model_id="kling-v1.5",
        display_name="Kling 1.5",
        family=VideoModelFamily.KLING,
        version="1.5",
        hard_char_limit=3072,
        safe_char_limit=2500,
        supported_providers=[ProviderId.FAL_AI, ProviderId.APIDOT_AI],
    )
    return VideoGenerationRequest(
        project_id="test_project",
        beat_index=1,
        model_profile=profile,
        prompt="A warrior walks into the misty forest",
        duration_sec=5.0,
    )


@pytest.mark.asyncio
async def test_zero_cost_cascade_on_5xx_failure(test_request):
    """Verifies that when primary provider fails with 5xx, system cascades to secondary with 0-cost on primary."""
    engine = CostArbitrageEngine()

    mock_primary_adapter = AsyncMock()
    mock_primary_adapter.provider_id = ProviderId.APIDOT_AI
    mock_primary_adapter.is_configured = lambda: True
    # Primary fails with infrastructure 500 error
    mock_primary_adapter.submit_video_job.side_effect = ProviderInfrastructureError(
        "Upstream 500 internal server error",
        provider_id=ProviderId.APIDOT_AI,
        status_code=500
    )

    mock_secondary_adapter = AsyncMock()
    mock_secondary_adapter.provider_id = ProviderId.FAL_AI
    mock_secondary_adapter.is_configured = lambda: True
    mock_secondary_adapter.submit_video_job.return_value = "fal_task_999"
    mock_secondary_adapter.poll_job_status.return_value = {
        "status": JobExecutionStatus.COMPLETED,
        "progress_percent": 100,
        "video_url": "https://fal.media/output.mp4",
        "billed_cost_usd": 0.45,
    }
    mock_secondary_adapter.download_video_asset.return_value = "/tmp/output.mp4"

    with patch.object(engine, "get_adapter") as mock_get_adapter:
        def get_adapter_side_effect(pid):
            if pid == ProviderId.APIDOT_AI:
                return mock_primary_adapter
            return mock_secondary_adapter
        mock_get_adapter.side_effect = get_adapter_side_effect

        ticket = await engine.execute_with_cascade(
            test_request,
            candidate_providers=[ProviderId.APIDOT_AI, ProviderId.FAL_AI],
            output_path="/tmp/output.mp4"
        )

        assert ticket.status == JobExecutionStatus.COMPLETED
        # Winning ticket was completed by secondary provider
        assert ticket.provider_id == ProviderId.FAL_AI
        assert ticket.provider_task_id == "fal_task_999"
        assert ticket.retry_count == 1
        assert ticket.actual_billed_usd == 0.45


@pytest.mark.asyncio
async def test_cascade_selects_cheapest_secondary_before_expensive(test_request):
    """Verifies that cascade iterates strictly in ascending price order (cheapest secondary first)."""
    engine = CostArbitrageEngine()

    # Provider A ($0.30) fails
    p_a = AsyncMock()
    p_a.provider_id = ProviderId.APIDOT_AI
    p_a.is_configured = lambda: True
    p_a.submit_video_job.side_effect = ProviderInfrastructureError("A failed", provider_id=ProviderId.APIDOT_AI)

    # Provider B ($0.45) succeeds
    p_b = AsyncMock()
    p_b.provider_id = ProviderId.FAL_AI
    p_b.is_configured = lambda: True
    p_b.submit_video_job.return_value = "fal_task_cheap"
    p_b.poll_job_status.return_value = {
        "status": JobExecutionStatus.COMPLETED,
        "video_url": "https://fal.media/cheap.mp4",
        "billed_cost_usd": 0.45,
    }
    p_b.download_video_asset.return_value = "/tmp/cheap.mp4"

    # Provider C ($0.75 - more expensive, should never be called)
    p_c = AsyncMock()
    p_c.provider_id = ProviderId.KIE_AI
    p_c.is_configured = lambda: True
    p_c.submit_video_job.return_value = "kie_task_expensive"

    with patch.object(engine, "get_adapter") as mock_get_adapter:
        mock_get_adapter.side_effect = lambda pid: {
            ProviderId.APIDOT_AI: p_a,
            ProviderId.FAL_AI: p_b,
            ProviderId.KIE_AI: p_c,
        }.get(pid)

        # Ranked list passed in ascending cost order: [Cheapest ($0.30), 2nd ($0.45), 3rd ($0.75)]
        ticket = await engine.execute_with_cascade(
            test_request,
            candidate_providers=[ProviderId.APIDOT_AI, ProviderId.FAL_AI, ProviderId.KIE_AI],
            output_path="/tmp/output.mp4"
        )

        assert ticket.status == JobExecutionStatus.COMPLETED
        assert ticket.provider_id == ProviderId.FAL_AI
        # Provider B was attempted
        p_b.submit_video_job.assert_called_once()
        # More expensive Provider C was NOT needed and never called
        p_c.submit_video_job.assert_not_called()


def test_disable_cascade_prevents_secondary_attempt(tmp_path):
    """Verifies that when allow_cascade is False, visual router only attempts Candidate 1 and never calls secondary."""
    from core.visual_router import route_and_execute_beat
    from core.models import StoryboardBeat, VisualStrategyRoute
    from unittest.mock import AsyncMock, MagicMock

    beat = StoryboardBeat(
        beat_index=1,
        name="Strict Single Provider Beat",
        duration_sec=5.0,
        visual_prompt="Epic mountain sunset",
        visual_strategy=VisualStrategyRoute.FLAT_RATE_DIFFUSION
    )
    dest_mp4 = str(tmp_path / "strict_cascade_off.mp4")

    mock_engine = MagicMock()
    # execute_with_cascade should receive only a single candidate provider!
    mock_engine.execute_with_cascade = AsyncMock(side_effect=RuntimeError("Primary provider failed"))

    route_and_execute_beat(
        beat=beat,
        output_video_path=dest_mp4,
        backend="channel_2",
        model_id="kling-v1.5",
        arbitrage_engine=mock_engine,
        allow_cascade=False,
    )

    # When allow_cascade is False, candidates passed to execute_with_cascade must be exactly 1 provider
    call_args = mock_engine.execute_with_cascade.call_args
    passed_candidates = call_args[0][1]
    assert len(passed_candidates) == 1


