"""Kie.ai Provider Adapter for Channel 2 Multi-Model Video Generation."""

from __future__ import annotations
import os
import asyncio
import logging
from typing import Optional, Dict, Any

import httpx

from core.config import get_kie_key, get_provider_timeout_sec
from core.models import (
    ProviderId,
    VideoGenerationRequest,
    VideoGenerationModality,
    ProviderPriceQuote,
    JobExecutionStatus,
)
from core.providers.base_provider import (
    BaseVideoProvider,
    ProviderAuthenticationError,
    ProviderQuotaExceededError,
    ProviderPayloadValidationError,
    ProviderInfrastructureError,
    ProviderError,
)

logger = logging.getLogger(__name__)

# Kie.ai rates per second in USD (derived from token multiplier per model version)
KIE_MODEL_RATES: Dict[str, float] = {
    # Kling AI Family
    "kling-v1.0": 0.060,
    "kling-v1.0-pro": 0.070,
    "kling-v1.5-std": 0.072,
    "kling-v1.5": 0.085,
    "kling-v2.0": 0.110,
    "kling-v2.5": 0.118,
    "kling-v3.0": 0.130,
    "kling-v4.0": 0.1425,

    # ByteDance Seedance Family
    "seedance-1.0": 0.022,
    "seedance-1.5": 0.028,
    "seedance-2.0": 0.048,
    "seedance-2.5": 0.068,

    # Runway Family
    "runway-gen2": 0.025,
    "runway-gen3-alpha": 0.090,
    "runway-gen3-turbo": 0.045,

    # MiniMax Hailuo Family
    "minimax-hailuo-01": 0.058,
    "minimax-hailuo-live": 0.070,
    "minimax-h3": 0.088,

    # Google Veo Family
    "veo-2": 0.180,
    "veo-3": 0.270,
    "veo-3.1": 0.300,

    # Alibaba Wan Family
    "wan-2.1-t2v-1.3b": 0.019,
    "wan-2.1": 0.040,
    "wan-2.1-i2v-720p": 0.040,
    "wan-2.2": 0.058,
    "wan-3.0": 0.092,

    # xAI Grok Family
    "grok-video-1.5": 0.0225,

    # Luma Dream Machine Family
    "luma-ray1": 0.058,
    "luma-ray2": 0.095,

    # PixVerse Family
    "pixverse-v2": 0.038,
    "pixverse-v3": 0.068,

    # Pika Family
    "pika-1.0": 0.030,
    "pika-2.0": 0.058,

    # ShengShu Vidu Family
    "vidu-1.5": 0.048,
    "vidu-2.0": 0.078,

    # Open-Weights / Budget Family
    "cogvideox-2b": 0.016,
    "cogvideox-5b": 0.032,
    "hunyuan-video": 0.045,
    "mochi-1": 0.050,
}

KIE_MODEL_NAMES: Dict[str, str] = {
    "seedance-1.0": "bytedance/seedance-1",
    "seedance-1.5": "seedance-1-pro",
    "seedance-2.0": "bytedance/seedance-2",
    "seedance-2.5": "bytedance/seedance-2-5",
    "kling-v1.0": "kling-v1",
    "kling-v1.5": "kling",
    "kling-v2.0": "kling-v2",
    "runway-gen2": "runway-gen2",
    "runway-gen3-turbo": "runway",
    "runway-gen3-alpha": "runway-gen3-alpha",
    "veo-2": "google/veo-2",
    "veo-3": "google/veo-3",
}


class KieProvider(BaseVideoProvider):
    """Adapter for Kie.ai unified task-based generative media API."""

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or get_kie_key()

    @property
    def provider_id(self) -> ProviderId:
        return ProviderId.KIE_AI

    @property
    def official_docs_url(self) -> str:
        return "https://docs.kie.ai"

    @property
    def pricing_docs_url(self) -> str:
        return "https://kie.ai"

    @property
    def failure_billing_policy(self) -> str:
        return "Prepaid token safety: Failed tasks (status: fail) do not deduct credits. Upstream failures can be reviewed via task monitor."

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _get_headers(self) -> Dict[str, str]:
        if not self.is_configured():
            raise ProviderAuthenticationError("Missing KIE_API_KEY in environment", provider_id=self.provider_id)
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def get_price_quote(
        self,
        model_id: str,
        duration_sec: float,
        resolution: str = "720p",
        has_native_audio: bool = False,
    ) -> Optional[ProviderPriceQuote]:
        if model_id not in KIE_MODEL_RATES:
            return None

        base_rate = KIE_MODEL_RATES[model_id]
        if resolution == "480p":
            base_rate *= 0.55
        elif resolution == "1080p":
            base_rate *= 1.45
        elif resolution == "4k":
            base_rate *= 2.10

        if has_native_audio:
            base_rate += 0.02

        total_cost = round(base_rate * duration_sec, 4)

        return ProviderPriceQuote(
            provider_id=self.provider_id,
            model_id=model_id,
            duration_sec=duration_sec,
            resolution=resolution,
            native_audio_enabled=has_native_audio,
            rate_per_sec_usd=base_rate,
            estimated_total_usd=total_cost,
            billing_unit="per_second",
            is_available=self.is_configured(),
        )

    async def submit_video_job(self, request: VideoGenerationRequest) -> str:
        url = "https://api.kie.ai/api/v1/jobs/createTask"
        target_model = KIE_MODEL_NAMES.get(request.model_profile.model_id, request.model_profile.model_id)

        input_payload: Dict[str, Any] = {
            "prompt": request.prompt,
            "duration": int(request.duration_sec),
            "aspect_ratio": request.aspect_ratio,
            "quality": request.resolution,
        }

        # 1. Start Frame / First Frame mapping
        if request.start_frame_path:
            input_payload["image_url"] = request.start_frame_path

        # 2. End Frame / Last Frame mapping
        if request.end_frame_path:
            input_payload["tail_image_url"] = request.end_frame_path
            input_payload["end_image_url"] = request.end_frame_path

        if request.negative_prompt:
            input_payload["negative_prompt"] = request.negative_prompt

        # 3. Reference Images mapping
        all_refs = request.reference_image_paths or request.reference_assets
        if all_refs:
            ref_imgs = [a for a in all_refs if not a.endswith((".mp4", ".mov", ".webm"))]
            ref_vids = [a for a in all_refs if a.endswith((".mp4", ".mov", ".webm"))]
            if ref_imgs:
                ref_param = getattr(request.model_profile, "reference_param_name", "reference_images") or "reference_images"
                input_payload[ref_param] = ref_imgs
                input_payload["reference_images"] = ref_imgs
            if ref_vids:
                input_payload["reference_videos"] = ref_vids

        if request.audio_mode.value == "native_clip_audio":
            input_payload["audio"] = True
            input_payload["with_audio"] = True

        payload = {
            "model": target_model,
            "input": input_payload,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                res = await client.post(url, headers=self._get_headers(), json=payload)
                if res.status_code in (401, 403):
                    raise ProviderAuthenticationError(f"Kie.ai auth error: {res.text}", provider_id=self.provider_id, status_code=res.status_code)
                elif res.status_code == 402:
                    raise ProviderQuotaExceededError(f"Kie.ai quota error: {res.text}", provider_id=self.provider_id, status_code=res.status_code)
                elif res.status_code == 422:
                    raise ProviderPayloadValidationError(f"Kie.ai validation error: {res.text}", provider_id=self.provider_id, status_code=res.status_code)
                elif res.status_code >= 500:
                    raise ProviderInfrastructureError(f"Kie.ai server error: {res.text}", provider_id=self.provider_id, status_code=res.status_code)

                data = res.json()
                if isinstance(data, dict):
                    code = data.get("code")
                    msg = data.get("msg") or data.get("message")
                    if code and code not in (200, 0):
                        raise ProviderInfrastructureError(f"Kie.ai error ({code}): {msg}", provider_id=self.provider_id)
                data_obj = data.get("data") if (isinstance(data, dict) and isinstance(data.get("data"), dict)) else {}
                task_id = data.get("taskId") or data_obj.get("taskId") if isinstance(data, dict) else None
                if not task_id:
                    raise ProviderInfrastructureError(f"Kie.ai returned missing taskId ({data})", provider_id=self.provider_id)
                return str(task_id)
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                raise ProviderInfrastructureError(f"Kie.ai connection failure: {e}", provider_id=self.provider_id)

    async def poll_job_status(self, provider_task_id: str) -> Dict[str, Any]:
        url = f"https://api.kie.ai/api/v1/jobs/recordInfo?taskId={provider_task_id}"

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                res = await client.get(url, headers=self._get_headers())
                if res.status_code >= 500:
                    raise ProviderInfrastructureError(f"Kie.ai status check 5xx: {res.text}", provider_id=self.provider_id, status_code=res.status_code)
                data = res.json()
                task_data = data.get("data", data)
                state = str(task_data.get("state") or task_data.get("status") or "").lower()

                if state in ("success", "completed", "done"):
                    video_url = task_data.get("resultUrl") or task_data.get("videoUrl") or task_data.get("outputUrl")
                    return {
                        "status": JobExecutionStatus.COMPLETED,
                        "progress_percent": 100,
                        "video_url": video_url,
                        "error_message": None,
                        "billed_cost_usd": task_data.get("cost"),
                    }
                elif state in ("fail", "failed", "error"):
                    return {
                        "status": JobExecutionStatus.FAILED,
                        "progress_percent": 0,
                        "video_url": None,
                        "error_message": task_data.get("failReason") or "Task failed on Kie.ai",
                        "billed_cost_usd": 0.0,
                    }
                else:
                    return {
                        "status": JobExecutionStatus.IN_PROGRESS,
                        "progress_percent": task_data.get("progress", 50),
                        "video_url": None,
                        "error_message": None,
                    }
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                raise ProviderInfrastructureError(f"Kie.ai polling network failure: {e}", provider_id=self.provider_id)

    async def download_video_asset(self, video_url: str, destination_path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(destination_path)), exist_ok=True)
        async with httpx.AsyncClient(timeout=120.0) as client:
            res = await client.get(video_url)
            if res.status_code != 200:
                raise ProviderInfrastructureError(f"Failed to download asset from {video_url} ({res.status_code})")
            with open(destination_path, "wb") as f:
                f.write(res.content)
        return destination_path

    async def extend_video_clip(self, parent_task_id: str, continuation_prompt: str, added_duration_sec: float = 5.0) -> str:
        url = "https://api.kie.ai/api/v1/jobs/createTask"
        payload = {
            "model": "runway/extend-ai-video",
            "input": {
                "task_id": parent_task_id,
                "prompt": continuation_prompt,
                "duration": int(added_duration_sec),
            }
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(url, headers=self._get_headers(), json=payload)
            if res.status_code != 200:
                raise ProviderInfrastructureError(f"Kie.ai extend failed: {res.text}", provider_id=self.provider_id)
            return str(res.json().get("taskId"))

    async def cancel_job(self, provider_task_id: str) -> bool:
        url = f"https://api.kie.ai/api/v1/jobs/cancelTask?taskId={provider_task_id}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(url, headers=self._get_headers())
            return res.status_code in (200, 204)
