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



class StoryboardBeat(BaseModel):
    beat_index: int
    name: str
    duration_sec: float = 3.0
    visual_strategy: VisualStrategyRoute = VisualStrategyRoute.FLAT_RATE_DIFFUSION
    visual_prompt: str = ""
    dialogue_text: Optional[str] = None
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


class ModelCascadeConfig(BaseModel):
    provider: ModelProvider = ModelProvider.AUTO
    gemini_models: List[str] = Field(
        default_factory=lambda: [
            "gemini-3.5-flash",
            "gemini-3.1-flash-lite",
            "gemini-flash-latest",
            "gemini-3.8-flash",
            "gemini-pro-latest",
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


class StoryboardCard(BaseModel):
    beat_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    beat_index: int
    visual_prompt: str
    keyframe_path: Optional[str] = None
    speaker: str = "Narrator"
    dialogue_text: str = ""
    voice_actor: str = "en-US-ChristopherNeural"
    camera_motion: str = "push_in"
    duration_seconds: float = 3.0
    duration_frames: int = 49
    render_status: str = "pending"
    output_video_path: Optional[str] = None
    edited_by_ai: bool = False
    is_custom_image: bool = False
    is_chained: bool = False
    chained_from_beat: Optional[int] = None
    chain_out_of_sync: bool = False
    error_message: Optional[str] = None


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


class TelemetryState(BaseModel):
    total_workers: int = 4
    active_workers: int = 0
    elapsed_seconds: float = 0.0
    estimated_cost_usd: float = 0.0
    worker_tiles: List[TelemetryWorkerTile] = Field(default_factory=list)


class StudioSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    concept_prompt: str = ""
    aspect_ratio: str = "16:9"
    directing_mode: DirectingMode = DirectingMode.PRO
    backend_strategy: BackendExecutionStrategy = BackendExecutionStrategy.SERVERLESS
    beats: List[StoryboardCard] = Field(default_factory=list)
    chat_history: List[ChatMessage] = Field(default_factory=list)
    telemetry: Optional[TelemetryState] = None
    master_video_path: Optional[str] = None
    status: str = "draft"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


