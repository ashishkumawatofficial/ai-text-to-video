"""APIDot Provider Adapter for Channel 2 Multi-Model Video Generation."""

from __future__ import annotations
import os
import asyncio
import logging
from typing import Optional, Dict, Any

import httpx

from core.config import get_apidot_key, get_provider_timeout_sec
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

# APIDot rates per second in USD (calibrated per model version and tier)
APIDOT_MODEL_RATES: Dict[str, float] = {
    # Kling AI Family (APIDot offers competitive Asian provider wholesale pricing)
    "kling-v1.0": 0.055,
    "kling-v1.0-pro": 0.065,
    "kling-v1.5-std": 0.068,
    "kling-v1.5": 0.080,
    "kling-v2.0": 0.100,
    "kling-v2.5": 0.110,
    "kling-v3.0": 0.125,
    "kling-v4.0": 0.140,

    # ByteDance Seedance Family
    "seedance-1.0": 0.025,
    "seedance-1.5": 0.030,
    "seedance-2.0": 0.050,
    "seedance-2.5": 0.070,

    # Runway Family
    "runway-gen2": 0.028,
    "runway-gen3-alpha": 0.095,
    "runway-gen3-turbo": 0.048,

    # MiniMax Hailuo Family
    "minimax-hailuo-01": 0.055,
    "minimax-hailuo-live": 0.068,
    "minimax-h3": 0.085,

    # Google Veo Family
    "veo-2": 0.175,
    "veo-3": 0.260,
    "veo-3.1": 0.290,

    # Alibaba Wan Family
    "wan-2.1-t2v-1.3b": 0.018,
    "wan-2.1": 0.038,
    "wan-2.1-i2v-720p": 0.038,
    "wan-2.2": 0.055,
    "wan-3.0": 0.090,

    # xAI Grok Family
    "grok-video-1.5": 0.028,

    # Luma Dream Machine Family
    "luma-ray1": 0.055,
    "luma-ray2": 0.090,

    # PixVerse Family
    "pixverse-v2": 0.035,
    "pixverse-v3": 0.065,

    # Pika Family
    "pika-1.0": 0.032,
    "pika-2.0": 0.060,

    # ShengShu Vidu Family
    "vidu-1.5": 0.045,
    "vidu-2.0": 0.075,

    # Open-Weights / Budget Family
    "cogvideox-2b": 0.015,
    "cogvideox-5b": 0.030,
    "hunyuan-video": 0.042,
    "mochi-1": 0.048,
}


class ApidotProvider(BaseVideoProvider):
    """Adapter for APIDot unified AI video API gateway."""

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or get_apidot_key()

    @property
    def provider_id(self) -> ProviderId:
        return ProviderId.APIDOT_AI

    @property
    def official_docs_url(self) -> str:
        return "https://apidot.ai/docs"

    @property
    def pricing_docs_url(self) -> str:
        return "https://apidot.ai/pricing"

    @property
    def failure_billing_policy(self) -> str:
        return "Credit protection: Tasks that fail or crash do not consume credits or are automatically refunded."

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _get_headers(self) -> Dict[str, str]:
        if not self.is_configured():
            raise ProviderAuthenticationError("Missing APIDOT_API_KEY in environment", provider_id=self.provider_id)
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
        if model_id not in APIDOT_MODEL_RATES:
            return None

        base_rate = APIDOT_MODEL_RATES[model_id]
        if resolution == "480p":
            base_rate *= 0.60
        elif resolution == "1080p":
            base_rate *= 1.25
        elif resolution == "4k":
            base_rate *= 1.85

        if has_native_audio:
            base_rate += 0.015

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
        url = "https://api.apidot.ai/v1/video/generations"
        payload: Dict[str, Any] = {
            "model": request.model_profile.model_id,
            "prompt": request.prompt,
            "duration": int(request.duration_sec),
            "aspect_ratio": request.aspect_ratio,
            "resolution": request.resolution,
        }

        # 1. Start Frame / First Frame mapping
        if request.start_frame_path:
            payload["image_url"] = request.start_frame_path
            payload["image"] = request.start_frame_path

        # 2. End Frame / Last Frame mapping
        if request.end_frame_path:
            payload["tail_image_url"] = request.end_frame_path
            payload["end_image_url"] = request.end_frame_path

        if request.negative_prompt:
            payload["negative_prompt"] = request.negative_prompt

        # 3. Reference Images mapping
        all_refs = request.reference_image_paths or request.reference_assets
        if all_refs:
            ref_imgs = [a for a in all_refs if not a.endswith((".mp4", ".mov", ".webm"))]
            ref_vids = [a for a in all_refs if a.endswith((".mp4", ".mov", ".webm"))]
            if ref_imgs:
                ref_param = getattr(request.model_profile, "reference_param_name", "reference_images") or "reference_images"
                payload[ref_param] = ref_imgs
                payload["reference_images"] = ref_imgs
            if ref_vids:
                payload["reference_videos"] = ref_vids

        if request.audio_mode.value == "native_clip_audio":
            payload["with_audio"] = True

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                res = await client.post(url, headers=self._get_headers(), json=payload)
                if res.status_code in (401, 403):
                    raise ProviderAuthenticationError(f"APIDot auth error: {res.text}", provider_id=self.provider_id, status_code=res.status_code)
                elif res.status_code == 402:
                    raise ProviderQuotaExceededError(f"APIDot quota error: {res.text}", provider_id=self.provider_id, status_code=res.status_code)
                elif res.status_code == 422:
                    raise ProviderPayloadValidationError(f"APIDot validation error: {res.text}", provider_id=self.provider_id, status_code=res.status_code)
                elif res.status_code >= 500:
                    raise ProviderInfrastructureError(f"APIDot server error: {res.text}", provider_id=self.provider_id, status_code=res.status_code)

                data = res.json()
                task_id = data.get("task_id") or data.get("id")
                if not task_id:
                    raise ProviderInfrastructureError("APIDot returned missing task_id", provider_id=self.provider_id)
                return task_id
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                raise ProviderInfrastructureError(f"APIDot connection failure: {e}", provider_id=self.provider_id)

    async def poll_job_status(self, provider_task_id: str) -> Dict[str, Any]:
        url = f"https://api.apidot.ai/v1/tasks/{provider_task_id}"

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                res = await client.get(url, headers=self._get_headers())
                if res.status_code >= 500:
                    raise ProviderInfrastructureError(f"APIDot status check 5xx: {res.text}", provider_id=self.provider_id, status_code=res.status_code)
                data = res.json()
                status_raw = data.get("status", "running").lower()

                if status_raw in ("success", "completed", "done"):
                    return {
                        "status": JobExecutionStatus.COMPLETED,
                        "progress_percent": 100,
                        "video_url": data.get("output_url") or data.get("video_url"),
                        "error_message": None,
                        "billed_cost_usd": data.get("actual_cost_usd"),
                    }
                elif status_raw in ("failed", "error"):
                    return {
                        "status": JobExecutionStatus.FAILED,
                        "progress_percent": 0,
                        "video_url": None,
                        "error_message": data.get("error_message", "Task failed on APIDot"),
                        "billed_cost_usd": 0.0,
                    }
                else:
                    return {
                        "status": JobExecutionStatus.IN_PROGRESS,
                        "progress_percent": data.get("progress", 50),
                        "video_url": None,
                        "error_message": None,
                    }
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                raise ProviderInfrastructureError(f"APIDot polling network failure: {e}", provider_id=self.provider_id)

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
        url = "https://api.apidot.ai/v1/video/extend"
        payload = {
            "task_id": parent_task_id,
            "prompt": continuation_prompt,
            "added_duration": int(added_duration_sec),
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(url, headers=self._get_headers(), json=payload)
            if res.status_code != 200:
                raise ProviderInfrastructureError(f"APIDot extend failed: {res.text}", provider_id=self.provider_id)
            return res.json().get("task_id")

    async def cancel_job(self, provider_task_id: str) -> bool:
        url = f"https://api.apidot.ai/v1/tasks/{provider_task_id}/cancel"
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(url, headers=self._get_headers())
            return res.status_code in (200, 204)
