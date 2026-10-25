# Data Model: Multi-Character Dialogue & Video Motion Synthesis

**Feature**: `007-character-dialogue-motion-synthesis`  
**Date**: 2026-10-25  
**Status**: Completed  

---

## 1. Entities & Schemas

### 1.1 `CharacterProfile`
Represents an identifiable persona within the video narrative.

| Field | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `name` | `str` | Yes | Character display name (e.g., `"Cow #1 - Relaxed Bull"`, `"Mr. Corporate Cow"`). |
| `archetype` | `str` | Yes | Character archetype (`"cartoon_animal"`, `"deep_villain"`, `"kid"`, `"narrator"`). |
| `gender` | `str` | Yes | `"male"`, `"female"`, or `"neutral"`. |
| `default_voice` | `str` | Yes | Preferred neural voice persona identifier (e.g., `"en-US-GuyNeural"`). |
| `visual_summary`| `str` | No | Persistent visual style cues (e.g. `"black and white dairy cow wearing blue scarf"`). |

---

### 1.2 `SceneBeatPlan` (Updated)
Represents a directed narrative beat with explicit speaker attribution and motion kinetics.

```python
class SceneBeatPlan(BaseModel):
    beat_index: int
    name: str = "Scene"
    beat_title: Optional[str] = None
    duration_sec: float = 4.5
    conditioning_mode: ConditioningMode = ConditioningMode.HARD_CUT
    camera_movement: Optional[str] = "push_in"
    visual_prompt: str
    
    # Character & Dialogue Attribution
    speaker: Optional[str] = "Narrator"
    dialogue_text: Optional[str] = None
    voice_persona: Optional[str] = None  # e.g. "cartoon_animal", "en-US-GuyNeural"
    
    # Media Assets & Status
    keyframe_image_path: Optional[str] = None
    start_frame_path: Optional[str] = None
    end_frame_path: Optional[str] = None
    character_references: List[str] = Field(default_factory=list)
    environment_reference: Optional[str] = None
    sound_effects: List[AudioCue] = Field(default_factory=list)
    output_video_path: Optional[str] = None
```

---

### 1.3 `StoryboardCard` (Web Studio Domain Entity)
Synchronized visual card rendered in the Web Studio interface.

```python
class StoryboardCard(BaseModel):
    beat_id: str
    beat_index: int
    visual_prompt: str
    keyframe_path: Optional[str] = None
    
    # Character Attribution
    speaker: str = "Narrator"
    dialogue_text: str = ""
    voice_actor: str = "auto"
    
    # Camera & Timing
    camera_motion: str = "push_in"
    duration_seconds: float = 4.5
    duration_frames: int = 72
    render_status: str = "pending"  # "pending" | "rendering" | "completed" | "failed"
    output_video_path: Optional[str] = None
    edited_by_ai: bool = False
    is_custom_image: bool = False
```

---

### 1.4 `BeatAudioTrack`
Represents an individual character audio asset rendered per beat.

| Field | Type | Description |
| :--- | :--- | :--- |
| `beat_index` | `int` | Sequential beat index. |
| `audio_file_path` | `str` | Absolute path to rendered speech file (`outputs/temp/dialogue_beat_0_*.mp3`). |
| `duration_sec` | `float` | Exact measured duration of spoken dialogue. |
| `timeline_offset_sec` | `float` | Cumulative start timestamp in final video composition. |
| `subtitles` | `SubtitleTrack` | Word-level kinetic timestamps for this character's spoken line. |

---

## 2. Validation Rules & Invariants

1. **Explicit Attribution**: If `dialogue_text` is non-empty, `speaker` MUST NOT be `null` (defaults to `"Narrator"` or inferred character name).
2. **Audio Pacing Invariant**: For any beat $i$, $\text{duration\_sec}_i \ge \text{audio\_duration}_i + 0.5\text{s}$ to guarantee no speech truncation.
3. **Safe Video Frame Lengths**: Frame counts for Wan 2.1 video generation MUST conform to $4k + 1$ (e.g., 17, 33, 49, 65, 81 frames) at 16 fps.
4. **Anchor Integrity**: When `keyframe_image_path` exists, video synthesis MUST inject the keyframe into the diffusion initial latent or Image-to-Video conditioning node, establishing frame 0 continuity.

---

## 3. Entity Lifecycle & State Transitions

```
[Prompt Concept]
       │
       ▼ (Story Director LLM)
[DirectorMasterPlan] ──> Extracted [CharacterProfiles]
       │                 Assigns speaker & voice_persona per beat
       ▼
[StoryboardCards] in Web Studio
       │
       ├─ Creator edits Speaker / Voice Persona / Prompt
       │  (PATCH /api/storyboard/beat)
       │
       ▼ (Approve & Synthesize)
[Per-Beat Speech Synthesis] ──> [BeatAudioTracks] with word timestamps
       │
       ▼
[Serverless I2V Video Diffusion] (EmptyHunyuanLatentVideo / WanImageToVideo)
       │
       ▼
[Remotion Master Compilation] ──> Master MP4 with multi-character audio
```
