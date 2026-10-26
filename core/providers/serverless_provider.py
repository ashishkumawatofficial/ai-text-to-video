"""RunPod Serverless Provider Adapter (Channel 1 Private Workers)."""

from __future__ import annotations
import os
import asyncio
import logging
from typing import Optional, Dict, Any

from core.models import (
    ProviderId,
    VideoGenerationRequest,
    VideoGenerationModality,
    ProviderPriceQuote,
    JobExecutionStatus,
)
from core.providers.base_provider import (
    BaseVideoProvider,
    ProviderInfrastructureError,
    ProviderAuthenticationError,
)
from core.runpod_serverless import RunPodServerlessClient, RunPodServerlessError

logger = logging.getLogger(__name__)


class ServerlessProvider(BaseVideoProvider):
    """Adapter for private on-demand RunPod serverless GPU workers (Channel 1)."""

    def __init__(self, client: Optional[RunPodServerlessClient] = None):
        self._client = client or RunPodServerlessClient()

    @property
    def provider_id(self) -> ProviderId:
        return ProviderId.RUNPOD_SERVERLESS

    @property
    def official_docs_url(self) -> str:
        return "https://docs.runpod.io/serverless/overview"

    @property
    def pricing_docs_url(self) -> str:
        return "https://www.runpod.io/pricing"

    @property
    def failure_billing_policy(self) -> str:
        return "Direct compute metering: Only active worker execution milliseconds are billed."

    def is_configured(self) -> bool:
        return self._client.is_available()

    async def get_price_quote(
        self,
        model_id: str,
        duration_sec: float,
        resolution: str = "720p",
        has_native_audio: bool = False,
    ) -> Optional[ProviderPriceQuote]:
        # Serverless currently serves Wan 2.1 open weights
        if not model_id.startswith("wan"):
            return None

        # Standard RTX 4090 serverless compute rate ($0.00021 / GPU-sec)
        # 5 seconds of video typically requires ~45 seconds of diffusion computation
        estimated_compute_sec = duration_sec * 9.0
        rate_per_sec = 0.00021
        total_cost = round(estimated_compute_sec * rate_per_sec, 4)

        return ProviderPriceQuote(
            provider_id=self.provider_id,
            model_id=model_id,
            duration_sec=duration_sec,
            resolution=resolution,
            native_audio_enabled=has_native_audio,
            rate_per_sec_usd=round(total_cost / max(1.0, duration_sec), 4),
            estimated_total_usd=total_cost,
            billing_unit="active_compute_sec",
            is_available=self.is_configured(),
        )

    async def submit_video_job(self, request: VideoGenerationRequest) -> str:
        if not self.is_configured():
            raise ProviderAuthenticationError("Missing RunPod Serverless credentials", provider_id=self.provider_id)

        from core.runpod_client import build_wan3_workflow_payload, Wan3WorkflowConfig
        from core.runpod_serverless import calculate_safe_video_frames

        safe_frames = calculate_safe_video_frames(request.duration_sec)
        wan_cfg = Wan3WorkflowConfig(
            prompt=request.prompt,
            duration_frames=safe_frames,
            reference_images=[request.start_frame_path] if request.start_frame_path else [],
        )
        workflow = build_wan3_workflow_payload(wan_cfg)

        try:
            job = self._client.submit_job(
                workflow=workflow,
                beat_index=request.beat_index,
                beat_name=f"Beat {request.beat_index}",
            )
            return job.job_id
        except Exception as e:
            raise ProviderInfrastructureError(f"RunPod Serverless submission error: {e}", provider_id=self.provider_id)

    async def poll_job_status(self, provider_task_id: str) -> Dict[str, Any]:
        try:
            job_info = self._client.poll_job(provider_task_id)
            status_str = str(job_info.get("status", "IN_PROGRESS"))
            
            if status_str == "COMPLETED":
                output = job_info.get("output", {})
                video_url = output.get("video_url") or output.get("output")
                return {
                    "status": JobExecutionStatus.COMPLETED,
                    "progress_percent": 100,
                    "video_url": video_url,
                    "error_message": None,
                    "billed_cost_usd": (job_info.get("executionTime", 0.0) / 1000.0) * 0.00021,
                }
            elif status_str in ("FAILED", "CANCELLED", "TIMED_OUT"):
                return {
                    "status": JobExecutionStatus.FAILED,
                    "progress_percent": 0,
                    "video_url": None,
                    "error_message": job_info.get("error", "Serverless job failed"),
                    "billed_cost_usd": 0.0,
                }
            else:
                return {
                    "status": JobExecutionStatus.IN_PROGRESS,
                    "progress_percent": 50,
                    "video_url": None,
                    "error_message": None,
                }
        except Exception as e:
            raise ProviderInfrastructureError(f"Serverless status check error: {e}", provider_id=self.provider_id)

    async def download_video_asset(self, video_url: str, destination_path: str) -> str:
        # If output is a local path or data URL, handle via RunPod client helper
        return self._client.download_video_output(video_url, destination_path)

    async def extend_video_clip(self, parent_task_id: str, continuation_prompt: str, added_duration_sec: float = 5.0) -> str:
        raise NotImplementedError("Serverless Wan 2.1 currently uses tail-frame chaining rather than API extension")

    async def cancel_job(self, provider_task_id: str) -> bool:
        return self._client.cancel_job(provider_task_id)
