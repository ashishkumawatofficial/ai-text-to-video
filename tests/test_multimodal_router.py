"""Unit tests for multimodal generation: T2V, I2V kinetic filtering, dual frame pinning, and multi-asset passing."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from core.models import (
    VideoGenerationRequest,
    VideoGenerationModality,
    VideoAudioMode,
)
from core.provider_registry import get_model_profile
from core.prompt_adapter import PromptAdapter
from core.providers.fal_provider import FalProvider
from core.providers.apidot_provider import ApidotProvider
from core.providers.kie_provider import KieProvider


def test_i2v_kinetic_filtering_suppresses_static_descriptions():
    adapter = PromptAdapter()
    
    # Prompt containing static clothing and static positioning descriptions
    static_rich_prompt = (
        "A detective wearing a dark wool trenchcoat and clad in leather gloves, "
        "standing against a rusted metal fire escape in front of an old warehouse. "
        "Suddenly she spins around, unholsters a scanner, and races across the wet rooftop as lightning flashes. "
        "Rapid lateral camera tracking shot following her motion."
    )

    res = adapter.adapt_prompt(
        prompt=static_rich_prompt,
        model_id="kling-v1.5",
        modality=VideoGenerationModality.IMAGE_TO_VIDEO,
    )

    # Static elements should be suppressed
    assert "wearing a dark wool trenchcoat" not in res.adapted_prompt.lower()
    assert "clad in leather gloves" not in res.adapted_prompt.lower()
    assert "standing against a rusted metal" not in res.adapted_prompt.lower()

    # Kinetic actions and camera motion vectors must be preserved
    assert "spins around" in res.adapted_prompt
    assert "races across the wet rooftop" in res.adapted_prompt
    assert "tracking shot" in res.adapted_prompt


@pytest.mark.asyncio
async def test_dual_frame_pinning_in_adapters():
    profile = get_model_profile("kling-v1.5")
    req = VideoGenerationRequest(
        project_id="proj_test",
        beat_index=1,
        model_profile=profile,
        prompt="Transition scene from sunny day to thunderstorm",
        start_frame_path="https://storage.example.com/start_frame.jpg",
        end_frame_path="https://storage.example.com/end_frame.jpg",
        duration_sec=5.0,
        modality=VideoGenerationModality.START_END_INTERPOLATION,
    )

    # Test FalProvider builds payload with start and end frames
    fal = FalProvider(api_key="fake-fal-key")
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"request_id": "fal_req_001"}
        mock_post.return_value = mock_resp

        task_id = await fal.submit_video_job(req)
        assert task_id == "fal_req_001"
        _, kwargs = mock_post.call_args
        sent_json = kwargs["json"]
        assert sent_json["image_url"] == "https://storage.example.com/start_frame.jpg"
        assert sent_json["tail_image_url"] == "https://storage.example.com/end_frame.jpg"

    # Test ApidotProvider builds payload with start and end frames
    apidot = ApidotProvider(api_key="fake-apidot-key")
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"task_id": "apidot_req_001"}
        mock_post.return_value = mock_resp

        task_id = await apidot.submit_video_job(req)
        assert task_id == "apidot_req_001"
        _, kwargs = mock_post.call_args
        sent_json = kwargs["json"]
        assert sent_json["image_url"] == "https://storage.example.com/start_frame.jpg"
        assert sent_json["tail_image_url"] == "https://storage.example.com/end_frame.jpg"

    # Test KieProvider builds payload with start and end frames
    kie = KieProvider(api_key="fake-kie-key")
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"code": 200, "data": {"taskId": "kie_req_001"}}
        mock_post.return_value = mock_resp

        task_id = await kie.submit_video_job(req)
        assert task_id == "kie_req_001"
        _, kwargs = mock_post.call_args
        sent_json = kwargs["json"]
        assert sent_json["input"]["image_url"] == "https://storage.example.com/start_frame.jpg"
        assert sent_json["input"]["tail_image_url"] == "https://storage.example.com/end_frame.jpg"


@pytest.mark.asyncio
async def test_multimodal_reference_assets_attachment():
    profile = get_model_profile("seedance-2.5")
    req = VideoGenerationRequest(
        project_id="proj_seedance",
        beat_index=2,
        model_profile=profile,
        prompt="Character dancing with holographic duplicate",
        reference_assets=[
            "https://storage.example.com/ref1.jpg",
            "https://storage.example.com/ref2.png",
            "https://storage.example.com/motion_ref.mp4",
        ],
        duration_sec=5.0,
    )

    fal = FalProvider(api_key="fake-fal-key")
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"request_id": "fal_req_seedance"}
        mock_post.return_value = mock_resp

        await fal.submit_video_job(req)
        _, kwargs = mock_post.call_args
        sent_json = kwargs["json"]
        assert len(sent_json["reference_images"]) == 2
        assert len(sent_json["reference_videos"]) == 1
        assert "motion_ref.mp4" in sent_json["reference_videos"][0]
