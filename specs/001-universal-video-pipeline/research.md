# Phase 0 Research: Universal Multi-Genre Video Generation Pipeline

**Feature Branch**: `001-universal-video-pipeline`  
**Date**: 2026-10-23  
**Status**: Completed  

---

## 1. Executive Technical Decisions

### Decision 1: Hybrid Architecture (Python Orchestrator + Remotion Master Compositor)
- **Decision**: Use a Python 3.11+ core orchestrator (`core/`) for AI pipeline dispatch (storyboarding, audio synthesis, whisper alignment, GPU API calls) coupled with a Remotion (React + TypeScript) rendering engine (`remotion/`) for final master video composition, kinetic typography, countdown dials, and audio ducking.
- **Rationale**:
  - Python has the most mature ecosystem for LLM orchestration, Whisper audio alignment, ComfyUI WebSocket/REST clients, and Pillow/OpenCV image manipulation.
  - Remotion provides 100% deterministic, frame-accurate React-based video rendering, eliminating rendering glitches, supporting CSS animations, SVG radial progress dials, and word-by-word kinetic subtitles with sub-frame accuracy.
- **Alternatives Considered**:
  - *Pure Python (MoviePy / OpenCV / FFmpeg direct)*: MoviePy has known audio-sync drift, sluggish text rendering, memory leaks on long clips, and no reactive layout system for dynamic subtitles.
  - *Pure Node.js / TypeScript*: Lack of native client libraries for high-performance audio processing (Whisper, PyTorch tensors) and cumbersome ComfyUI workflow scripting.

---

### Decision 2: GPU Video Diffusion Inference via RunPod + ComfyUI API
- **Decision**: Use dedicated RunPod cloud GPUs (NVIDIA RTX 4090 @ ~$0.44/hour or A100 @ ~$1.19/hour) running ComfyUI with REST/WebSocket API integration for all heavy video and image diffusion workloads.
- **Rationale**:
  - Running open-source video models (Wan2.1, CogVideoX, HunyuanVideo) locally on consumer Mac hardware is either impossible or takes >15 minutes per 3-second clip due to VRAM limits.
  - Commercial closed APIs (Luma Dream Machine, Runway Gen-3, Kling) charge $0.20 to $0.50 per 5-second generation with no free rerolls, creating severe "reroll anxiety".
  - ComfyUI exposed via RunPod allows unmetered, programmatic batch generations with modular nodes: IP-Adapter (character consistency), ControlNet (pose/layout), and Image-to-Video (I2V).
- **Alternatives Considered**:
  - *Replicate / Fal.ai Serverless*: Convenient pay-per-call APIs, but costs escalate rapidly during testing and iterative rerolls ($0.15–$0.40 per 5s clip).
  - *Local Mac GPU (MPS / MLX)*: Inadequate for 14B video models requiring 18GB+ of VRAM at fast inference speeds.

---

### Decision 3: Audio Synthesis & Word-Level Timestamp Alignment
- **Decision**: Pair high-clarity Neural TTS (`edge-tts` for high-speed multi-lingual narration or ElevenLabs API for cinematic character voices) with OpenAI Whisper (`faster-whisper` / `whisper-timestamped`) to generate word-level timestamp tokens `{word, start_ms, end_ms}`.
- **Rationale**:
  - Edge-TTS is free, near-instantaneous, and produces broadcast-quality speech across dozens of vocal styles.
  - Faster-Whisper provides millisecond-precise token start and end timestamps, enabling Remotion's subtitle engine to highlight words dynamically as they are spoken (active word scaling, glow, or color shift).
- **Alternatives Considered**:
  - *Syllable estimation via char-count*: Extremely prone to drift on varying syllable complexities, leading to jarring desynchronization.
  - *Pre-rendered subtitles via FFmpeg drawtext*: Static, visually dated, lacks smooth bouncy scale animations, and cannot adjust layout dynamically.

---

### Decision 4: Tri-Strategy Anti-Reroll Visual Routing Engine
- **Decision**: Categorize each scene beat into one of three execution strategies:
  1. **`PROGRAMMATIC_HYBRID` (Remotion + Clean Sprites)**: 100% deterministic, $0.00 compute. Background plates remain stationary; moving parts (e.g. water stream, hand holding glass) are rendered as alpha-channel sprites animated via React springs.
  2. **`START_END_INTERPOLATION` (Dual-Frame Guided Diffusion)**: 85%–90% first-pass success. Frame 0 (initial state) and Frame N (target state) are strictly anchored, and diffusion models interpolate the motion trajectory between them.
  3. **`FLAT_RATE_DIFFUSION` (RunPod RTX 4090 ComfyUI)**: Unmetered creative rendering for character acting, dialogue, and high-energy action. Rerolls cost $0.00 incremental compute.
- **Rationale**: Eliminates the "Slot Machine Problem" where creators spend dollars rerolling simple logical puzzle steps while unleashing full creative freedom on narrative shots.

---

### Decision 5: Tail-to-Head Frame Chaining (Clip K End ➔ Clip K+1 Start)
- **Decision**: Automatically extract the terminal frame ($t = \text{end}$) from completed Clip $K$, save it losslessly as an image asset, and pass it as the initial latent anchor (`Frame 0`) into the I2V workflow for Clip $K+1$.
- **Rationale**: Guarantees sub-pixel physical continuity across consecutive multi-shot cuts. Eliminates object popping, arm jumping, lighting shifts, and character teleportation.
- **Alternatives Considered**:
  - *Independent T2V generation for each clip*: Results in severe character and environment discontinuity between shots.
  - *Cross-fade / dissolve transitions*: Looks dated and fails to provide true physical motion continuity.

---

### Decision 6: The 6-Role Image Ingestion Taxonomy
- **Decision**: Classify all user-provided or AI-generated images into 6 typed operational roles:
  1. `STYLE_REFERENCE` ➔ Conditioned via IP-Adapter Style.
  2. `CHARACTER_IMAGE` ➔ Conditioned via InstantID / FaceID / Character LoRA.
  3. `STORYBOARD_IMAGE` ➔ Conditioned via ControlNet (Depth/Canny/OpenPose).
  4. `SCENE_IMAGE` ➔ Stationary environmental background plate.
  5. `START_FRAME` ➔ Frame 0 anchor for Image-to-Video.
  6. `END_FRAME` ➔ Frame N target for dual-frame interpolation.
- **Rationale**: Gives creators granular control over which visual aspect of an image dictates the scene without ambiguous prompt collisions.

---

## 2. Directory Layout Decision

```text
ai-text-to-video/
├── core/                        # Python Orchestration Core
│   ├── __init__.py
│   ├── director.py              # LLM storyboard generator & intent classifier
│   ├── audio_engine.py          # TTS synthesis & Whisper word timestamping
│   ├── sfx_mixer.py             # Sound effect library & audio ducking
│   ├── visual_router.py         # Tri-Strategy Anti-Reroll dispatcher
│   ├── chain_manager.py         # Tail-to-Head frame extraction & conditioning
│   ├── runpod_client.py         # ComfyUI WebSocket/REST client for RunPod GPU
│   └── models.py                # Pydantic v2 schemas for all entities
├── remotion/                    # Master React Video Compositor
│   ├── src/
│   │   ├── Root.tsx             # Main Remotion composition entry
│   │   ├── index.ts             # Remotion registration
│   │   ├── components/          # Reusable motion components
│   │   │   ├── KineticSubtitles.tsx
│   │   │   ├── CountdownDial.tsx
│   │   │   ├── SpriteLayer.tsx
│   │   │   └── AudioMixer.tsx
│   │   └── templates/           # Genre visual templates
│   │       ├── RiddleTemplate.tsx
│   │       ├── StoryTemplate.tsx
│   │       └── ActionTemplate.tsx
│   ├── package.json
│   ├── tsconfig.json
│   └── remotion.config.ts
├── assets/                      # Static assets, sound library, sprites
│   ├── audio/sfx/
│   ├── audio/music/
│   └── templates/
├── outputs/                     # Generated videos, intermediate clips, manifests
└── specs/                       # Feature specifications and documentation
```

---

## 3. Technology Verification Matrix

| Subsystem | Selected Tool / Library | Version | Verification / Proof |
| :--- | :--- | :--- | :--- |
| **Orchestration** | Python + Pydantic | Python 3.11+, Pydantic 2.7+ | Strict type validation and JSON serialization |
| **Story & Intent** | LLM API (Gemini / Claude / GPT) | Structured JSON mode | Guarantees valid Pydantic storyboard schemas |
| **TTS Engine** | `edge-tts` + `faster-whisper` | edge-tts 6.1+, faster-whisper 1.0+ | Broadcast audio + word-level timestamps in <2 seconds |
| **GPU Inference** | ComfyUI on RunPod RTX 4090 | ComfyUI v0.2+ | Native I2V workflows with Wan2.1 / CogVideoX |
| **Compositing** | Remotion | Remotion 4.0+ (React 19 / TypeScript) | Frame-accurate web-to-video rendering |
| **Video Encoding** | FFmpeg via Remotion Bundler | FFmpeg 6.0+ | Native H.264 / AAC 1080x1920 MP4 export |
