# Tasks: Wan 3.0 ComfyUI Recipe, RunPod Integration, and Local Visual Mock Preview

**Feature Directory**: `specs/002-wan3-runpod-preview`  
**Input**: Design artifacts from `spec.md`, `plan.md`, `data-model.md`, `contracts/`, `research.md`, `quickstart.md`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 [P] Initialize workflows directory and model schema bindings in `core/workflows/`
- [x] T002 [P] Configure endpoint configuration constants and environment bindings in `core/models.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core domain models and test scaffolding that MUST be complete before user stories begin

**⚠️ CRITICAL**: No user story implementation can begin until this phase is complete

- [x] T003 Implement `RunPodHealthReport` and `Wan3WorkflowConfig` Pydantic models in `core/models.py`
- [x] T004 [P] Implement `LocalKeyframeAsset` Pydantic model in `core/models.py`
- [x] T005 [P] Setup unit test scaffolding in `tests/test_health_check.py`, `tests/test_wan3_workflow.py`, and `tests/test_local_visual_mock.py`

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 - Instant Local Visual Mock & Ken Burns Storyboard Generation (Priority: P1) 🎯 MVP

**Goal**: When running locally without GPU, automatically generate high-definition visual keyframes, animate with smooth 2.5D Ken Burns zoom/pan in Remotion, and restore 6-glasses puzzle graphics so prompt-to-video renders a moving, illustrated storyboard in <30s.

**Independent Test**: Run `python -m core.cli render --prompt "A clever cyber detective uncovers a secret data core in the rain"` with no GPU connected. The output video must contain vibrant illustrated scene backgrounds with continuous camera movement, kinetic subtitles, and synchronized audio (zero blank placeholder plates).

### Tests for User Story 1

- [x] T006 [P] [US1] Create unit test for local keyframe synthesis in `tests/test_local_visual_mock.py`
- [x] T007 [P] [US1] Create unit test for riddle asset generator in `tests/test_riddle_assets.py`

### Implementation for User Story 1

- [x] T008 [US1] Implement `core/local_visual_mock.py` for lightweight text-to-image synthesis, prompt hashing, and file caching in `outputs/temp/`
- [x] T009 [US1] Create procedural puzzle asset generator in `scripts/generate_riddle_assets.py` (restoring `assets/processed/reference_1080.png`)
- [x] T010 [US1] Integrate local visual mock fallback into `core/visual_router.py` when ComfyUI is unavailable
- [x] T011 [US1] Update `core/remotion_bridge.py` to stage generated keyframe assets into `remotion/public/media/`
- [x] T012 [US1] Implement 2.5D Ken Burns smooth camera zoom/pan interpolation in `remotion/src/templates/StoryTemplate.tsx`
- [x] T013 [US1] Add procedural inline SVG fallback for the 6 glasses puzzle in `remotion/src/templates/RiddleTemplate.tsx`

**Checkpoint**: User Story 1 is fully functional and testable independently.

---

## Phase 4: User Story 2 - Wan 3.0 Omni-Reference Video Generation Recipe (Priority: P2)

**Goal**: Provide a validated ComfyUI API workflow recipe for Wan 3.0 supporting up to 10 reference images (character identity, wardrobe, environment, anchor frames) and continuous video generation up to 30s.

**Independent Test**: Dispatch a multi-scene beat with 3 character reference images to the Wan 3.0 workflow recipe. The resulting ComfyUI payload must correctly map all image references into the multi-conditioning nodes and produce continuous video output matching the specified duration.

### Tests for User Story 2

- [x] T014 [P] [US2] Create unit test for Wan 3.0 recipe payload binding in `tests/test_wan3_workflow.py`

### Implementation for User Story 2

- [x] T015 [US2] Author `core/workflows/wan3_omni_reference.json` ComfyUI API node graph with checkpoint loader, multi-reference conditioning, and latent video generation
- [x] T016 [US2] Implement Wan 3.0 workflow payload builder and reference slot mapper (up to 10 images) in `core/runpod_client.py`
- [x] T017 [US2] Update `core/visual_router.py` to route multi-reference character beats to `wan3_omni_reference.json`

**Checkpoint**: User Story 2 is fully functional and testable independently.

---

## Phase 5: User Story 3 - RunPod Cloud Connection & Health Diagnostics (Priority: P3)

**Goal**: Provide a dedicated `python -m core.cli health` command to test connectivity, report latency, VRAM availability, and loaded model checkpoints.

**Independent Test**: Run `python -m core.cli health`. The CLI outputs clear connection status, ping latency, GPU specifications, and lists whether Wan 3.0 or fallback models are loaded.

### Tests for User Story 3

- [x] T018 [P] [US3] Create unit test for endpoint diagnostic parser in `tests/test_health_check.py`

### Implementation for User Story 3

- [x] T019 [US3] Implement `check_endpoint_health()` in `core/runpod_client.py` querying `/system_stats` and `/object_info`
- [x] T020 [US3] Add `health` subcommand to `core/cli.py` with formatted terminal diagnostics report

**Checkpoint**: User Story 3 is fully functional and testable independently.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, regression testing, and end-to-end validation

- [x] T021 [P] Update documentation and usage examples in `README.md`
- [x] T022 Run end-to-end regression test suite across all 3 user stories via `pytest tests/`
- [x] T023 Run quickstart validation scenarios defined in `specs/002-wan3-runpod-preview/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Can start immediately.
- **Foundational (Phase 2)**: Depends on Setup (Phase 1). Blocks all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2). Delivers MVP.
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2). Can execute in parallel with US1 or sequentially.
- **User Story 3 (Phase 5)**: Depends on Foundational (Phase 2). Can execute in parallel with US1/US2.
- **Polish (Phase 6)**: Depends on US1, US2, and US3 completion.

### Parallel Opportunities

- `T001` and `T002` in Setup can run in parallel.
- `T004` and `T005` in Foundational can run in parallel.
- `T006` and `T007` tests can run in parallel.
- `T014` and `T018` tests can run in parallel once Foundational is complete.
- User Stories 1, 2, and 3 touch distinct files and can proceed in parallel once Phase 2 is finished.

---

## Implementation Strategy: MVP First

1. Complete **Phase 1: Setup** & **Phase 2: Foundational** (T001–T005). [COMPLETE]
2. Complete **Phase 3: User Story 1 (MVP)** (T006–T013). [COMPLETE]
3. **Validate MVP**: Run `python -m core.cli render --prompt "..."` and verify full visual video generated locally with Ken Burns camera movement in under 30s! [COMPLETE]
4. Complete **Phase 4: User Story 2 (Wan 3.0 Recipe)** (T014–T017). [COMPLETE]
5. Complete **Phase 5: User Story 3 (RunPod Health)** (T018–T020). [COMPLETE]
6. Complete **Phase 6: Polish & Verification** (T021–T023). [COMPLETE]
