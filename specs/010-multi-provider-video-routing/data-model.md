# Data Model & Schema Specification: Multi-Provider Video Routing

**Feature Branch**: `010-multi-provider-video-routing`
**Date**: 2026-10-25
**Status**: Completed (Phase 1)

This document formalizes the Pydantic domain models, enums, and data contracts powering Feature 010.

---

## 1. Domain Enums

### ProviderId
Identifies the execution platform or aggregation gateway.
```python
class ProviderId(str, Enum):
    FAL_AI = "fal_ai"
    APIDOT_AI = "apidot_ai"
    KIE_AI = "kie_ai"
    RUNPOD_SERVERLESS = "runpod_serverless"  # Channel 1 fallback
    AUTO = "auto"                            # Dynamic cost arbitrage
```

### VideoGenerationModality
Defines the visual input conditioning mode.
```python
class VideoGenerationModality(str, Enum):
    TEXT_TO_VIDEO = "t2v"
    IMAGE_TO_VIDEO = "i2v"
    START_END_INTERPOLATION = "interpolation"
    VIDEO_EXTEND = "extend"
```

### VideoAudioMode
Controls native clip audio vs external synthesis.
```python
class VideoAudioMode(str, Enum):
    NATIVE_CLIP_AUDIO = "native_clip_audio"
    EXTERNAL_SYNTHESIS = "external_synthesis"
    MUTED = "muted"
```

### VideoModelFamily
Foundation model lineage.
```python
class VideoModelFamily(str, Enum):
    KLING = "kling"
    SEEDANCE = "seedance"
    RUNWAY = "runway"
    MINIMAX = "minimax"
    VEO = "veo"
    WAN = "wan"
    LUMA = "luma"
    HUNYUAN = "hunyuan"
    COGVIDEOX = "cogvideox"
```

---

## 2. Core Entities & Data Structures

### VideoModelProfile
Defines version-bound metadata, prompt limits, and capabilities for a specific model.
```python
class VideoModelProfile(BaseModel):
    model_id: str                              # e.g., "kling-v1.5", "seedance-2.5"
    display_name: str                          # e.g., "Kling 1.5 Pro", "ByteDance Seedance 2.5"
    family: VideoModelFamily
    version: str                               # e.g., "1.5", "2.5", "gen3-turbo"
    hard_char_limit: int                       # Strict API gateway reject threshold
    safe_char_limit: int                       # Recommended target for optimal adherence
    token_encoder: str                         # "T5-XXL", "UMT5", "CLIP", "LLaMA-3"
    token_limit: Optional[int] = None          # Max token context window
    supports_native_audio: bool = False
    supports_i2v: bool = True
    supports_dual_frame: bool = False
    supports_extend: bool = False
    supported_providers: List[ProviderId]      # Providers hosting this model
    default_duration_sec: float = 5.0
    allowed_durations: List[float] = Field(default_factory=lambda: [5.0, 10.0])
    allowed_resolutions: List[str] = Field(default_factory=lambda: ["720p", "1080p"])
```

### ProviderDocsEntry
Official links bank and failure insurance metadata.
```python
class ProviderDocsEntry(BaseModel):
    provider_id: ProviderId
    name: str                                  # e.g. "fal.ai"
    official_docs_url: str                     # e.g. "https://fal.ai/docs"
    pricing_docs_url: str                      # e.g. "https://fal.ai/pricing"
    failure_billing_policy: str                # e.g. "Zero-cost guarantee: 5xx errors & queue time are $0.00"
    zero_cost_on_failure: bool = True
    api_status_url: Optional[str] = None
    last_verified: str                         # ISO timestamp
```

### ProviderPriceQuote
Dynamic real-time rate quotation generated during pre-flight checks.
```python
class ProviderPriceQuote(BaseModel):
    provider_id: ProviderId
    model_id: str
    modality: VideoGenerationModality
    duration_sec: float
    resolution: str
    native_audio_enabled: bool = False
    rate_per_sec_usd: float
    estimated_total_usd: float
    billing_unit: str                          # "per_second" or "flat_task"
    is_available: bool = True
    latency_ms: float = 0.0
    quote_timestamp: float                     # Unix timestamp
    ttl_sec: int = 600                         # 10 minutes cache validity
```

### VideoGenerationRequest
The normalized execution payload dispatched to any provider adapter.
```python
class VideoGenerationRequest(BaseModel):
    project_id: str
    beat_index: int
    model_profile: VideoModelProfile
    modality: VideoGenerationModality
    prompt: str
    negative_prompt: Optional[str] = "blurry, low quality, distorted, jitter"
    start_frame_path: Optional[str] = None
    end_frame_path: Optional[str] = None
    reference_assets: List[str] = Field(default_factory=list)
    duration_sec: float = 5.0
    aspect_ratio: str = "16:9"
    resolution: str = "720p"
    audio_mode: VideoAudioMode = VideoAudioMode.EXTERNAL_SYNTHESIS
    dialogue_text: Optional[str] = None
    selected_provider_id: Optional[ProviderId] = None  # None = auto cheapest
    parent_video_id: Optional[str] = None              # Used for video extending
```

### RenderingJobTicket
Tracks the lifecycle of an active or completed rendering task.
```python
class JobExecutionStatus(str, Enum):
    QUEUED = "QUEUED"
    SUBMITTED = "SUBMITTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CASCADED = "CASCADED"
    TIMED_OUT = "TIMED_OUT"

class RenderingJobTicket(BaseModel):
    ticket_id: str = Field(default_factory=lambda: f"ticket_{uuid.uuid4().hex[:10]}")
    project_id: str
    beat_index: int
    provider_id: ProviderId
    provider_task_id: str                      # External vendor task ID
    model_id: str
    status: JobExecutionStatus = JobExecutionStatus.QUEUED
    modality: VideoGenerationModality
    has_native_audio: bool = False
    quoted_price_usd: float
    actual_billed_usd: float = 0.0
    output_video_path: Optional[str] = None
    error_message: Optional[str] = None
    submitted_at: float = Field(default_factory=time.time)
    completed_at: Optional[float] = None
    retry_count: int = 0
```

---

## 3. Schema Updates to Existing Models

### Updated StoryboardCard (`core/models.py`)
```python
class StoryboardCard(BaseModel):
    # Existing fields: beat_id, beat_index, visual_prompt, duration_seconds, etc.
    # ...
    
    # Feature 010 Additions:
    model_id: str = "kling-v1.5"
    provider_override: ProviderId = ProviderId.AUTO
    modality: VideoGenerationModality = VideoGenerationModality.TEXT_TO_VIDEO
    native_audio: bool = False
    character_budget_ratio: float = 0.0        # current_chars / max_chars (0.0 to 1.0)
    last_quote: Optional[ProviderPriceQuote] = None
    active_ticket: Optional[RenderingJobTicket] = None
    has_clip_audio: bool = False               # Output MP4 has embedded audio
```

### Updated Remotion Scene Props (`remotion/src/types.ts`)
```typescript
export interface SceneConfig {
  id: string;
  startFrame: number;
  durationInFrames: number;
  type: 'video_clip' | 'static_plate' | 'countdown_timer';
  mediaSrc: string;
  hasClipAudio?: boolean;                      // If true, Remotion un-mutes <Video /> and mutes TTS
  audioVolume?: number;                        // Default 1.0
}
```
