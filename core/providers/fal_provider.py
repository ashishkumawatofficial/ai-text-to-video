"""fal.ai Provider Adapter for Channel 2 Multi-Model Video Generation."""

from __future__ import annotations
import os
import time
import asyncio
import logging
from typing import Optional, Dict, Any

import httpx

from core.config import get_fal_key, get_provider_timeout_sec
from core.models import (
    ProviderId,
    VideoGenerationRequest,
    VideoGenerationModality,
    VideoModelFamily,
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

# fal.ai rates per second in USD (calibrated per model version and tier)
FAL_MODEL_RATES: Dict[str, float] = {
    # Kling AI Family
    "kling-v1.0": 0.065,
    "kling-v1.0-pro": 0.075,
    "kling-v1.5-std": 0.075,
    "kling-v1.5": 0.090,
    "kling-v2.0": 0.115,
    "kling-v2.5": 0.125,
    "kling-v3.0": 0.140,
    "kling-v4.0": 0.160,

    # ByteDance Seedance Family
    "seedance-1.0": 0.030,
    "seedance-1.5": 0.040,
    "seedance-2.0": 0.060,
    "seedance-2.5": 0.080,

    # Runway Family
    "runway-gen2": 0.030,
    "runway-gen3-alpha": 0.100,
    "runway-gen3-turbo": 0.050,

    # MiniMax Hailuo Family
    "minimax-hailuo-01": 0.060,
    "minimax-hailuo-live": 0.075,
    "minimax-h3": 0.095,

    # Google Veo Family
    "veo-2": 0.190,
    "veo-3": 0.280,
    "veo-3.1": 0.320,

    # Alibaba Wan Family
    "wan-2.1-t2v-1.3b": 0.020,
    "wan-2.1": 0.045,
    "wan-2.1-i2v-720p": 0.045,
    "wan-2.2": 0.065,
    "wan-3.0": 0.100,

    # xAI Grok Family
    "grok-video-1.5": 0.035,

    # Luma Dream Machine Family
    "luma-ray1": 0.060,
    "luma-ray2": 0.100,

    # PixVerse Family
    "pixverse-v2": 0.040,
    "pixverse-v3": 0.070,

    # Pika Family
    "pika-1.0": 0.035,
    "pika-2.0": 0.065,

    # ShengShu Vidu Family
    "vidu-1.5": 0.050,
    "vidu-2.0": 0.080,

    # Open-Weights / Budget Family
    "cogvideox-2b": 0.018,
    "cogvideox-5b": 0.035,
    "hunyuan-video": 0.050,
    "mochi-1": 0.055,

    # FLUX Video Family (Black Forest Labs & fal Research)
    "flux-3-max": 0.02125,  # 75% Launch promotional discount (standard 0.085)
    "flux-3": 0.085,
}

FAL_MODEL_ENDPOINTS: Dict[str, Dict[str, str]] = {
    "flux-3-max": {
        "t2v": "blackforestlabs/flux-3-max/text-to-video",
        "i2v": "blackforestlabs/flux-3-max/image-to-video",
        "interpolation": "blackforestlabs/flux-3-max/keyframes-to-video",
    },
    "flux-3": {
        "t2v": "blackforestlabs/flux-3/text-to-video",
        "i2v": "blackforestlabs/flux-3/image-to-video",
        "interpolation": "blackforestlabs/flux-3/keyframes-to-video",
    },
    "kling-v1.5": {
        "t2v": "fal-ai/kling-video/v1.5/pro/text-to-video",
        "i2v": "fal-ai/kling-video/v1.5/pro/image-to-video",
    },
    "kling-v2.0": {
        "t2v": "fal-ai/kling-video/v2/pro/text-to-video",
        "i2v": "fal-ai/kling-video/v2/pro/image-to-video",
    },
    "kling-v2.5": {
        "t2v": "fal-ai/kling-video/v2.5/turbo/text-to-video",
        "i2v": "fal-ai/kling-video/v2.5/turbo/image-to-video",
    },
    "kling-v3.0": {
        "t2v": "fal-ai/kling-video/v3/pro/text-to-video",
        "i2v": "fal-ai/kling-video/v3/pro/image-to-video",
    },
    "kling-v4.0": {
        "t2v": "fal-ai/kling-video/v4/pro/text-to-video",
        "i2v": "fal-ai/kling-video/v4/pro/image-to-video",
    },
    "runway-gen3-turbo": {
        "t2v": "fal-ai/runway-gen3/turbo/text-to-video",
        "i2v": "fal-ai/runway-gen3/turbo/image-to-video",
    },
    "minimax-h3": {
        "t2v": "fal-ai/minimax/h3/text-to-video",
        "i2v": "fal-ai/minimax/h3/image-to-video",
    },
    "wan-2.1": {
        "t2v": "fal-ai/wan/v2.1",
        "i2v": "fal-ai/wan/v2.1/image-to-video",
    },
    "wan-2.2": {
        "t2v": "fal-ai/wan/v2.2",
        "i2v": "fal-ai/wan/v2.2/image-to-video",
    },
    "wan-3.0": {
        "t2v": "fal-ai/wan/v3.0",
        "i2v": "fal-ai/wan/v3.0/image-to-video",
    },
    "luma-ray2": {
        "t2v": "fal-ai/luma-dream-machine",
        "i2v": "fal-ai/luma-dream-machine/image-to-video",
    },
    "veo-2": {
        "t2v": "fal-ai/veo2",
        "i2v": "fal-ai/veo2/image-to-video",
    },
    "veo-3.1": {
        "t2v": "fal-ai/veo-3.1",
        "i2v": "fal-ai/veo-3.1/image-to-video",
    },
    "cogvideox-5b": {
        "t2v": "fal-ai/cogvideox-5b",
        "i2v": "fal-ai/cogvideox-5b/image-to-video",
    },
    "hunyuan-video": {
        "t2v": "fal-ai/hunyuan-video",
        "i2v": "fal-ai/hunyuan-video/image-to-video",
    },
    "grok-video-1.5": {
        "t2v": "fal-ai/grok-video/v1.5",
        "i2v": "fal-ai/grok-video/v1.5/image-to-video",
    },
}


class FalProvider(BaseVideoProvider):
    """Adapter for fal.ai queue and inference API."""

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or get_fal_key()
        self._live_price_cache: Dict[str, tuple[float, str, float]] = {}

    @property
    def provider_id(self) -> ProviderId:
        return ProviderId.FAL_AI

    @property
    def official_docs_url(self) -> str:
        return "https://fal.ai/docs"

    @property
    def pricing_docs_url(self) -> str:
        return "https://fal.ai/pricing"

    @property
    def failure_billing_policy(self) -> str:
        return "Zero-cost guarantee: HTTP 5xx errors, cold starts, and queue wait times are strictly $0.00."

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _get_headers(self) -> Dict[str, str]:
        if not self.is_configured():
            raise ProviderAuthenticationError("Missing FAL_KEY in environment", provider_id=self.provider_id)
        return {
            "Authorization": f"Key {self._api_key}",
            "Content-Type": "application/json",
        }

    async def _fetch_live_pricing(self, endpoint: str) -> Optional[tuple[float, str]]:
        """Queries fal.ai live pricing API with in-memory TTL caching."""
        now = time.time()
        if endpoint in self._live_price_cache:
            price, unit, ts = self._live_price_cache[endpoint]
            if now - ts < 600:  # 10-minute cache window
                return price, unit

        if not self.is_configured():
            return None

        try:
            async with httpx.AsyncClient(timeout=2.5) as client:
                res = await client.get(
                    f"https://api.fal.ai/v1/models/pricing?endpoint_id={endpoint}",
                    headers=self._get_headers(),
                )
                if res.status_code == 200:
                    data = res.json()
                    prices = data.get("prices", [])
                    if prices:
                        unit = prices[0].get("unit", "seconds")
                        unit_price = float(prices[0].get("unit_price", 0.0))
                        self._live_price_cache[endpoint] = (unit_price, unit, now)
                        return unit_price, unit
        except Exception as e:
            logger.debug("Fal live pricing fetch failed for %s, falling back: %s", endpoint, e)

        return None

    async def get_price_quote(
        self,
        model_id: str,
        duration_sec: float,
        resolution: str = "720p",
        has_native_audio: bool = False,
    ) -> Optional[ProviderPriceQuote]:
        endpoint = self._resolve_endpoint(model_id, VideoGenerationModality.TEXT_TO_VIDEO)
        live_info = await self._fetch_live_pricing(endpoint)

        if live_info:
            live_rate, unit = live_info
            if unit == "seconds" and live_rate > 0:
                base_rate = live_rate
            elif unit == "videos" and live_rate > 0:
                base_rate = round(live_rate / max(duration_sec, 1.0), 4)
            else:
                base_rate = FAL_MODEL_RATES.get(model_id, 0.05)
        else:
            if model_id not in FAL_MODEL_RATES:
                return None
            base_rate = FAL_MODEL_RATES[model_id]

        if resolution == "480p":
            base_rate *= 0.60
        elif resolution == "1080p":
            base_rate *= 1.35
        elif resolution == "4k":
            base_rate *= 2.0

        if has_native_audio:
            base_rate += 0.02

        total_cost = round(base_rate * duration_sec, 4)

        standard_baseline = 0.085 if "flux-3-max" in model_id else FAL_MODEL_RATES.get(model_id, base_rate)
        is_promo = False
        discount_pct = 0.0
        promo_desc = None
        if standard_baseline > base_rate and standard_baseline > 0:
            discount_pct = round(((standard_baseline - base_rate) / standard_baseline) * 100, 1)
            is_promo = True
            promo_desc = f"Special {int(discount_pct)}% OFF promotional rate"

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
            discount_pct=discount_pct,
            is_promotional=is_promo,
            promo_description=promo_desc,
        )

    def _resolve_endpoint(self, model_id: str, modality: VideoGenerationModality) -> str:
        if modality == VideoGenerationModality.START_END_INTERPOLATION:
            if model_id in FAL_MODEL_ENDPOINTS and "interpolation" in FAL_MODEL_ENDPOINTS[model_id]:
                return FAL_MODEL_ENDPOINTS[model_id]["interpolation"]
        mod_key = "i2v" if modality in (VideoGenerationModality.IMAGE_TO_VIDEO, VideoGenerationModality.START_END_INTERPOLATION) else "t2v"
        if model_id in FAL_MODEL_ENDPOINTS and mod_key in FAL_MODEL_ENDPOINTS[model_id]:
            return FAL_MODEL_ENDPOINTS[model_id][mod_key]
        return f"fal-ai/{model_id}"

    async def submit_video_job(self, request: VideoGenerationRequest) -> str:
        endpoint = self._resolve_endpoint(request.model_profile.model_id, request.modality)
        url = f"https://queue.fal.run/{endpoint}"

        payload: Dict[str, Any] = {
            "prompt": request.prompt,
            "duration": str(int(request.duration_sec)),
            "aspect_ratio": request.aspect_ratio,
        }

        if request.negative_prompt:
            payload["negative_prompt"] = request.negative_prompt

        # 0. Keyframes payload for models supporting dedicated keyframe sequences (e.g. FLUX 3 Max)
        if "keyframes-to-video" in endpoint:
            keyframes = []
            if request.start_frame_path:
                keyframes.append({"image_url": request.start_frame_path, "frame_index": 0})
            if request.end_frame_path:
                fps = 24
                last_frame = max(int(request.duration_sec * fps) - 1, 1)
                keyframes.append({"image_url": request.end_frame_path, "frame_index": last_frame})
            if keyframes:
                payload["keyframes"] = keyframes

        # 1. Start Frame / First Frame mapping
        if request.start_frame_path and (request.modality in [VideoGenerationModality.IMAGE_TO_VIDEO, VideoGenerationModality.START_END_INTERPOLATION] or request.model_profile.supports_i2v):
            payload["image_url"] = request.start_frame_path
            # Endpoint-specific aliases
            if request.model_profile.family == VideoModelFamily.MINIMAX:
                payload["first_frame_image"] = request.start_frame_path
            elif request.model_profile.family == VideoModelFamily.VIDU:
                payload["start_image_url"] = request.start_frame_path

        # 2. End Frame / Last Frame mapping
        if request.end_frame_path and (request.modality == VideoGenerationModality.START_END_INTERPOLATION or request.model_profile.supports_dual_frame):
            if request.model_profile.family == VideoModelFamily.KLING:
                payload["tail_image_url"] = request.end_frame_path
                payload["end_image_url"] = request.end_frame_path
            elif request.model_profile.family in (VideoModelFamily.LUMA, VideoModelFamily.RUNWAY):
                payload["image_end_url"] = request.end_frame_path
                payload["end_image_url"] = request.end_frame_path
            elif request.model_profile.family == VideoModelFamily.VIDU:
                payload["end_image_url"] = request.end_frame_path
            else:
                payload["end_image_url"] = request.end_frame_path
                payload["tail_image_url"] = request.end_frame_path

        # 3. Reference Images & Videos mapping
        all_refs = request.reference_image_paths or request.reference_assets
        if all_refs:
            ref_imgs = [a for a in all_refs if not a.endswith((".mp4", ".mov", ".webm"))]
            ref_vids = [a for a in all_refs if a.endswith((".mp4", ".mov", ".webm"))]
            if ref_imgs:
                ref_param = getattr(request.model_profile, "reference_param_name", "reference_images") or "reference_images"
                payload[ref_param] = ref_imgs
                payload["reference_images"] = ref_imgs
                payload["image_urls"] = ref_imgs
            if ref_vids:
                payload["reference_videos"] = ref_vids

        if request.resolution:
            payload["resolution"] = request.resolution

        if request.audio_mode.value == "native_clip_audio" or request.model_profile.supports_native_audio:
            payload["generate_audio"] = (request.audio_mode.value == "native_clip_audio")

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                res = await client.post(url, headers=self._get_headers(), json=payload)
                if res.status_code in (401, 403):
                    raise ProviderAuthenticationError(f"fal.ai auth error: {res.text}", provider_id=self.provider_id, status_code=res.status_code)
                elif res.status_code == 402:
                    raise ProviderQuotaExceededError(f"fal.ai quota error: {res.text}", provider_id=self.provider_id, status_code=res.status_code)
                elif res.status_code == 422:
                    raise ProviderPayloadValidationError(f"fal.ai validation error: {res.text}", provider_id=self.provider_id, status_code=res.status_code)
                elif res.status_code >= 500:
                    raise ProviderInfrastructureError(f"fal.ai server error: {res.text}", provider_id=self.provider_id, status_code=res.status_code)

                data = res.json()
                task_id = data.get("request_id")
                if not task_id:
                    raise ProviderInfrastructureError("fal.ai returned missing request_id", provider_id=self.provider_id)
                return task_id
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                raise ProviderInfrastructureError(f"fal.ai connection failure: {e}", provider_id=self.provider_id)

    async def poll_job_status(self, provider_task_id: str) -> Dict[str, Any]:
        url = f"https://queue.fal.run/requests/{provider_task_id}/status?logs=true"
        timeout_sec = get_provider_timeout_sec()

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                res = await client.get(url, headers=self._get_headers())
                if res.status_code >= 500:
                    raise ProviderInfrastructureError(f"fal.ai status check 5xx: {res.text}", provider_id=self.provider_id, status_code=res.status_code)
                data = res.json()
                status_raw = data.get("status", "IN_PROGRESS")

                if status_raw == "COMPLETED":
                    # Fetch final result payload
                    res_url = f"https://queue.fal.run/requests/{provider_task_id}"
                    final_res = await client.get(res_url, headers=self._get_headers())
                    result_data = final_res.json() if final_res.status_code == 200 else {}
                    video_info = result_data.get("video", {})
                    video_url = video_info.get("url") if isinstance(video_info, dict) else str(video_info)
                    return {
                        "status": JobExecutionStatus.COMPLETED,
                        "progress_percent": 100,
                        "video_url": video_url,
                        "error_message": None,
                        "billed_cost_usd": result_data.get("cost_usd"),
                    }
                elif status_raw in ("FAILED", "ERROR"):
                    return {
                        "status": JobExecutionStatus.FAILED,
                        "progress_percent": 0,
                        "video_url": None,
                        "error_message": data.get("error", "Task failed on fal.ai"),
                        "billed_cost_usd": 0.0,
                    }
                elif status_raw == "IN_QUEUE":
                    q_pos = data.get("queue_position", 1)
                    return {
                        "status": JobExecutionStatus.QUEUED,
                        "progress_percent": max(5, 20 - min(q_pos * 2, 15)),
                        "video_url": None,
                        "error_message": None,
                        "queue_position": q_pos,
                    }
                else:
                    progress = 50
                    logs = data.get("logs", [])
                    if logs:
                        import re
                        for log_entry in reversed(logs):
                            msg = log_entry.get("message", "") if isinstance(log_entry, dict) else str(log_entry)
                            pct_m = re.search(r"(\d+)%", msg)
                            if pct_m:
                                progress = min(99, max(5, int(pct_m.group(1))))
                                break
                            step_m = re.search(r"(\d+)\s*/\s*(\d+)", msg)
                            if step_m:
                                cur, total = int(step_m.group(1)), int(step_m.group(2))
                                if total > 0:
                                    progress = min(99, max(5, int((cur / total) * 100)))
                                    break
                    return {
                        "status": JobExecutionStatus.IN_PROGRESS,
                        "progress_percent": progress,
                        "video_url": None,
                        "error_message": None,
                    }
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                raise ProviderInfrastructureError(f"fal.ai polling network failure: {e}", provider_id=self.provider_id)

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
        # fal.ai extend uses video continuation endpoints
        url = "https://queue.fal.run/fal-ai/kling-video/v1.5/pro/extend"
        payload = {
            "video_id": parent_task_id,
            "prompt": continuation_prompt,
            "duration": str(int(added_duration_sec)),
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(url, headers=self._get_headers(), json=payload)
            if res.status_code != 200:
                raise ProviderInfrastructureError(f"fal.ai extend failed: {res.text}", provider_id=self.provider_id)
            return res.json().get("request_id")

    async def cancel_job(self, provider_task_id: str) -> bool:
        url = f"https://queue.fal.run/requests/{provider_task_id}/cancel"
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(url, headers=self._get_headers())
            return res.status_code in (200, 204)
