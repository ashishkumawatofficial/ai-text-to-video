"""Comprehensive unit test suite for multi-frame (first frame, last frame, reference images)
capabilities, API endpoints, and provider payload mapping across fal.ai, apidot.ai, and kie.ai.
"""

import io
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from core.models import (
    StudioSession,
    StoryboardCard,
    DirectingMode,
    BackendExecutionStrategy,
    VideoGenerationRequest,
    VideoGenerationModality,
    VideoAudioMode,
    VideoModelProfile,
    VideoModelFamily,
    ProviderId,
)
from core.provider_registry import MODEL_PROFILES_REGISTRY
from core.server import app, _ACTIVE_SESSIONS
from core.providers.fal_provider import FalProvider
from core.providers.apidot_provider import ApidotProvider
from core.providers.kie_provider import KieProvider

client = TestClient(app)


def test_model_profiles_conditioning_capabilities_matrix():
    """Verify all video foundation models have accurately verified conditioning capabilities."""
    # 1. Kling AI
    assert MODEL_PROFILES_REGISTRY["kling-v1.0"].supports_i2v is True
    assert MODEL_PROFILES_REGISTRY["kling-v1.0"].supports_dual_frame is False
    assert MODEL_PROFILES_REGISTRY["kling-v1.0"].supports_reference_images is False

    assert MODEL_PROFILES_REGISTRY["kling-v1.5"].supports_i2v is True
    assert MODEL_PROFILES_REGISTRY["kling-v1.5"].supports_dual_frame is True
    assert MODEL_PROFILES_REGISTRY["kling-v1.5"].supports_reference_images is False

    assert MODEL_PROFILES_REGISTRY["kling-v2.0"].supports_dual_frame is True
    assert MODEL_PROFILES_REGISTRY["kling-v2.0"].supports_reference_images is True
    assert MODEL_PROFILES_REGISTRY["kling-v2.0"].max_reference_images == 2

    assert MODEL_PROFILES_REGISTRY["kling-v2.5"].supports_dual_frame is True
    assert MODEL_PROFILES_REGISTRY["kling-v2.5"].supports_reference_images is True
    assert MODEL_PROFILES_REGISTRY["kling-v2.5"].max_reference_images == 4

    assert MODEL_PROFILES_REGISTRY["kling-v3.0"].supports_reference_images is True
    assert MODEL_PROFILES_REGISTRY["kling-v4.0"].supports_reference_images is True

    # 2. ByteDance Seedance
    assert MODEL_PROFILES_REGISTRY["seedance-1.0"].supports_dual_frame is False
    assert MODEL_PROFILES_REGISTRY["seedance-1.5"].supports_dual_frame is False
    assert MODEL_PROFILES_REGISTRY["seedance-2.0"].supports_dual_frame is True
    assert MODEL_PROFILES_REGISTRY["seedance-2.0"].supports_reference_images is True
    assert MODEL_PROFILES_REGISTRY["seedance-2.5"].supports_dual_frame is True
    assert MODEL_PROFILES_REGISTRY["seedance-2.5"].supports_reference_images is True
    assert MODEL_PROFILES_REGISTRY["seedance-2.5"].max_reference_images == 4

    # 3. Runway Gen
    assert MODEL_PROFILES_REGISTRY["runway-gen2"].supports_dual_frame is False
    assert MODEL_PROFILES_REGISTRY["runway-gen3-alpha"].supports_dual_frame is True
    assert MODEL_PROFILES_REGISTRY["runway-gen3-turbo"].supports_dual_frame is True

    # 4. MiniMax Hailuo
    assert MODEL_PROFILES_REGISTRY["minimax-hailuo-01"].supports_dual_frame is False
    assert MODEL_PROFILES_REGISTRY["minimax-h3"].supports_dual_frame is True
    assert MODEL_PROFILES_REGISTRY["minimax-h3"].supports_reference_images is True

    # 5. Google Veo
    assert MODEL_PROFILES_REGISTRY["veo-2"].supports_dual_frame is False
    assert MODEL_PROFILES_REGISTRY["veo-3"].supports_dual_frame is True
    assert MODEL_PROFILES_REGISTRY["veo-3"].supports_reference_images is True
    assert MODEL_PROFILES_REGISTRY["veo-3.1"].supports_dual_frame is True
    assert MODEL_PROFILES_REGISTRY["veo-3.1"].supports_reference_images is True

    # 6. Alibaba Wan
    assert MODEL_PROFILES_REGISTRY["wan-2.1-t2v-1.3b"].supports_i2v is False  # Pure T2V
    assert MODEL_PROFILES_REGISTRY["wan-2.1"].supports_i2v is True
    assert MODEL_PROFILES_REGISTRY["wan-2.1"].supports_dual_frame is True
    assert MODEL_PROFILES_REGISTRY["wan-2.1"].supports_reference_images is True
    assert MODEL_PROFILES_REGISTRY["wan-3.0"].supports_reference_images is True
    assert MODEL_PROFILES_REGISTRY["wan-3.0"].max_reference_images == 5

    # 7. Luma Dream Machine & Vidu
    assert MODEL_PROFILES_REGISTRY["luma-ray1"].supports_dual_frame is False
    assert MODEL_PROFILES_REGISTRY["luma-ray2"].supports_dual_frame is True
    assert MODEL_PROFILES_REGISTRY["luma-ray2"].supports_reference_images is True

    assert MODEL_PROFILES_REGISTRY["vidu-1.5"].supports_dual_frame is False
    assert MODEL_PROFILES_REGISTRY["vidu-2.0"].supports_dual_frame is True
    assert MODEL_PROFILES_REGISTRY["vidu-2.0"].supports_reference_images is True

    # 8. FLUX Video (Black Forest Labs & fal Research)
    assert MODEL_PROFILES_REGISTRY["flux-3-max"].supports_dual_frame is True
    assert MODEL_PROFILES_REGISTRY["flux-3-max"].supports_reference_images is True
    assert MODEL_PROFILES_REGISTRY["flux-3-max"].supports_native_audio is True
    assert MODEL_PROFILES_REGISTRY["flux-3-max"].family == VideoModelFamily.FLUX


def test_api_providers_models_serialization():
    """Verify /api/providers/models endpoint serializes the new conditioning properties."""
    response = client.get("/api/providers/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data

    wan3 = next(m for m in data["models"] if m["model_id"] == "wan-3.0")
    assert wan3["supports_i2v"] is True
    assert wan3["supports_dual_frame"] is True
    assert wan3["supports_reference_images"] is True
    assert wan3["max_reference_images"] == 5
    assert wan3["first_frame_param_name"] == "image_url"
    assert wan3["end_frame_param_name"] in ("tail_image_url", "end_image_url")

    t2v_wan = next(m for m in data["models"] if m["model_id"] == "wan-2.1-t2v-1.3b")
    assert t2v_wan["supports_i2v"] is False
    assert t2v_wan["supports_dual_frame"] is False


def test_server_upload_and_remove_multiframe():
    """Verify backend endpoints for start frame, end frame, and reference images."""
    session_id = "test-session-multiframe-upload"
    test_session = StudioSession(
        session_id=session_id,
        concept_prompt="A knight fighting a dragon",
        aspect_ratio="16:9",
        directing_mode=DirectingMode.PRO,
        backend_strategy=BackendExecutionStrategy.SERVERLESS,
        beats=[
            StoryboardCard(
                beat_id="beat_0",
                beat_index=0,
                visual_prompt="Knight draws glowing sword",
                speaker="Narrator",
                dialogue_text="He ready his blade.",
                voice_actor="en-US-ChristopherNeural",
                camera_motion="push_in"
            )
        ]
    )
    _ACTIVE_SESSIONS[session_id] = test_session

    fake_image_bytes = b"fake-png-data"

    # 1. Upload start frame
    res_start = client.post(
        "/api/storyboard/upload-image",
        data={"session_id": session_id, "beat_index": 0, "frame_type": "start_frame"},
        files={"file": ("start.png", io.BytesIO(fake_image_bytes), "image/png")}
    )
    assert res_start.status_code == 200
    beat_data = res_start.json()
    assert beat_data["start_frame_path"] is not None
    assert beat_data["keyframe_path"] == beat_data["start_frame_path"]

    # 2. Upload end frame
    res_end = client.post(
        "/api/storyboard/upload-image",
        data={"session_id": session_id, "beat_index": 0, "frame_type": "end_frame"},
        files={"file": ("end.png", io.BytesIO(fake_image_bytes), "image/png")}
    )
    assert res_end.status_code == 200
    beat_data = res_end.json()
    assert beat_data["end_frame_path"] is not None

    # 3. Upload reference images
    res_ref1 = client.post(
        "/api/storyboard/upload-image",
        data={"session_id": session_id, "beat_index": 0, "frame_type": "reference_image"},
        files={"file": ("ref1.png", io.BytesIO(fake_image_bytes), "image/png")}
    )
    assert res_ref1.status_code == 200
    assert len(res_ref1.json()["reference_image_paths"]) == 1

    res_ref2 = client.post(
        "/api/storyboard/upload-image",
        data={"session_id": session_id, "beat_index": 0, "frame_type": "reference_image"},
        files={"file": ("ref2.png", io.BytesIO(fake_image_bytes), "image/png")}
    )
    assert res_ref2.status_code == 200
    assert len(res_ref2.json()["reference_image_paths"]) == 2

    # 4. Remove reference image by index
    res_rm_ref = client.post(
        "/api/storyboard/remove-frame",
        json={"session_id": session_id, "beat_index": 0, "frame_type": "reference_image", "image_index": 0}
    )
    assert res_rm_ref.status_code == 200
    assert len(res_rm_ref.json()["reference_image_paths"]) == 1

    # 5. Remove end frame
    res_rm_end = client.post(
        "/api/storyboard/remove-frame",
        json={"session_id": session_id, "beat_index": 0, "frame_type": "end_frame"}
    )
    assert res_rm_end.status_code == 200
    assert res_rm_end.json()["end_frame_path"] is None

    # 6. Remove start frame
    res_rm_start = client.post(
        "/api/storyboard/remove-frame",
        json={"session_id": session_id, "beat_index": 0, "frame_type": "start_frame"}
    )
    assert res_rm_start.status_code == 200
    assert res_rm_start.json()["start_frame_path"] is None
    assert res_rm_start.json()["keyframe_path"] is None


def test_storyboard_upload_resolves_project_from_disk():
    """Verify that if _ACTIVE_SESSIONS is empty (e.g. after server reload), upload_beat_image still resolves from project_manager."""
    from core.server import project_manager as server_pm

    # Create test project with beat 0
    test_proj = server_pm.create_project(title="Disk Resolve Test", prompt="Disk resolve prompt")
    test_proj.beats.append(StoryboardCard(beat_index=0, visual_prompt="Test"))
    server_pm.save_project(test_proj)
    pid = test_proj.session_id

    # Intentionally clear _ACTIVE_SESSIONS to simulate server restart
    _ACTIVE_SESSIONS.clear()
    assert pid not in _ACTIVE_SESSIONS

    fake_image_bytes = b"fake-png-data"
    res = client.post(
        "/api/storyboard/upload-image",
        data={"session_id": pid, "beat_index": 0, "frame_type": "reference_image"},
        files={"file": ("disk_ref.png", io.BytesIO(fake_image_bytes), "image/png")}
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["reference_image_paths"]) >= 1
    assert data["reference_image_paths"][-1].startswith(f"/api/projects/{pid}/media/references/")

    # Clean up test project
    server_pm.delete_project(pid)


@pytest.mark.asyncio
async def test_fal_provider_payload_mapping():
    """Verify FalProvider maps start frame, end frame, and reference images accurately."""
    provider = FalProvider(api_key="fal_test_key")

    # Kling Model with dual frame and reference image
    kling_profile = MODEL_PROFILES_REGISTRY["kling-v2.5"]
    req = VideoGenerationRequest(
        project_id="test_proj",
        beat_index=0,
        prompt="Cinematic battle scene",
        model_profile=kling_profile,
        modality=VideoGenerationModality.START_END_INTERPOLATION,
        duration_sec=5.0,
        aspect_ratio="16:9",
        resolution="720p",
        audio_mode=VideoAudioMode.MUTED,
        start_frame_path="https://example.com/start.png",
        end_frame_path="https://example.com/end.png",
        reference_image_paths=["https://example.com/hero_char.png"],
    )

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"request_id": "fal_job_123"}
        mock_post.return_value = mock_resp

        task_id = await provider.submit_video_job(req)
        assert task_id == "fal_job_123"

        call_args = mock_post.call_args
        payload = call_args.kwargs["json"]
        assert payload["image_url"] == "https://example.com/start.png"
        assert payload["tail_image_url"] == "https://example.com/end.png"
        assert payload["reference_images"] == ["https://example.com/hero_char.png"]


@pytest.mark.asyncio
async def test_apidot_provider_payload_mapping():
    """Verify APIDotProvider maps start frame, end frame, and reference images accurately."""
    provider = ApidotProvider(api_key="apidot_test_key")
    wan_profile = MODEL_PROFILES_REGISTRY["wan-2.1"]

    req = VideoGenerationRequest(
        project_id="test_proj",
        beat_index=0,
        prompt="Sci-fi corridor flythrough",
        model_profile=wan_profile,
        modality=VideoGenerationModality.IMAGE_TO_VIDEO,
        duration_sec=5.0,
        aspect_ratio="16:9",
        resolution="720p",
        audio_mode=VideoAudioMode.NATIVE_CLIP_AUDIO,
        start_frame_path="https://example.com/door_start.png",
        end_frame_path="https://example.com/door_end.png",
        reference_image_paths=["https://example.com/style_guide.png"],
    )

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"task_id": "apidot_job_456"}
        mock_post.return_value = mock_resp

        task_id = await provider.submit_video_job(req)
        assert task_id == "apidot_job_456"

        call_args = mock_post.call_args
        payload = call_args.kwargs["json"]
        assert payload["image_url"] == "https://example.com/door_start.png"
        assert payload["image"] == "https://example.com/door_start.png"
        assert payload["tail_image_url"] == "https://example.com/door_end.png"
        assert payload["end_image_url"] == "https://example.com/door_end.png"
        assert payload["reference_images"] == ["https://example.com/style_guide.png"]
        assert payload["with_audio"] is True


@pytest.mark.asyncio
async def test_kie_provider_payload_mapping():
    """Verify KieProvider maps input dictionary with start frame, end frame, and reference images."""
    provider = KieProvider(api_key="kie_test_key")
    seedance_profile = MODEL_PROFILES_REGISTRY["seedance-2.5"]

    req = VideoGenerationRequest(
        project_id="test_proj",
        beat_index=0,
        prompt="Hyper-realistic drone flight",
        model_profile=seedance_profile,
        modality=VideoGenerationModality.START_END_INTERPOLATION,
        duration_sec=5.0,
        aspect_ratio="16:9",
        resolution="1080p",
        audio_mode=VideoAudioMode.NATIVE_CLIP_AUDIO,
        start_frame_path="https://example.com/island_start.png",
        end_frame_path="https://example.com/island_end.png",
        reference_image_paths=["https://example.com/island_ref.png"],
    )

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"code": 200, "data": {"taskId": "kie_task_789"}}
        mock_post.return_value = mock_resp

        task_id = await provider.submit_video_job(req)
        assert task_id == "kie_task_789"

        call_args = mock_post.call_args
        payload = call_args.kwargs["json"]
        input_data = payload["input"]
        assert input_data["image_url"] == "https://example.com/island_start.png"
        assert input_data["tail_image_url"] == "https://example.com/island_end.png"
        assert input_data["end_image_url"] == "https://example.com/island_end.png"
        assert input_data["reference_images"] == ["https://example.com/island_ref.png"]
        assert input_data["audio"] is True


@pytest.mark.asyncio
async def test_fal_flux_keyframes_and_promotions():
    """Verify fal.ai FLUX 3 Max payload with keyframes array and promotional quote detection."""
    fal = FalProvider(api_key="fake_key")
    flux_profile = MODEL_PROFILES_REGISTRY["flux-3-max"]

    # Test keyframes-to-video payload
    req = VideoGenerationRequest(
        project_id="test_proj",
        beat_index=0,
        prompt="Camera zooms through mystical gateway",
        model_profile=flux_profile,
        modality=VideoGenerationModality.START_END_INTERPOLATION,
        duration_sec=5.0,
        aspect_ratio="16:9",
        resolution="720p",
        audio_mode=VideoAudioMode.NATIVE_CLIP_AUDIO,
        start_frame_path="https://example.com/gate_start.png",
        end_frame_path="https://example.com/gate_end.png",
    )

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"request_id": "fal_flux_req_123"}
        mock_post.return_value = mock_resp

        task_id = await fal.submit_video_job(req)
        assert task_id == "fal_flux_req_123"

        call_args = mock_post.call_args
        assert "blackforestlabs/flux-3-max/keyframes-to-video" in call_args.args[0]
        payload = call_args.kwargs["json"]
        assert "keyframes" in payload
        assert len(payload["keyframes"]) == 2
        assert payload["keyframes"][0] == {"image_url": "https://example.com/gate_start.png", "frame_index": 0}
        assert payload["keyframes"][1] == {"image_url": "https://example.com/gate_end.png", "frame_index": 119}
        assert payload["generate_audio"] is True

    # Test price quote calculation and promotion detection
    with patch.object(fal, "_fetch_live_pricing", return_value=(0.02125, "seconds")):
        quote = await fal.get_price_quote("flux-3-max", duration_sec=5.0)
        assert quote is not None
        assert quote.rate_per_sec_usd == 0.02125
        assert quote.is_promotional is True
        assert quote.discount_pct == 75.0


@pytest.mark.asyncio
async def test_provider_payloads_custom_reference_param_name():
    """Verify that Fal, APIDot, and Kie serialize reference images using profile.reference_param_name."""
    import copy
    custom_profile = copy.deepcopy(MODEL_PROFILES_REGISTRY["kling-v2.5"])
    custom_profile.reference_param_name = "character_reference_images"

    req = VideoGenerationRequest(
        project_id="test_proj",
        beat_index=0,
        prompt="Hero walks into frame",
        model_profile=custom_profile,
        modality=VideoGenerationModality.TEXT_TO_VIDEO,
        duration_sec=5.0,
        aspect_ratio="16:9",
        resolution="720p",
        audio_mode=VideoAudioMode.MUTED,
        negative_prompt="blurry, distorted",
        reference_image_paths=["https://example.com/character_sheet.png"],
    )

    # 1. FalProvider
    fal = FalProvider(api_key="fal_test_key")
    with patch("httpx.AsyncClient.post") as mock_fal_post:
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"request_id": "fal_custom_ref"}
        mock_fal_post.return_value = mock_resp

        await fal.submit_video_job(req)
        fal_payload = mock_fal_post.call_args.kwargs["json"]
        assert fal_payload["character_reference_images"] == ["https://example.com/character_sheet.png"]
        assert fal_payload["negative_prompt"] == "blurry, distorted"

    # 2. ApidotProvider
    apidot = ApidotProvider(api_key="apidot_test_key")
    with patch("httpx.AsyncClient.post") as mock_api_post:
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"task_id": "api_custom_ref"}
        mock_api_post.return_value = mock_resp

        await apidot.submit_video_job(req)
        api_payload = mock_api_post.call_args.kwargs["json"]
        assert api_payload["character_reference_images"] == ["https://example.com/character_sheet.png"]
        assert api_payload["negative_prompt"] == "blurry, distorted"

    # 3. KieProvider
    kie = KieProvider(api_key="kie_test_key")
    with patch("httpx.AsyncClient.post") as mock_kie_post:
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"code": 200, "data": {"taskId": "kie_custom_ref"}}
        mock_kie_post.return_value = mock_resp

        await kie.submit_video_job(req)
        kie_input = mock_kie_post.call_args.kwargs["json"]["input"]
        assert kie_input["character_reference_images"] == ["https://example.com/character_sheet.png"]
        assert kie_input["negative_prompt"] == "blurry, distorted"

