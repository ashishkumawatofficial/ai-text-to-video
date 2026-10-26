"""Real-Time Cost Arbitrage & Automatic Failure Cascading Engine."""

from __future__ import annotations
import time
import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any, Callable

from core.models import (
    ProviderId,
    ProviderPriceQuote,
    VideoGenerationRequest,
    RenderingJobTicket,
    JobExecutionStatus,
    VideoGenerationModality,
)
from core.providers.base_provider import (
    BaseVideoProvider,
    ProviderInfrastructureError,
    ProviderError,
)
from core.provider_registry import get_providers_for_model, get_model_profile
from core.providers.fal_provider import FalProvider
from core.providers.apidot_provider import ApidotProvider
from core.providers.kie_provider import KieProvider
from core.providers.serverless_provider import ServerlessProvider

logger = logging.getLogger(__name__)


# Global Registry of Known Provider Promotions & Free Quotas
ACTIVE_PROMOTIONS: Dict[str, Dict[ProviderId, Dict[str, Any]]] = {
    "flux-3-max": {
        ProviderId.FAL_AI: {
            "discount_pct": 75.0,
            "free_daily_videos": 5,
            "max_free_duration_sec": 15.0,
            "max_free_resolution": "720p",
            "description": "fal.ai Launch Offer: 75% OFF + Sandbox Free Tier (Up to 5 free 720p 15s videos/day)",
        }
    }
}


class CostArbitrageEngine:
    """Calculates real-time price quotes, ranks providers by lowest cost, and handles failover cascades."""

    def __init__(self):
        self._adapters: Dict[ProviderId, BaseVideoProvider] = {
            ProviderId.FAL_AI: FalProvider(),
            ProviderId.APIDOT_AI: ApidotProvider(),
            ProviderId.KIE_AI: KieProvider(),
            ProviderId.RUNPOD_SERVERLESS: ServerlessProvider(),
        }
        # In-memory quote cache: cache_key -> (timestamp, ProviderPriceQuote)
        self._quote_cache: Dict[str, Tuple[float, ProviderPriceQuote]] = {}
        self.default_ttl_sec = 600  # 10 minutes

    def get_adapter(self, provider_id: ProviderId) -> Optional[BaseVideoProvider]:
        """Retrieve the adapter instance for a given provider."""
        return self._adapters.get(provider_id)

    def clear_cache(self) -> None:
        """Flushes the in-memory quote cache."""
        self._quote_cache.clear()

    def get_active_promotions(self, model_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List active provider promotions, discounts, and free tier allowances."""
        results = []
        for mid, prov_map in ACTIVE_PROMOTIONS.items():
            if model_id and mid != model_id:
                continue
            for pid, details in prov_map.items():
                results.append({
                    "model_id": mid,
                    "provider_id": pid.value,
                    **details,
                })
        return results

    def _make_cache_key(
        self,
        provider_id: ProviderId,
        model_id: str,
        duration_sec: float,
        resolution: str,
        has_native_audio: bool,
    ) -> str:
        return f"{provider_id.value}:{model_id}:{duration_sec}:{resolution}:{has_native_audio}"

    async def _query_provider_quote(
        self,
        provider_id: ProviderId,
        model_id: str,
        duration_sec: float,
        resolution: str,
        has_native_audio: bool,
    ) -> Optional[ProviderPriceQuote]:
        """Queries a single provider with TTL caching and promotional overlay."""
        cache_key = self._make_cache_key(provider_id, model_id, duration_sec, resolution, has_native_audio)
        now = time.time()

        if cache_key in self._quote_cache:
            cached_at, cached_quote = self._quote_cache[cache_key]
            if now - cached_at < cached_quote.ttl_sec:
                return cached_quote

        adapter = self.get_adapter(provider_id)
        if not adapter:
            return None

        quote = await adapter.get_price_quote(
            model_id=model_id,
            duration_sec=duration_sec,
            resolution=resolution,
            has_native_audio=has_native_audio,
        )
        if quote:
            # Check active promotions and free tier policies
            promo = ACTIVE_PROMOTIONS.get(model_id, {}).get(provider_id)
            if promo:
                quote.is_promotional = True
                quote.discount_pct = max(quote.discount_pct, float(promo.get("discount_pct", 0.0)))
                if not quote.promo_description:
                    quote.promo_description = str(promo.get("description", ""))
                if (
                    duration_sec <= float(promo.get("max_free_duration_sec", 15.0))
                    and resolution in ("720p", "480p")
                    and int(promo.get("free_daily_videos", 0)) > 0
                ):
                    quote.free_tier_applicable = True

            self._quote_cache[cache_key] = (now, quote)
        return quote

    async def fetch_all_quotes(
        self,
        model_id: str,
        duration_sec: float = 5.0,
        resolution: str = "720p",
        has_native_audio: bool = False,
    ) -> List[ProviderPriceQuote]:
        """Fetches quotes from all providers that host the requested model."""
        candidate_ids = get_providers_for_model(model_id)
        quotes: List[ProviderPriceQuote] = []

        for pid in candidate_ids:
            try:
                quote = await self._query_provider_quote(
                    provider_id=pid,
                    model_id=model_id,
                    duration_sec=duration_sec,
                    resolution=resolution,
                    has_native_audio=has_native_audio,
                )
                if quote:
                    quotes.append(quote)
            except Exception as e:
                logger.warning(f"Failed to fetch price quote from {pid.value} for {model_id}: {e}")

        return quotes

    async def get_ranked_quotes(
        self,
        model_id: str,
        duration_sec: float = 5.0,
        resolution: str = "720p",
        has_native_audio: bool = False,
    ) -> List[ProviderPriceQuote]:
        """Fetches and sorts quotes in ascending order by availability, free tier eligibility, and estimated cost."""
        quotes = await self.fetch_all_quotes(
            model_id=model_id,
            duration_sec=duration_sec,
            resolution=resolution,
            has_native_audio=has_native_audio,
        )
        if not quotes:
            return []

        # Sort by: availability, free tier eligibility, and cost ascending
        quotes.sort(key=lambda q: (not q.is_available, not q.free_tier_applicable, q.estimated_total_usd))

        # Mark lowest as cheapest
        for idx, q in enumerate(quotes):
            q.is_cheapest = (idx == 0)

        return quotes

    async def resolve_target_provider(
        self,
        model_id: str,
        duration_sec: float = 5.0,
        resolution: str = "720p",
        has_native_audio: bool = False,
        provider_override: Optional[ProviderId] = None,
    ) -> Optional[ProviderPriceQuote]:
        """Determines target provider based on override or auto lowest-cost selection."""
        quotes = await self.get_ranked_quotes(
            model_id=model_id,
            duration_sec=duration_sec,
            resolution=resolution,
            has_native_audio=has_native_audio,
        )
        if not quotes:
            return None

        if provider_override and provider_override != ProviderId.AUTO:
            matching = next((q for q in quotes if q.provider_id == provider_override), None)
            if matching:
                return matching

        # Default: return cheapest available quote
        return quotes[0]

    async def execute_with_cascade(
        self,
        request: VideoGenerationRequest,
        candidate_providers: List[ProviderId],
        output_path: str,
        poll_interval_sec: float = 3.0,
        max_timeout_sec: float = 600.0,
        progress_callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ) -> RenderingJobTicket:
        """Dispatches job with automatic failover to the next candidate provider on infrastructure failure."""
        last_error = None

        for attempt_idx, pid in enumerate(candidate_providers):
            adapter = self.get_adapter(pid)
            if not adapter or not adapter.is_configured():
                continue

            logger.info(f"Attempting render on provider: {pid.value} (Attempt {attempt_idx + 1}/{len(candidate_providers)})")
            ticket = RenderingJobTicket(
                project_id=request.project_id,
                beat_index=request.beat_index,
                provider_id=pid,
                provider_task_id="pending",
                model_id=request.model_profile.model_id,
                status=JobExecutionStatus.SUBMITTED,
                modality=request.modality,
                has_native_audio=(request.audio_mode.value == "native_clip_audio"),
                retry_count=attempt_idx,
            )

            try:
                # Submit job
                task_id = await adapter.submit_video_job(request)
                ticket.provider_task_id = task_id
                ticket.status = JobExecutionStatus.IN_PROGRESS

                # Initial submission progress callback
                if progress_callback:
                    try:
                        res = progress_callback({
                            "provider_id": pid.value,
                            "provider_task_id": task_id,
                            "status": "SUBMITTED",
                            "progress_percent": 10,
                            "queue_position": None,
                        })
                        if asyncio.iscoroutine(res):
                            await res
                    except Exception as cb_err:
                        logger.debug(f"Progress callback initial error: {cb_err}")

                # Poll until terminal status
                start_time = time.time()
                while time.time() - start_time < max_timeout_sec:
                    status_info = await adapter.poll_job_status(task_id)
                    current_status = status_info.get("status")

                    if progress_callback:
                        try:
                            status_val = current_status.value if hasattr(current_status, "value") else str(current_status)
                            res = progress_callback({
                                "provider_id": pid.value,
                                "provider_task_id": task_id,
                                "status": status_val,
                                "progress_percent": status_info.get("progress_percent", 50),
                                "queue_position": status_info.get("queue_position"),
                            })
                            if asyncio.iscoroutine(res):
                                await res
                        except Exception as cb_err:
                            logger.debug(f"Progress callback polling error: {cb_err}")

                    if current_status == JobExecutionStatus.COMPLETED:
                        video_url = status_info.get("video_url")
                        if not video_url:
                            raise ProviderInfrastructureError("Completed task missing video_url", provider_id=pid)

                        downloaded_path = await adapter.download_video_asset(video_url, output_path)
                        ticket.status = JobExecutionStatus.COMPLETED
                        ticket.output_video_path = downloaded_path
                        ticket.actual_billed_usd = status_info.get("billed_cost_usd", 0.0)
                        ticket.completed_at = time.time()
                        logger.info(f"Render succeeded on {pid.value}: {downloaded_path}")
                        return ticket

                    elif current_status == JobExecutionStatus.FAILED:
                        raise ProviderInfrastructureError(
                            status_info.get("error_message", "Task failed on provider"),
                            provider_id=pid
                        )

                    await asyncio.sleep(poll_interval_sec)

                # Polling timed out
                await adapter.cancel_job(task_id)
                raise ProviderInfrastructureError("Task polling exceeded max_timeout_sec", provider_id=pid)

            except ProviderInfrastructureError as e:
                logger.warning(f"Provider {pid.value} encountered infrastructure error: {e}. Cascading to next candidate.")
                ticket.status = JobExecutionStatus.CASCADED
                ticket.error_message = str(e)
                last_error = e
                continue
            except Exception as e:
                logger.error(f"Non-retryable provider error on {pid.value}: {e}")
                ticket.status = JobExecutionStatus.FAILED
                ticket.error_message = str(e)
                raise e

        # All candidates exhausted
        raise ProviderInfrastructureError(f"All candidate providers failed. Last error: {last_error}")
