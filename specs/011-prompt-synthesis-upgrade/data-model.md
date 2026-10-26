# Data Model: Model-Aware Prompt Synthesis & Gemini Upgrade

**Branch**: `011-prompt-synthesis-upgrade` | **Date**: 2026-10-26

## 1. Enums & Type Definitions

### AudioSyntaxType
Defines the required formatting for embedding dialogue or speech cues into video diffusion prompts:
- `NONE`: Model does not support native audio prompt markup.
- `MINIMAX_TAG`: Formatted as `<d>Dialogue text here</d>`.
- `NATURAL_LINE`: Formatted as `Spoken line: "Dialogue text here". Sound: crystal clear voice, natural room acoustics.`.

### NegativePromptStrategy
Defines how negative prompts should be synthesized for the model and genre:
- `CINEMATIC_REALISTIC`: Suppresses CGI, 3D cartoons, plastic textures, jitter, blur, and distortion. Never suppresses photography.
- `ANIMATED_STYLIZED`: Suppresses photorealism, live action footage, camera grain, and photographic noise.
- `CLEAN_GRAPHICS`: Suppresses visual noise, background clutter, and low-contrast elements for riddles and UI overlays.
- `PASSTHROUGH`: Accepts custom negative prompts without modification.

---

## 2. Updated Domain Entities

### VideoModelProfile (Expanded)
Consolidates capabilities, pricing, and routing endpoints into a Single Source of Truth:

```python
class VideoModelProfile(BaseModel):
    model_id: str
    display_name: str
    family: VideoModelFamily
    version: str
    hard_char_limit: int
    safe_char_limit: int
    token_encoder: str
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
    allowed_durations: List[float] = Field(default_factory=lambda: [5.0])
    allowed_resolutions: List[str] = Field(default_factory=lambda: ["720p"])
    provider_endpoints: Dict[ProviderId, Dict[str, str]] = Field(default_factory=dict)
    provider_rates: Dict[ProviderId, float] = Field(default_factory=dict)
```

### ModelCascadeConfig (Updated)
Reflects the modernized Gemini 3.x cascade and OpenAI tiers:

```python
class ModelCascadeConfig(BaseModel):
    provider: ModelProvider = ModelProvider.AUTO
    gemini_models: List[str] = Field(
        default_factory=lambda: [
            "gemini-3.8-flash",
            "gemini-3.5-flash",
            "gemini-3.1-flash-lite",
            "gemini-flash-latest",
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
```

### CompiledRenderPrompt
The output produced by the late-stage prompt compiler immediately prior to provider dispatch:

```python
class CompiledRenderPrompt(BaseModel):
    positive_prompt: str
    negative_prompt: str
    character_count: int
    token_budget_safe: bool
    is_kinetic_filtered: bool
    audio_markup_applied: bool
    model_id: str
    modality: VideoGenerationModality
```

---

## 3. State Transitions & Compilation Flow

```
   Storyboard Beat (Stored on Disk)
   ├── image_prompt: Pure static visual description
   └── motion_prompt: Pure 4-part kinetic motion description
                   │
                   ▼ (User clicks "Render Beat")
   Render Request: (target_model_id, modality, genre, audio_mode)
                   │
                   ▼
   ┌────────────────────────────────────────────────────────┐
   │ PromptCompiler.compile_beat(...)                       │
   │                                                        │
   │ 1. Resolve Model Profile & Token Limits                │
   │ 2. If I2V + Keyframe present:                          │
   │    ➔ Apply Kinetic Filter (strip static attire)        │
   │ 3. If Native Audio == ON and dialogue present:         │
   │    ➔ Inject model audio syntax (<d> or Spoken line:)   │
   │ 4. Build Dynamic Negative Prompt:                      │
   │    ➔ Formulate per (Genre, Art Style, Model Strategy)  │
   │ 5. Semantic Character Compression:                     │
   │    ➔ Truncate/compress to fit safe_char_limit          │
   └───────────────────────┬────────────────────────────────┘
                           │
                           ▼
                  CompiledRenderPrompt
                           │
                           ▼
             Provider Payload Serialization
             (Dispatched to fal.ai / RunPod / Kie.ai)
```
