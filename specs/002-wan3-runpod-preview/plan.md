# Implementation Plan: Wan 3.0 ComfyUI Recipe, RunPod Integration, and Local Visual Mock Preview

**Branch**: `002-wan3-runpod-preview` | **Date**: 2026-10-23 | **Spec**: [spec.md](file:///Users/ashishkumavat/Projects/ai-text-to-video/specs/002-wan3-runpod-preview/spec.md)

**Input**: Feature specification from `specs/002-wan3-runpod-preview/spec.md`

---

## Summary

This feature extends the Universal AI Video Production Studio with three core visual capabilities:
1. **Local Visual Mock & Ken Burns Storyboard Engine**: Generates high-definition visual keyframes and applies smooth 2.5D camera pan/zoom in Remotion when running without a GPU pod, alongside restoring visual puzzle assets for riddles ($0.00 cost, renders in <30s).
2. **Wan 3.0 Omni-Reference ComfyUI Recipe**: Provides an automated ComfyUI API workflow recipe supporting Wan 3.0 with multi-image conditioning (up to 10 reference images) and extended continuous generation (up to 30s).
3. **RunPod Connection & Health Diagnostics**: Provides a dedicated `python -m core.cli health` diagnostic suite that tests connectivity, latency, available VRAM, and loaded model checkpoints on RunPod ComfyUI or Serverless endpoints.

---

## Technical Context

**Language/Version**: Python 3.12 (Virtualenv `.venv/`), TypeScript / React 18 (Remotion v4.0.538)  
**Primary Dependencies**:
- Python: `pydantic` v2, `requests`, `edge-tts`, `faster-whisper`, `opencv-python`, `ffmpeg`
- Node.js: `@remotion/cli`, `remotion`, `react`, `react-dom`  
**Storage**: Local filesystem (`outputs/temp/`, `remotion/public/media/`, `assets/processed/`)  
**Testing**: `pytest tests/`, `npm run build` (Remotion type-check)  
**Target Platform**: macOS (Apple Silicon / Intel) local workstation + Linux (Ubuntu 22.04 with NVIDIA RTX 4090 / A6000) on RunPod  
**Project Type**: Hybrid Python CLI Orchestrator + Headless React Video Compositor  
**Performance Goals**: Local visual storyboard rendering in `<30s`; ComfyUI health check round-trip in `<3s`  
**Constraints**: 100% render completion rate via automatic cloud-to-local fallback; zero unhandled crashes  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Zero Regressions**: Existing `cinematic_story`, `riddle`, and `action` pipelines must remain fully functional.
- [x] **Graceful Fallback**: Cloud GPU disconnection MUST fall back to local visual mock rendering without user-facing stack traces.
- [x] **Deterministic Logic**: Riddle and puzzle assets must remain 100% deterministic with zero AI counting hallucinations.
- [x] **Type Safety**: All payloads validated with Pydantic v2 domain models and TypeScript contracts.

---

## Project Structure

### Documentation (this feature)

```text
specs/002-wan3-runpod-preview/
├── spec.md                  # Feature specification
├── plan.md                  # This implementation plan
├── research.md              # Phase 0 research findings
├── data-model.md            # Phase 1 data models & schemas
├── quickstart.md            # Phase 1 runnable validation scenarios
├── contracts/               # Phase 1 JSON schema contracts
│   ├── wan3_workflow_contract.json
│   └── runpod_health_response_schema.json
└── checklists/
    └── requirements.md      # Specification quality checklist
```

### Source Code Architecture

```text
core/
├── cli.py                   # Add 'health' subcommand
├── runpod_client.py         # Add check_endpoint_health() and Wan 3.0 queueing
├── visual_router.py         # Integrate local visual mock fallback & Wan 3.0 dispatch
├── local_visual_mock.py     # NEW: High-definition keyframe synthesis & caching
├── workflows/
│   ├── comfy_character_i2v.json
│   └── wan3_omni_reference.json # NEW: Wan 3.0 10-reference ComfyUI API graph
remotion/
├── src/
│   ├── templates/
│   │   ├── StoryTemplate.tsx # Add Ken Burns 2.5D camera zoom/pan interpolation
│   │   └── RiddleTemplate.tsx# Add inline procedural SVG fallback for 6 glasses
scripts/
└── generate_riddle_assets.py# Procedural generator restoring 6-glasses reference plate
tests/
├── test_health_check.py     # Unit test for RunPod diagnostics
├── test_wan3_workflow.py    # Unit test for Wan 3.0 recipe validation
└── test_local_visual_mock.py# Integration test for local keyframe synthesis
```

---

## Phase Status

- [x] **Phase 0**: Research completed (`research.md`)
- [x] **Phase 1**: Design completed (`data-model.md`, `contracts/`, `quickstart.md`)
- [ ] **Phase 2**: Task breakdown (`tasks.md` via `/speckit-tasks`)
