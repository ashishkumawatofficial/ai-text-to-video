# Implementation Plan: Iterative Shot Chaining & Single-Beat Rendering in Pro Director

**Branch**: `008-iterative-shot-chaining` | **Date**: 2026-10-25 | **Spec**: [specs/008-iterative-shot-chaining/spec.md](file:///Users/ashishkumavat/Projects/ai-text-to-video/specs/008-iterative-shot-chaining/spec.md)

**Input**: Feature specification from `specs/008-iterative-shot-chaining/spec.md`

---

## Summary

Enable creators using Pro Director mode to render video clips one beat at a time, inspect and approve each shot in isolation, capture the terminal frame (Frame -1) of a completed clip to bind as the initial starting anchor of the next consecutive shot for 100% optical continuity, and compile all individually approved clips into a master 1080p video with audio, SFX, and subtitles in under 15 seconds.

---

## Technical Context

**Language/Version**: Python 3.11+ (Backend) / TypeScript 5.x & React 18 (Frontend Studio)  
**Primary Dependencies**: FastAPI, Pydantic v2, OpenCV (`cv2`), Remotion, React, Lucide React  
**Storage**: Local JSON session records (`outputs/temp/sessions/{session_id}.json`), file assets (`outputs/temp/chain_*.png`, `outputs/temp/scene_*.mp4`), in-memory session registry (`_ACTIVE_SESSIONS`)  
**Testing**: PyTest (`./.venv/bin/pytest`) for backend endpoints & frame chaining; component & API integration tests  
**Target Platform**: Linux / macOS (FastAPI backend, RunPod Serverless GPU workers, local browser)  
**Project Type**: Full-Stack Web Application (FastAPI backend + Vite/React frontend)  
**Performance Goals**: 
- Single-beat generation: < 90s on Serverless GPU, < 5s on local mock plate
- Terminal frame extraction: < 80ms via OpenCV `total_frames - 1` seek
- Master video compilation: < 15s when scene clips are pre-rendered  
**Constraints**: 
- Single-beat rendering must strictly avoid triggering batch parallel dispatch of other beats
- Chaining Frame -1 must guarantee bit-identical frame handoff to prevent optical jump cuts
- Fully backward-compatible with 1-Click Auto batch synthesis  
**Scale/Scope**: 4 new/updated API endpoints, 1 updated component (`BeatCard.tsx`), 1 updated sidebar (`DirectorSidebar.tsx`), 1 updated service client (`api.ts`), 2 updated backend modules (`core/server.py`, `core/models.py`)

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Gate | Status | Assessment |
|---|---|---|
| **I. Library-First & Modularity** | **PASS** | Chaining engine encapsulated in `core/chain_manager.py`; single-beat dispatch leverages `RunPodServerlessClient.execute_video_job()`. |
| **II. API & Protocol Contract** | **PASS** | Formally documented OpenAPI 3.1 contract in `contracts/chaining_api.json` with strict input/output DTOs. |
| **III. Test-First (TDD)** | **PASS** | Verification scenarios defined in `quickstart.md` and test suite `tests/test_studio_backend.py`. |
| **IV. Integration Integrity** | **PASS** | Preserves existing batch render routes (`/api/render/start`) while adding discrete single-beat routes. |
| **V. Simplicity & YAGNI** | **PASS** | Uses native OpenCV already present in `.venv`; avoids unnecessary background message queue or custom microservices. |

---

## Project Structure

### Documentation (this feature)

```text
specs/008-iterative-shot-chaining/
├── plan.md              # Implementation plan (this file)
├── research.md          # Phase 0 decisions: OpenCV seeking, single-beat routing, Remotion compilation
├── data-model.md        # Phase 1 data models: StoryboardCard, ContinuityLink, API DTOs
├── quickstart.md        # Phase 1 validation scenarios and test commands
├── contracts/           # Phase 1 OpenAPI interface specifications
│   └── chaining_api.json
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (Concrete Repository Paths)

```text
core/
├── models.py            # StoryboardCard (add is_chained, chained_from_beat, chain_out_of_sync)
├── chain_manager.py     # extract_terminal_frame(), chain_shots()
├── server.py            # POST /api/render/beat, POST /api/storyboard/chain-frame,
│                        # POST /api/storyboard/unlink-chain, POST /api/render/compile
├── interactive_director.py # Session state persistence & beat synchronization
└── runpod_serverless.py # execute_video_job() single beat worker dispatch

studio/
├── src/
│   ├── components/
│   │   ├── BeatCard.tsx        # Add Render Beat button, Chain to Shot K+1 button, inline player
│   │   └── DirectorSidebar.tsx # Add Compile Master Video button in Pro Director mode
│   ├── services/
│   │   └── api.ts              # renderBeat(), chainFrame(), unlinkChain(), compileMaster()
│   └── App.css                 # Continuity badge styles, chaining animations

tests/
├── test_studio_backend.py      # Unit & integration tests for single-beat and chaining routes
└── test_chain_manager.py       # Frame extraction and continuity link validation
```

**Structure Decision**: Integrated directly into existing full-stack architecture (`core/` backend services and `studio/` React web application).

---

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*No violations. All components adhere directly to the architectural principles.*
