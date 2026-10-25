# Tasks: 006 Web Studio Interface & AI Director Copilot

**Input**: Design artifacts from `specs/006-web-studio-interface/` (`spec.md`, `plan.md`, `data-model.md`, `contracts/`, `quickstart.md`)  
**Status**: Ready for Implementation  

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize full-stack dependencies and scaffold frontend and backend environments.

- [x] T001 Add backend dependencies (`fastapi`, `uvicorn`, `sse-starlette`) to `requirements.txt` and install in `.venv`
- [x] T002 Scaffold React 18 + Vite TypeScript project in `studio/` with `@remotion/player`, `remotion`, and `lucide-react`
- [x] T003 [P] Configure Vite dev server proxy in `studio/vite.config.ts` to route `/api/*` to FastAPI backend at `http://localhost:8000`

---

## Phase 2: Foundational (Core Backend & Shared State)

**Purpose**: Core data models, API routing, and CLI launch command required before user stories can run.

- [x] T004 Implement studio domain models (`StudioSession`, `StoryboardCard`, `ChatMessage`, `TelemetryState`) in `core/models.py`
- [x] T005 [P] Implement FastAPI backend application in `core/server.py` with CORS, error handling, and health check endpoint `GET /api/health`
- [x] T006 Add `studio` command to `core/cli.py` to concurrently launch both the FastAPI backend and Vite frontend from the terminal

**Checkpoint**: Foundation ready — backend responds at `http://localhost:8000/api/health` and Vite dev server runs at `http://localhost:5173`.

---

## Phase 3: User Story 1 - Visual Storyboard Canvas & Parameter Controls (Priority: P1) 🎯 MVP

**Goal**: Visual canvas rendering narrative beat cards with keyframes, prompt, dialogue, camera move, and single-beat surgical re-roll.

**Independent Test**: Plan a 4-beat concept prompt via `POST /api/storyboard/generate`, confirm all beat cards render with keyframe previews on the canvas, toggle aspect ratio between `16:9` and `9:16`, and trigger a single-beat re-roll verifying only that card updates.

### Tests for User Story 1
- [x] T007 [P] [US1] Unit test for storyboard generation and single-beat re-roll endpoints in `tests/test_studio_backend.py`

### Implementation for User Story 1
- [x] T008 [US1] Implement `POST /api/storyboard/generate` in `core/server.py` integrating `InteractiveDirector.direct_session()`
- [x] T009 [US1] Implement `POST /api/storyboard/reroll` in `core/server.py` integrating `InteractiveDirector.regenerate_beat()`
- [x] T010 [P] [US1] Implement React API client in `studio/src/services/api.ts` for storyboard generation and re-roll
- [x] T011 [P] [US1] Implement `StoryboardCanvas.tsx` and `BeatCard.tsx` in `studio/src/components/` with keyframe image previews, camera badges, and prompt editing
- [x] T012 [US1] Implement `AspectRatioToggle.tsx` in `studio/src/components/` and integrate with canvas layout for `16:9` and `9:16`

**Checkpoint**: User Story 1 (MVP) is fully functional and testable independently.

---

## Phase 4: User Story 2 - Conversational Gemini AI Co-Director Chat (Priority: P1)

**Goal**: Natural language interactive chat with Gemini to adjust scenes, update prompts, and apply real-time delta updates to canvas cards.

**Independent Test**: Type a conversational prompt (*"Make beat 2 darker and add rain"*) into the chat sidebar, verify Gemini replies with a confirmation, and verify Card #2's prompt updates automatically on screen.

### Tests for User Story 2
- [x] T013 [P] [US2] Unit test for conversational director chat delta parser in `tests/test_director_chat.py`

### Implementation for User Story 2
- [x] T014 [US2] Implement conversational delta engine in `core/director_chat.py` with structured JSON actions (`UPDATE_BEAT`, `REROLL_KEYFRAME`, `UPDATE_SCRIPT`, `CHANGE_ASPECT_RATIO`)
- [x] T015 [US2] Implement `POST /api/director/chat` endpoint in `core/server.py` using `director_chat.py`
- [x] T016 [P] [US2] Implement `DirectorSidebar.tsx` in `studio/src/components/` with chat history thread, quick prompts, and real-time canvas delta synchronizer

**Checkpoint**: User Stories 1 and 2 operate cohesively together.

---

## Phase 5: User Story 3 - Dual Directing Modes (1-Click Auto vs Pro-Director) (Priority: P2)

**Goal**: Seamless toggle between unattended 1-click video creation and pro-director review & approval gate.

**Independent Test**: Run a concept in 1-Click Auto mode and verify full pipeline execution to player, then run in Pro-Director mode and verify synthesis pauses at the canvas until approved.

### Tests for User Story 3
- [x] T017 [P] [US3] Unit test for 1-click auto vs pro-director approval gate in `tests/test_studio_backend.py`

### Implementation for User Story 3
- [x] T018 [US3] Implement execution orchestrator in `core/server.py` supporting both 1-Click direct synthesis and Pro-Director approval triggers
- [x] T019 [US3] Implement mode switcher and "1-Click Generate" vs "Approve & Synthesize" buttons in `studio/src/components/DirectorSidebar.tsx`

**Checkpoint**: Dual directing modes independently functional.

---

## Phase 6: User Story 4 - Live In-Browser Remotion Player & Serverless Telemetry (Priority: P2)

**Goal**: 60 FPS in-browser video scrubbing with kinetic subtitles, audio-ducked BGM, and real-time RunPod GPU worker telemetry with live USD cost meter.

**Independent Test**: Trigger a parallel serverless render, observe real-time GPU worker status tiles and incrementing USD billing in the UI, verify video plays smoothly upon completion, and test the "Cancel All" button.

### Tests for User Story 4
- [x] T020 [P] [US4] Unit test for telemetry SSE stream and batch cancellation in `tests/test_studio_backend.py`

### Implementation for User Story 4
- [x] T021 [US4] Implement `GET /api/events` (SSE) and `POST /api/render/cancel` in `core/server.py` calling `RunPodServerlessClient.cancel_batch()`
- [x] T022 [P] [US4] Implement `TelemetryGrid.tsx` in `studio/src/components/` showing real-time GPU worker tiles, elapsed time, and USD cost counter
- [x] T023 [US4] Implement `RemotionPlayerPane.tsx` in `studio/src/components/` embedding `@remotion/player` with playback controls and 1-click MP4 export

**Checkpoint**: Complete end-to-end studio experience operational.

---

## Phase 7: Polish & Validation

**Purpose**: Aesthetic enhancements, documentation, and regression validation across all components.

- [x] T024 [P] Create rich dark-mode studio theme with glassmorphism and subtle animations in `studio/src/styles/studio.css`
- [x] T025 Update `README.md` with instructions on running the Web Studio (`python -m core.cli studio`)
- [x] T026 Execute full quickstart validation scenarios and run backend test suite (`pytest tests/`)

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (Phase 1)**: No dependencies — executes immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 — blocks all user stories.
- **User Story 1 (Phase 3)**: Depends on Phase 2 — MVP foundation.
- **User Story 2 (Phase 4)**: Depends on Phase 2 & Phase 3 (attaches to Storyboard Canvas).
- **User Story 3 (Phase 5)**: Depends on Phase 3.
- **User Story 4 (Phase 6)**: Depends on Phase 3 (renders approved beats).
- **Polish (Phase 7)**: Depends on completion of all user story phases.

### Parallel Opportunities
- T003 (Vite config) can run parallel to T002.
- T005 (FastAPI server) can run parallel to T004.
- T010 (API client) and T011 (Canvas cards) can run parallel to T008/T009.
- T013 (Chat test) and T016 (Chat UI) can run parallel to T014/T015.
- T020 (Telemetry test) and T022 (Telemetry UI) can run parallel to T021.
