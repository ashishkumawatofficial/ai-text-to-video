"""Core domain models and Pydantic schemas for the universal video pipeline."""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
import uuid
import time
from datetime import datetime, timezone


class Genre(str, Enum):
    RIDDLE = "riddle"
    CINEMATIC_STORY = "cinematic_story"
    ACTION = "action"


class IngestionMode(str, Enum):
    AUTONOMOUS_DIRECTOR = "autonomous_director"
    DIRECTED_STUDIO = "directed_studio"


class VisualStrategyRoute(str, Enum):
    PROGRAMMATIC_HYBRID = "PROGRAMMATIC_HYBRID"
    START_END_INTERPOLATION = "START_END_INTERPOLATION"
    FLAT_RATE_DIFFUSION = "FLAT_RATE_DIFFUSION"


class ImageRole(str, Enum):
    STYLE_REFERENCE = "STYLE_REFERENCE"
    CHARACTER_IMAGE = "CHARACTER_IMAGE"
    STORYBOARD_IMAGE = "STORYBOARD_IMAGE"
    SCENE_IMAGE = "SCENE_IMAGE"
    START_FRAME = "START_FRAME"
    END_FRAME = "END_FRAME"


class ImageAsset(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    file_path: str
    role: ImageRole
    width: Optional[int] = 1080
    height: Optional[int] = 1920
    source: str = "user_supplied"


class ContinuityLink(BaseModel):
    chain_from_previous: bool = False
    previous_beat_id: Optional[str] = None
    extracted_tail_frame_path: Optional[str] = None
    motion_continuation_prompt: Optional[str] = None


class AudioCue(BaseModel):
    sfx_name: str
    offset_sec: float = 0.0
    start_offset_sec: Optional[float] = None
    duration_sec: Optional[float] = None
    start_frame: Optional[int] = None
    volume: float = 1.0

    def model_post_init(self, __context: Any) -> None:
        if self.start_offset_sec is not None and self.offset_sec == 0.0:
            self.offset_sec = self.start_offset_sec



class SubtitleWordToken(BaseModel):
    word: str
    start_ms: int
    end_ms: int
    confidence: float = 1.0


class SubtitleTrack(BaseModel):
    style_preset: str = "bold_yellow_glow"
    words: List[SubtitleWordToken] = Field(default_factory=list)


class CharacterProfile(BaseModel):
    name: str
    character_id: Optional[str] = None
    reference_images: List[str] = Field(default_factory=list)
    identity_prompt: Optional[str] = None
    ip_adapter_weight: float = 0.75
    archetype: Optional[str] = "cartoon_animal"
    gender: Optional[str] = "neutral"
    default_voice: Optional[str] = "en-US-ChristopherNeural"
    voice_actor: Optional[str] = "auto"
    voice_persona: Optional[str] = "auto"
    visual_anchor: Optional[str] = None
    visual_summary: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if not self.character_id:
            self.character_id = self.name.lower().replace(" ", "_")



class VideoAudioMode(str, Enum):
    NATIVE_CLIP_AUDIO = "native_clip_audio"
    EXTERNAL_SYNTHESIS = "external_synthesis"
    MUTED = "muted"


class StoryboardBeat(BaseModel):
    beat_index: int
    name: str
    duration_sec: float = 3.0
    visual_strategy: VisualStrategyRoute = VisualStrategyRoute.FLAT_RATE_DIFFUSION
    visual_prompt: str = ""
    image_prompt: Optional[str] = None
    motion_prompt: Optional[str] = None
    dialogue_text: Optional[str] = None
    audio_mode: VideoAudioMode = VideoAudioMode.EXTERNAL_SYNTHESIS
    has_native_audio: bool = False
    image_assets: List[ImageAsset] = Field(default_factory=list)
    continuity: ContinuityLink = Field(default_factory=ContinuityLink)
    sound_effects: List[AudioCue] = Field(default_factory=list)
    output_video_path: Optional[str] = None


class AudioAsset(BaseModel):
    voiceover_path: Optional[str] = None
    music_path: Optional[str] = None
    music_base_volume: float = 0.35
    music_ducked_volume: float = 0.10
    sfx_cues: List[AudioCue] = Field(default_factory=list)


class VideoProject(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    genre: Genre
    ingestion_mode: IngestionMode = IngestionMode.AUTONOMOUS_DIRECTOR
    aspect_ratio: str = "9:16"
    fps: int = 30
    width: int = 1080
    height: int = 1920
    target_duration_sec: Optional[float] = None
    character_profiles: List[CharacterProfile] = Field(default_factory=list)
    scenes: List[StoryboardBeat] = Field(default_factory=list)
    audio: AudioAsset = Field(default_factory=AudioAsset)
    subtitles: SubtitleTrack = Field(default_factory=SubtitleTrack)
    status: str = "draft"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RenderOutput(BaseModel):
    file_path: str
    resolution: str = "1080x1920"
    fps: int = 30
    duration_sec: float
    file_size_bytes: int = 0
    render_duration_sec: float = 0.0


# --- Feature 002: Wan 3.0, RunPod Diagnostics, and Local Keyframing ---

DEFAULT_RUNPOD_COMFY_URL = "http://127.0.0.1:8188"


class Wan3WorkflowConfig(BaseModel):
    model_checkpoint: str = Field(default="wan2.1_t2v_14B_fp8_scaled.safetensors")
    prompt: str = Field(description="Visual motion prompt describing scene dynamics")
    negative_prompt: str = Field(default="blurry, low quality, distorted anatomy, jitter, artifacts")
    width: int = Field(default=832, ge=256, le=1920)
    height: int = Field(default=480, ge=256, le=1920)
    duration_frames: int = Field(default=33, ge=16, le=900)
    steps: int = Field(default=15, ge=5, le=50)
    cfg: float = Field(default=6.5, ge=1.0, le=15.0)
    seed: int = Field(default=42)
    reference_images: List[str] = Field(default_factory=list, max_length=10)
    motion_bucket_id: Optional[int] = Field(default=127, ge=1, le=255)


class RunPodHealthReport(BaseModel):
    url: str
    is_reachable: bool
    latency_ms: float
    gpu_name: Optional[str] = None
    vram_total_gb: Optional[float] = None
    vram_free_gb: Optional[float] = None
    comfyui_version: Optional[str] = None
    available_checkpoints: List[str] = Field(default_factory=list)
    has_wan3: bool = False
    has_wan2: bool = False
    has_ipadapter: bool = False
    status_summary: str


class LocalKeyframeAsset(BaseModel):
    scene_id: str
    prompt: str
    cache_path: str
    width: int = 1080
    height: int = 1920
    is_cached: bool = False
    source_generator: str = Field(default="local_mock")


# --- Feature 003: Interactive Storyboard, Delta Modification & Autonomous Conditioning ---

class ConditioningMode(str, Enum):
    PURE_T2V = "pure_t2v"
    START_FRAME_ONLY = "start_frame_only"
    START_AND_END_FRAME = "start_and_end_frame"
    CHAIN_FROM_PREVIOUS = "chain_from_previous"
    HARD_CUT = "hard_cut"


class ApprovalStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    MODIFICATIONS_REQUESTED = "modifications_requested"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReferenceAsset(BaseModel):
    tag: str
    file_path: str
    role: str = Field(default="character", description="character, environment, start_frame, end_frame")
    description: Optional[str] = None


class CameraMotion(str, Enum):
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    TILT_UP = "tilt_up"
    TILT_DOWN = "tilt_down"
    SLOW_PUSH_IN = "slow_push_in"
    STATIC = "static"


class SceneBeatPlan(BaseModel):
    beat_index: int = 1
    scene_id: Optional[str] = None
    name: str = "Scene Beat"
    beat_title: Optional[str] = None
    duration_sec: float = Field(default=4.5, ge=0.5, le=60.0)
    conditioning_mode: ConditioningMode = ConditioningMode.START_FRAME_ONLY
    camera_movement: str = "slow_push_in"
    visual_prompt: str
    image_prompt: Optional[str] = None
    motion_prompt: Optional[str] = None
    speaker: Optional[str] = "Narrator"
    voice_persona: Optional[str] = None
    keyframe_image_path: Optional[str] = None
    start_frame_path: Optional[str] = None
    end_frame_path: Optional[str] = None
    character_references: List[str] = Field(default_factory=list)
    environment_reference: Optional[str] = None
    dialogue_text: Optional[str] = None
    sound_effects: List[AudioCue] = Field(default_factory=list)
    output_video_path: Optional[str] = None
    is_chained: bool = False
    chained_from_beat: Optional[int] = None

    def model_post_init(self, __context: Any) -> None:
        if self.beat_title and (self.name == "Scene Beat" or not self.name):
            self.name = self.beat_title
        if not self.scene_id:
            self.scene_id = f"scene_{self.beat_index}"
        if not self.image_prompt:
            self.image_prompt = self.visual_prompt
        if not self.motion_prompt:
            cam = getattr(self, "camera_movement", "slow_push_in") or "slow_push_in"
            cam_str = str(cam).replace("_", " ").title()
            self.motion_prompt = f"{cam_str} camera movement, dynamic subject motion and environmental physics: {self.visual_prompt}"


SceneBeat = SceneBeatPlan  # Backward compatible alias


class VideoAspectRatio(str, Enum):
    VERTICAL_9_16 = "9:16"    # 1080x1920 (TikTok, Reels, Shorts) - Default
    WIDESCREEN_16_9 = "16:9"  # 1920x1080 (YouTube, Standard Displays)
    SQUARE_1_1 = "1:1"        # 1080x1080 (Instagram Square)
    PORTRAIT_4_5 = "4:5"      # 1080x1350 (Instagram Portrait Feed)


ASPECT_RATIO_RESOLUTIONS: Dict[str, tuple[int, int]] = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
}


class DirectorMasterPlan(BaseModel):
    title: str = "Cinematic Story"
    story_title: Optional[str] = None
    genre: Genre = Genre.CINEMATIC_STORY
    aspect_ratio: str = "9:16"
    target_aspect_ratio: str = "9:16"
    width: int = 1080
    height: int = 1920
    target_audience: Optional[str] = None
    total_duration_sec: float = 0.0
    voiceover_enabled: bool = True
    voice_persona: str = "en-US-ChristopherNeural"
    voice_speed: float = 1.0
    music_genre_and_mood: str = "ambient_cinematic_score"
    background_music: Optional[Union[Dict[str, Any], str]] = None
    music_base_volume: float = 0.35
    music_ducked_volume: float = 0.10
    subtitles_enabled: bool = True
    subtitle_preset: str = "bold_yellow_glow"
    scenes: List[SceneBeatPlan] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        if self.story_title and self.title == "Cinematic Story":
            self.title = self.story_title
        elif self.title and not self.story_title:
            self.story_title = self.title

        if self.aspect_ratio and self.target_aspect_ratio == "9:16":
            self.target_aspect_ratio = self.aspect_ratio
        elif self.target_aspect_ratio and self.aspect_ratio == "9:16":
            self.aspect_ratio = self.target_aspect_ratio

        if self.aspect_ratio in ASPECT_RATIO_RESOLUTIONS:
            resolved_w, resolved_h = ASPECT_RATIO_RESOLUTIONS[self.aspect_ratio]
            if self.width == 1080 and self.height == 1920:
                self.width = resolved_w
                self.height = resolved_h

        if self.scenes and self.total_duration_sec == 0.0:
            self.total_duration_sec = sum(s.duration_sec for s in self.scenes)


# --- Feature 004: Dynamic AI Story Writer, Model Cascade & Script Adaptation ---

class NarrativeInputMode(str, Enum):
    CONCEPT_EXPANSION = "concept_expansion"  # Short prompt -> Multi-beat story
    SCRIPT_ADAPTATION = "script_adaptation"  # Full text -> Segmented scene beats


class ModelProvider(str, Enum):
    GEMINI = "gemini"
    OPENAI = "openai"
    AUTO = "auto"
    OFFLINE = "offline"


class NarrativeBrief(BaseModel):
    prompt_or_text: str = Field(min_length=1, description="Raw prompt or complete story text")
    input_mode: NarrativeInputMode = NarrativeInputMode.CONCEPT_EXPANSION
    aspect_ratio: VideoAspectRatio = VideoAspectRatio.VERTICAL_9_16
    width: int = Field(default=1080, description="Target canvas width")
    height: int = Field(default=1920, description="Target canvas height")
    genre_hint: Optional[Genre] = None
    target_duration_sec: Optional[float] = Field(default=None, ge=5.0, le=90.0)
    voice_persona: Optional[str] = "en-US-ChristopherNeural"
    reference_assets: Dict[str, ReferenceAsset] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        ratio_str = self.aspect_ratio.value if isinstance(self.aspect_ratio, VideoAspectRatio) else str(self.aspect_ratio)
        if ratio_str in ASPECT_RATIO_RESOLUTIONS and self.width == 1080 and self.height == 1920:
            self.width, self.height = ASPECT_RATIO_RESOLUTIONS[ratio_str]


LLM_MODEL_ALIASES: Dict[str, str] = {
    "gemini-2.5-flash": "gemini-3.8-flash",
    "gemini-2.5-pro": "gemini-3.8-flash",
    "gemini-2.0-flash": "gemini-3.8-flash",
    "gemini-2.0-pro": "gemini-3.8-flash",
    "gemini-1.5-flash": "gemini-3.1-flash-lite",
    "gemini-1.5-pro": "gemini-pro-latest",
}


def resolve_llm_model(model_name: Optional[str]) -> str:
    """Resolves model aliases to their modern supported counterparts."""
    if not model_name:
        return "gemini-3.8-flash"
    clean = model_name.strip()
    return LLM_MODEL_ALIASES.get(clean.lower(), clean)


class ModelCascadeConfig(BaseModel):
    provider: ModelProvider = ModelProvider.AUTO
    gemini_models: List[str] = Field(
        default_factory=lambda: [
            "gemini-3.8-flash",
            "gemini-3.5-flash",
        ]
    )
    openai_models: List[str] = Field(
        default_factory=lambda: [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
        ]
    )
    timeout_sec: float = 10.0
    enable_offline_fallback: bool = True


class StoryWriterResult(BaseModel):
    plan: DirectorMasterPlan
    model_used: str
    tier_level: int = Field(ge=1, le=4, description="1: Frontier, 2: Stable, 3: Legacy, 4: Offline")
    latency_ms: float = Field(ge=0.0)
    fallback_occurred: bool = False
    error_trace: List[str] = Field(default_factory=list)



class SessionTurn(BaseModel):
    turn_index: int
    user_message: str
    modified_beats: List[int] = Field(default_factory=list)
    summary_of_changes: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class StoryboardSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    initial_prompt: str
    approval_status: ApprovalStatus = ApprovalStatus.PENDING_REVIEW
    reference_assets: Dict[str, ReferenceAsset] = Field(default_factory=dict)
    plan: DirectorMasterPlan
    history: List[SessionTurn] = Field(default_factory=list)


# --- Feature 005: RunPod Serverless Parallel Video Pipeline ---

class BackendExecutionStrategy(str, Enum):
    AUTO = "auto"              # Try Serverless -> Dedicated Pod -> Local Mock
    SERVERLESS = "serverless"  # RunPod Serverless (Parallel on-demand workers)
    POD = "pod"                # RunPod Dedicated ComfyUI Pod (Direct HTTP 8188)
    LOCAL = "local"            # Local High-Definition Keyframe Plate (Zero GPU)


class ServerlessJobStatus(str, Enum):
    IN_QUEUE = "IN_QUEUE"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"


class ServerlessConfig(BaseModel):
    endpoint_id: str = Field(description="RunPod serverless endpoint ID (e.g., 'v2-xxxxxx')")
    api_key: str = Field(description="RunPod User API Key")
    timeout_sec: int = Field(default=600, ge=30, le=1800, description="Max polling timeout in seconds per worker")
    poll_interval_sec: float = Field(default=2.5, ge=1.0, le=10.0, description="Delay between status polls")
    max_concurrency: int = Field(default=4, ge=1, le=16, description="Max concurrent serverless worker requests")
    gpu_tier_rate_per_sec: float = Field(default=0.00021, description="USD rate per GPU second (default RTX 4090)")


class ServerlessJob(BaseModel):
    job_id: str = Field(description="RunPod serverless task ID")
    beat_index: int = Field(description="0-indexed scene beat order in director plan")
    beat_name: str = Field(description="Descriptive beat title")
    status: ServerlessJobStatus = Field(default=ServerlessJobStatus.IN_QUEUE)
    execution_time_ms: float = Field(default=0.0, description="Reported GPU compute time in milliseconds")
    output_video_path: Optional[str] = Field(default=None, description="Local downloaded MP4 file path")
    error_message: Optional[str] = Field(default=None, description="Error detail if status == FAILED")
    submitted_at: float = Field(default_factory=time.time, description="Unix timestamp when job was queued")
    completed_at: Optional[float] = Field(default=None, description="Unix timestamp when job completed")


class ServerlessCostReport(BaseModel):
    total_beats: int
    successful_beats: int
    wall_clock_duration_sec: float = Field(description="Real-world elapsed time from dispatch to final download")
    cumulative_gpu_seconds: float = Field(description="Sum of all individual worker execution times")
    estimated_cost_usd: float = Field(description="Calculated dollar cost based on active compute seconds")
    effective_concurrency: float = Field(default=1.0, description="cumulative_gpu_seconds / wall_clock_duration_sec")


# --- Feature 006: Web Studio Interface & AI Director Copilot ---

class DirectingMode(str, Enum):
    AUTO = "auto"
    PRO = "pro"


class RenderTake(BaseModel):
    take_id: str = Field(default_factory=lambda: f"take_{uuid.uuid4().hex[:8]}")
    beat_index: int
    take_index: int = 1
    video_path: str
    prompt: str = ""
    camera_motion: str = "push_in"
    backend: str = "serverless"
    duration_sec: float = 3.0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class StoryboardCard(BaseModel):
    beat_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    beat_index: int
    visual_prompt: str
    image_prompt: Optional[str] = None
    motion_prompt: Optional[str] = None
    keyframe_path: Optional[str] = None
    speaker: Optional[str] = "Narrator"
    dialogue_text: str = ""
    voice_actor: str = "en-US-ChristopherNeural"
    camera_motion: str = "push_in"
    duration_seconds: float = 3.0
    duration_frames: int = 49
    render_status: str = "pending"
    output_video_path: Optional[str] = None
    video_path: Optional[str] = None
    active_take_id: Optional[str] = None
    takes: List[RenderTake] = Field(default_factory=list)
    edited_by_ai: bool = False
    is_custom_image: bool = False
    is_chained: bool = False
    chained_from_beat: Optional[int] = None
    chain_out_of_sync: bool = False
    error_message: Optional[str] = None
    model_id: str = "kling-v1.5"
    provider_override: str = "auto"
    allow_provider_cascade: bool = True
    modality: str = "t2v"
    resolution: str = "720p"
    native_audio: bool = False
    has_clip_audio: bool = False
    character_budget_ratio: float = 0.0
    last_quoted_price_usd: Optional[float] = None
    last_provider_used: Optional[str] = None
    start_frame_path: Optional[str] = None
    end_frame_path: Optional[str] = None
    reference_image_paths: List[str] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        if not self.image_prompt:
            self.image_prompt = self.visual_prompt
        if not self.motion_prompt:
            cam = getattr(self, "camera_motion", "slow_push_in") or "slow_push_in"
            cam_str = str(cam).replace("_", " ").title()
            self.motion_prompt = f"{cam_str} camera movement, dynamic subject motion and environmental physics: {self.visual_prompt}"
        if self.keyframe_path and not self.start_frame_path:
            self.start_frame_path = self.keyframe_path
        elif self.start_frame_path and not self.keyframe_path:
            self.keyframe_path = self.start_frame_path
        if self.output_video_path and not self.video_path:
            self.video_path = self.output_video_path
        elif self.video_path and not self.output_video_path:
            self.output_video_path = self.video_path


class ChatMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender: str  # "user" | "director_ai"
    text: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    applied_delta: Optional[Dict[str, Any]] = None


class TelemetryWorkerTile(BaseModel):
    worker_id: str
    beat_index: int
    status: str
    elapsed_seconds: float = 0.0
    progress_percent: int = 0
    provider_id: Optional[str] = "fal.ai"
    model_id: Optional[str] = "kling-v2.5"
    api_status: Optional[str] = "IN_PROGRESS"
    status_detail: Optional[str] = "Awaiting inference slot"
    quoted_price_usd: float = 0.0


class TelemetryState(BaseModel):
    total_workers: int = 4
    active_workers: int = 0
    elapsed_seconds: float = 0.0
    estimated_cost_usd: float = 0.0
    active_provider: Optional[str] = "fal.ai"
    active_api_status: Optional[str] = "Ready"
    worker_tiles: List[TelemetryWorkerTile] = Field(default_factory=list)


class StudioSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    concept_prompt: str = ""
    aspect_ratio: str = "16:9"
    directing_mode: DirectingMode = DirectingMode.PRO
    backend_strategy: BackendExecutionStrategy = BackendExecutionStrategy.SERVERLESS
    beats: List[StoryboardCard] = Field(default_factory=list)
    chat_history: List[ChatMessage] = Field(default_factory=list)
    telemetry: Optional[TelemetryState] = None
    master_video_path: Optional[str] = None
    project_location: Optional[str] = None
    status: str = "draft"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProjectSummary(BaseModel):
    project_id: str
    title: str
    concept_prompt: str = ""
    aspect_ratio: str = "16:9"
    directing_mode: str = "pro"
    status: str = "draft"
    total_duration_sec: float = 0.0
    beat_count: int = 0
    completed_beats_count: int = 0
    total_takes_count: int = 0
    thumbnail_url: Optional[str] = None
    master_video_path: Optional[str] = None
    project_location: Optional[str] = None
    created_at: str
    updated_at: str
    is_legacy: bool = False


# --- Feature 010: Multi-Provider Video Routing & Real-Time Cost Arbitrage ---

class ProviderId(str, Enum):
    FAL_AI = "fal_ai"
    APIDOT_AI = "apidot_ai"
    KIE_AI = "kie_ai"
    RUNPOD_SERVERLESS = "runpod_serverless"
    AUTO = "auto"


class VideoGenerationModality(str, Enum):
    TEXT_TO_VIDEO = "t2v"
    IMAGE_TO_VIDEO = "i2v"
    START_END_INTERPOLATION = "interpolation"
    VIDEO_EXTEND = "extend"


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
    PIXVERSE = "pixverse"
    PIKA = "pika"
    VIDU = "vidu"
    MOCHI = "mochi"
    SORA = "sora"
    GROK = "grok"
    FLUX = "flux"


class AudioSyntaxType(str, Enum):
    NONE = "none"
    MINIMAX_TAG = "minimax_tag"
    NATURAL_LINE = "natural_line"


class NegativePromptStrategy(str, Enum):
    CINEMATIC_REALISTIC = "cinematic_realistic"
    ANIMATED_STYLIZED = "animated_stylized"
    CLEAN_GRAPHICS = "clean_graphics"
    PASSTHROUGH = "passthrough"


class VideoModelProfile(BaseModel):
    model_id: str
    display_name: str
    family: VideoModelFamily
    version: str
    hard_char_limit: int
    safe_char_limit: int
    token_encoder: str = "T5-XXL"
    token_limit: Optional[int] = None
    supports_native_audio: bool = False
    audio_syntax: AudioSyntaxType = AudioSyntaxType.NONE
    supports_i2v: bool = True
    supports_dual_frame: bool = False
    supports_reference_images: bool = False
    max_reference_images: int = 0
    supports_extend: bool = False
    negative_prompt_strategy: NegativePromptStrategy = NegativePromptStrategy.CINEMATIC_REALISTIC
    first_frame_param_name: str = "image_url"
    end_frame_param_name: str = "tail_image_url"
    reference_param_name: str = "reference_images"
    supported_providers: List[ProviderId] = Field(default_factory=list)
    default_duration_sec: float = 5.0
    allowed_durations: List[float] = Field(default_factory=lambda: [5.0, 10.0])
    allowed_resolutions: List[str] = Field(default_factory=lambda: ["720p", "1080p"])
    provider_endpoints: Dict[ProviderId, Dict[str, str]] = Field(default_factory=dict)
    provider_rates: Dict[ProviderId, float] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        if self.supports_native_audio and self.audio_syntax == AudioSyntaxType.NONE:
            if self.family == VideoModelFamily.MINIMAX:
                self.audio_syntax = AudioSyntaxType.MINIMAX_TAG
            else:
                self.audio_syntax = AudioSyntaxType.NATURAL_LINE


class CompiledRenderPrompt(BaseModel):
    positive_prompt: str
    negative_prompt: str
    character_count: int
    token_budget_safe: bool = True
    is_kinetic_filtered: bool = False
    audio_markup_applied: bool = False
    model_id: str
    modality: VideoGenerationModality = VideoGenerationModality.TEXT_TO_VIDEO


class ProviderDocsEntry(BaseModel):
    provider_id: ProviderId
    name: str
    official_docs_url: str
    pricing_docs_url: str
    failure_billing_policy: str
    zero_cost_on_failure: bool = True
    api_status_url: Optional[str] = None
    last_verified: str = "2026-10-25"


class ProviderPriceQuote(BaseModel):
    provider_id: ProviderId
    model_id: str
    modality: VideoGenerationModality = VideoGenerationModality.TEXT_TO_VIDEO
    duration_sec: float
    resolution: str = "720p"
    native_audio_enabled: bool = False
    rate_per_sec_usd: float
    estimated_total_usd: float
    billing_unit: str = "per_second"
    is_available: bool = True
    latency_ms: float = 0.0
    quote_timestamp: float = Field(default_factory=time.time)
    ttl_sec: int = 600
    is_cheapest: bool = False
    discount_pct: float = 0.0
    is_promotional: bool = False
    promo_description: Optional[str] = None
    free_tier_applicable: bool = False


class VideoGenerationRequest(BaseModel):
    project_id: str
    beat_index: int
    model_profile: VideoModelProfile
    modality: VideoGenerationModality = VideoGenerationModality.TEXT_TO_VIDEO
    prompt: str
    negative_prompt: Optional[str] = "blurry, low quality, distorted, jitter"
    start_frame_path: Optional[str] = None
    end_frame_path: Optional[str] = None
    reference_image_paths: List[str] = Field(default_factory=list)
    reference_assets: List[str] = Field(default_factory=list)
    duration_sec: float = 5.0
    aspect_ratio: str = "16:9"
    resolution: str = "720p"
    audio_mode: VideoAudioMode = VideoAudioMode.EXTERNAL_SYNTHESIS
    dialogue_text: Optional[str] = None
    selected_provider_id: Optional[ProviderId] = None
    allow_provider_cascade: bool = True
    parent_video_id: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if self.reference_image_paths and not self.reference_assets:
            self.reference_assets = list(self.reference_image_paths)
        elif self.reference_assets and not self.reference_image_paths:
            self.reference_image_paths = list(self.reference_assets)


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
    provider_task_id: str
    model_id: str
    status: JobExecutionStatus = JobExecutionStatus.QUEUED
    modality: VideoGenerationModality = VideoGenerationModality.TEXT_TO_VIDEO
    has_native_audio: bool = False
    quoted_price_usd: float = 0.0
    actual_billed_usd: float = 0.0
    output_video_path: Optional[str] = None
    error_message: Optional[str] = None
    submitted_at: float = Field(default_factory=time.time)
    completed_at: Optional[float] = None
    retry_count: int = 0


