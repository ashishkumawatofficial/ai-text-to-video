"""Abstract Base Video Provider Interface and Exceptions for Channel 2 Multi-Model Video Generation."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import logging

from core.models import (
    ProviderId,
    VideoGenerationRequest,
    ProviderPriceQuote,
    JobExecutionStatus,
)

logger = logging.getLogger(__name__)


# --- Provider Exception Hierarchy ---

class ProviderError(Exception):
    """Base exception for all external provider errors."""
    def __init__(self, message: str, provider_id: Optional[ProviderId] = None, status_code: Optional[int] = None):
        super().__init__(message)
        self.provider_id = provider_id
        self.status_code = status_code


class ProviderAuthenticationError(ProviderError):
    """Raised when an API key is missing, unauthorized, or invalid (HTTP 401/403)."""
    pass


class ProviderQuotaExceededError(ProviderError):
    """Raised when account balance or credits are depleted (HTTP 402)."""
    pass


class ProviderPayloadValidationError(ProviderError):
    """Raised when prompt length, dimensions, or parameters violate API schema (HTTP 422)."""
    pass


class ProviderInfrastructureError(ProviderError):
    """Raised on upstream 5xx crashes, timeouts, or gateway drops. Eligible for zero-cost cascade."""
    pass


# --- Abstract Base Provider Class ---

class BaseVideoProvider(ABC):
    """Abstract interface defining required capabilities for every video generation provider."""

    @property
    @abstractmethod
    def provider_id(self) -> ProviderId:
        """Returns the unique ProviderId enum value."""
        pass

    @property
    @abstractmethod
    def official_docs_url(self) -> str:
        """Returns the verified developer documentation URL."""
        pass

    @property
    @abstractmethod
    def pricing_docs_url(self) -> str:
        """Returns the verified pricing documentation URL."""
        pass

    @property
    @abstractmethod
    def failure_billing_policy(self) -> str:
        """Human-readable explanation of provider failure billing rules."""
        pass

    @property
    def supports_zero_cost_failure(self) -> bool:
        """Whether this provider guarantees $0.00 charge on 5xx/crashes. Defaults to True."""
        return True

    @abstractmethod
    def is_configured(self) -> bool:
        """Checks if required API keys/tokens exist in configuration."""
        pass

    @abstractmethod
    async def get_price_quote(
        self,
        model_id: str,
        duration_sec: float,
        resolution: str = "720p",
        has_native_audio: bool = False,
    ) -> Optional[ProviderPriceQuote]:
        """Calculates or fetches the real-time cost quotation in USD.
        
        Returns None if the provider does not support the requested model.
        """
        pass

    @abstractmethod
    async def submit_video_job(
        self,
        request: VideoGenerationRequest,
    ) -> str:
        """Submits an asynchronous video generation task.
        
        Returns the external provider's unique task/job identifier string.
        """
        pass

    @abstractmethod
    async def poll_job_status(
        self,
        provider_task_id: str,
    ) -> Dict[str, Any]:
        """Queries the current status of an ongoing task.
        
        Returns dictionary containing:
            - status: JobExecutionStatus ("IN_PROGRESS", "COMPLETED", "FAILED", "TIMED_OUT")
            - progress_percent: int (0-100)
            - video_url: Optional[str] (when COMPLETED)
            - error_message: Optional[str] (when FAILED)
            - billed_cost_usd: Optional[float]
        """
        pass

    @abstractmethod
    async def download_video_asset(
        self,
        video_url: str,
        destination_path: str,
    ) -> str:
        """Streams and downloads the completed video MP4 file to a local destination."""
        pass

    @abstractmethod
    async def extend_video_clip(
        self,
        parent_task_id: str,
        continuation_prompt: str,
        added_duration_sec: float = 5.0,
    ) -> str:
        """Submits a video extension task continuing from the parent video's terminal state."""
        pass

    @abstractmethod
    async def cancel_job(
        self,
        provider_task_id: str,
    ) -> bool:
        """Attempts to abort an in-flight rendering task."""
        pass
