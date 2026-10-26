# Provider Adapter Interface Contract

**Feature Branch**: `010-multi-provider-video-routing`
**Date**: 2026-10-25
**Interface**: `core/providers/base_provider.py`

This document defines the abstract class contract that every video provider adapter (`FalProvider`, `ApidotProvider`, `KieProvider`, `ServerlessProvider`) must implement.

---

## Abstract Base Class: `BaseVideoProvider`

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from core.models import (
    ProviderId,
    VideoGenerationRequest,
    RenderingJobTicket,
    ProviderPriceQuote,
    JobExecutionStatus,
)

class BaseVideoProvider(ABC):
    """Abstract interface governing all third-party video generation providers."""

    @property
    @abstractmethod
    def provider_id(self) -> ProviderId:
        """Returns the unique ProviderId enum value."""
        pass

    @property
    @abstractmethod
    def official_docs_url(self) -> str:
        """Official developer documentation URL."""
        pass

    @property
    @abstractmethod
    def pricing_docs_url(self) -> str:
        """Official pricing reference URL."""
        pass

    @property
    @abstractmethod
    def supports_zero_cost_failure(self) -> bool:
        """True if the provider guarantees $0.00 billing on 5xx/infrastructure failure."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Checks if required API keys/tokens are present in the environment."""
        pass

    @abstractmethod
    async def get_price_quote(
        self,
        model_id: str,
        duration_sec: float,
        resolution: str,
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
        Raises ProviderAPIError on submission failure (e.g. invalid auth or payload).
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
```

---

## Error Handling & Exception Hierarchy

```python
class ProviderError(Exception):
    """Base exception for all provider operations."""
    pass

class ProviderAuthenticationError(ProviderError):
    """Raised when an API key is missing, invalid, or expired (HTTP 401/403)."""
    pass

class ProviderQuotaExceededError(ProviderError):
    """Raised when account balance is insufficient (HTTP 402)."""
    pass

class ProviderPayloadValidationError(ProviderError):
    """Raised when prompt, resolution, or asset exceeds API schema constraints (HTTP 422)."""
    pass

class ProviderInfrastructureError(ProviderError):
    """Raised on upstream 5xx crashes, timeouts, or gateway drops. Triggers zero-cost cascade."""
    pass
```
