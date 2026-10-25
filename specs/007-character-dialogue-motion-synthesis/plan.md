# Implementation Plan: Multi-Character Dialogue Attribution & Continuous Video Motion Synthesis

**Branch**: `007-character-dialogue-motion-synthesis` | **Date**: 2026-10-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/007-character-dialogue-motion-synthesis/spec.md`

## Summary

This feature resolves two primary user-facing problems identified during production video generation:
1. **Elimination of "Shuttering/Strobe" Images in Video Output**: Replaces standard 2D `EmptyLatentImage` batching in the Wan 2.1 ComfyUI workflow with native 3D temporal video latents (`EmptyHunyuanLatentVideo` / `WanImageToVideo`), directly injecting the approved storyboard keyframe image so the clip animates smoothly from the approved artwork across the entire scene duration without strobe flicker or terminal frame freezes.
2. **Transition from Monotone Narrator to Multi-Character Dialogue**: Instructs the Story Writer LLM to explicitly identify speaking characters per scene, assigns character-specific vocal personas, and executes scene-by-scene speech synthesis with Remotion audio timeline sequencing so distinct characters speak with unique voices.
3. **4-Part Kinetic Prompt Architecture**: Formulates prompts into *Subject Action*, *Interaction*, *Environmental Physics*, and *Camera Kinetics*, ensuring motion vectors guide diffusion instead of static descriptions.

## Technical Context

**Language/Version**: Python 3.12 (Backend), TypeScript 5.7 / React 19 (Web Studio & Remotion)  
**Primary Dependencies**:
- Backend: FastAPI, Pydantic v2, `google-genai`, `edge-tts`, `faster-whisper`, `opencv-python`, `requests`
- Frontend: React 19, Vite, Lucide React, Remotion 4.0  
**Storage**: JSON file-persisted storyboard sessions (`outputs/temp/sessions/*.json`), staged media (`outputs/temp/`), master video outputs (`outputs/`)  
**Testing**: `pytest` (backend unit, integration, and contract tests), `npm run build` (frontend compilation)  
**Target Platform**: macOS (Apple Silicon / Darwin) + RunPod Serverless GPU workers (NVIDIA RTX 4090 / A5000)  
**Project Type**: AI Full-Stack Video Production Studio (CLI + FastAPI Server + React Web Studio + Remotion Compositor)  
**Performance Goals**:
- Story Generation (LLM): < 5.0 seconds
- Voiceover & Whisper Subtitle Extraction: < 3.0 seconds per scene
- Serverless Video Synthesis: 4 concurrent beats rendered in parallel within ~350–400s
- Master Remotion Video Compilation: < 30 seconds  
**Constraints**: Zero paid token waste (preserves API credits via free Edge-TTS & caching), strict visual continuity, 100% test pass rate  
**Scale/Scope**: 1 to 6 narrative beats per video, up to 4 concurrent serverless GPU workers  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Gate | Status | Compliance Details |
| :--- | :---: | :--- |
| **I. Library & Component First** | ✅ Pass | Character voice attribution and video workflow generators are encapsulated as modular functions in `core/` and reused across CLI, API, and Web Studio. |
| **II. Observable & Text I/O** | ✅ Pass | All prompts, plans, and ComfyUI payloads are structured JSON, persisted to disk and inspectable. |
| **III. Test-First & Regression Defense** | ✅ Pass | All changes are guarded by existing 57 unit/integration tests and new contract tests. |
| **IV. Zero-Waste Token Preservation** | ✅ Pass | Audio synthesis utilizes local/Edge-TTS caching to prevent repeated API calls during rerolls. |

## Project Structure

### Documentation (this feature)

```text
specs/007-character-dialogue-motion-synthesis/
├── spec.md              # Feature specification
├── plan.md              # This file (implementation plan)
├── research.md          # Phase 0 technical research & decisions
├── data-model.md        # Phase 1 schema & entity definitions
├── quickstart.md        # Phase 1 runnable validation scenarios
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── contracts/
    ├── storyboard_card_update_contract.json
    └── wan3_video_workflow_contract.json
```

### Source Code Impact

```text
core/
├── models.py                   # Add speaker to SceneBeatPlan and StoryboardCard
├── story_writer.py             # Update LLM prompt to output character speakers & 4-part motion prompts
├── audio_engine.py             # Support per-scene multi-speaker dialogue synthesis
├── interactive_director.py     # Execute scene-by-scene audio rendering & timeline offset assembly
├── runpod_client.py            # Update Wan 2.1 workflow builder to use EmptyHunyuanLatentVideo & keyframe injection
├── server.py                   # Add PATCH /api/storyboard/beat endpoint for card updates
└── workflows/
    └── wan3_omni_reference.json # Replace EmptyLatentImage with EmptyHunyuanLatentVideo / I2V nodes

studio/src/
├── types/index.ts              # Add speaker field to StoryboardCard interface
└── components/
    └── BeatCard.tsx            # Add Speaker Name badge and Voice Actor dropdown selector
```

## Complexity Tracking

No constitution violations detected. Architecture strictly follows existing modular pipeline patterns without introducing extraneous dependencies.
