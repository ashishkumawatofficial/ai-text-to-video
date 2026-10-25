# Implementation Plan: Universal Multi-Genre Video Generation Pipeline

**Branch**: `001-universal-video-pipeline` | **Date**: 2026-10-23 | **Spec**: [spec.md](file:///Users/ashishkumavat/Projects/ai-text-to-video/specs/001-universal-video-pipeline/spec.md)

**Input**: Feature specification from `specs/001-universal-video-pipeline/spec.md`

---

## Summary

Build a high-performance, studio-grade video production pipeline capable of generating vertical short-form content across three core genres: **Interactive Riddles**, **Cinematic Stories/Cartoons**, and **Action Sequences**. The system avoids the "Reroll Tax" via a **Tri-Strategy Anti-Reroll Visual Routing Engine** (Programmatic Hybrid, Start-to-End Interpolation, and Unmetered Flat-Rate GPU Diffusion on RunPod ComfyUI). It supports dual ingestion (Autonomous Director Mode & Directed Studio Mode with custom reference images), automated Tail-to-Head Frame Chaining for seamless continuity, and a Remotion master compositor for kinetic subtitles and audio ducking.

---

## Technical Context

**Language/Version**: Python 3.11+ (Orchestration & Director) + TypeScript 5.4+ / Node.js 20+ (Remotion Master Compositor)  
**Primary Dependencies**:
- Python: `pydantic` (v2.7+), `edge-tts` (v6.1+), `faster-whisper` (v1.0+), `pillow`, `opencv-python`, `requests`, `websockets`
- Remotion: `remotion` (v4.0+), `@remotion/bundler`, `@remotion/renderer`, `react` (v19), `tailwindcss` / vanilla CSS  
**Storage**: Local filesystem for media caches (`outputs/`, `assets/`, `outputs/temp/`), cloud storage for RunPod ComfyUI outputs  
**Testing**: `pytest` (unit & integration tests for Python core), `jest` / Remotion test renderer for React components  
**Target Platform**: macOS / Linux workstations + RunPod NVIDIA RTX 4090 (24GB VRAM) cloud instances  
**Project Type**: Hybrid CLI & Library + Web-based Video Compositor (Remotion)  
**Performance Goals**: Complete 30-to-60s vertical video rendered within 5 minutes; sub-100ms subtitle-to-audio synchronization; 60fps Remotion master render  
**Constraints**: <$0.25 total compute cost per video; zero visual hallucinations on riddle solutions; unmetered flat-rate rendering on RunPod ($0.44/hr)  
**Scale/Scope**: 3 core genres (Riddle, Story, Action), 6 typed image roles, dual ingestion modes, unlimited batch production  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Gate | Status | Evaluation & Compliance |
| :--- | :--- | :--- |
| **I. Clean Separation of Concerns** | **PASS** | Clear boundary between Python Orchestrator (`core/`) and React Master Compositor (`remotion/`). |
| **II. Deterministic Logic Guarantee** | **PASS** | Riddles and logic puzzles routed strictly through `PROGRAMMATIC_HYBRID` (0% hallucination). |
| **III. Contract-Driven Interfaces** | **PASS** | Explicit JSON schemas defined in `contracts/` for Director manifests, Remotion props, and ComfyUI API calls. |
| **IV. Continuity & Integrity** | **PASS** | Tail-to-Head Frame Chaining preserves sub-pixel physical continuity across consecutive video shots. |
| **V. Cost Predictability** | **PASS** | Free programmatic assets for logic, unmetered RunPod GPU for creative diffusion. |

---

## Project Structure

### Documentation (this feature)

```text
specs/001-universal-video-pipeline/
├── spec.md              # Feature specification
├── plan.md              # Implementation plan (this file)
├── research.md          # Phase 0 technical research & technology decisions
├── data-model.md        # Phase 1 entity specifications & relationships
├── quickstart.md        # Phase 1 runnable validation guide
├── contracts/           # Phase 1 JSON Schema interface contracts
│   ├── director_manifest_schema.json
│   ├── remotion_render_props_schema.json
│   └── comfyui_api_contract_schema.json
└── checklists/
    └── requirements.md  # Requirements completeness checklist
```

### Source Code Layout (repository root)

```text
ai-text-to-video/
├── core/                        # Python Orchestration Core
│   ├── __init__.py
│   ├── models.py                # Pydantic v2 schemas (VideoProject, StoryboardBeat, etc.)
│   ├── director.py              # LLM storyboard generator & intent classifier
│   ├── audio_engine.py          # Edge-TTS synthesis & Faster-Whisper alignment
│   ├── sfx_mixer.py             # Sound effect library & dynamic audio ducking
│   ├── visual_router.py         # Tri-Strategy Anti-Reroll dispatcher
│   ├── chain_manager.py         # Tail-to-Head frame extraction (Frame -1 ➔ Frame 0)
│   ├── runpod_client.py         # ComfyUI WebSocket/REST client for RunPod GPU
│   └── pipeline.py              # Main CLI & programmatic execution orchestrator
├── remotion/                    # Master React Video Compositor
│   ├── src/
│   │   ├── Root.tsx             # Master Remotion composition registration
│   │   ├── index.ts             # Entry point
│   │   ├── components/          # Reusable motion UI components
│   │   │   ├── KineticSubtitles.tsx
│   │   │   ├── CountdownDial.tsx
│   │   │   ├── SpriteLayer.tsx
│   │   │   └── AudioMixer.tsx
│   │   └── templates/           # Genre-specific layout templates
│   │       ├── RiddleTemplate.tsx
│   │       ├── StoryTemplate.tsx
│   │       └── ActionTemplate.tsx
│   ├── package.json
│   ├── tsconfig.json
│   └── remotion.config.ts
├── assets/                      # Static assets, sound library, sprites
│   ├── audio/sfx/               # Whooshes, impacts, ticks, risers
│   ├── audio/music/             # Ambient background tracks
│   └── processed/               # Clean transparent sprites & plates
├── outputs/                     # Rendered MP4s and intermediate clips
└── tests/                       # Test suites
    ├── unit/                    # Core logic and schema validation tests
    └── integration/             # End-to-end pipeline & contract tests
```

**Structure Decision**: A hybrid architecture consisting of a Python backend core (`core/`) for intelligent AI orchestration, audio synthesis, and GPU API communication, paired with a modern Remotion React app (`remotion/`) for frame-accurate, broadcast-quality video compositing.

---

## Complexity Tracking

| Component | Why Needed | Simpler Alternative Rejected Because |
| :--- | :--- | :--- |
| **Remotion Compositor** | Sub-frame kinetic typography, SVG dials, audio ducking | FFmpeg direct/MoviePy has audio desync drift, sluggish styling, and poor animation control |
| **RunPod ComfyUI Client** | Unmetered video diffusion inference without per-call fees | Closed APIs (Luma/Runway) cost $0.30–$0.50 per reroll; local Mac lacks 24GB VRAM |
| **Tail-to-Head Frame Chaining** | Zero-jump-cut physical continuity between multi-shot actions | Standard independent T2V generation causes severe character popping and lighting resets |
