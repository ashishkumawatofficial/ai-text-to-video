# Tasks: Interactive Storyboard Review, Conversational Modification, and Multi-Modal Director Engine

**Feature Directory**: `specs/003-interactive-storyboard-approval`  
**Input**: Design artifacts from `spec.md`, `plan.md`, `data-model.md`, `contracts/`, `research.md`, `quickstart.md`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 [P] Initialize session persistence directory in `outputs/temp/sessions/`
- [x] T002 [P] Implement `ConditioningMode`, `ApprovalStatus`, and `ReferenceAsset` models in `core/models.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core domain models, session store, and test scaffolding that MUST be complete before user stories begin

**⚠️ CRITICAL**: No user story implementation can begin until this phase is complete

- [x] T003 Implement `SceneBeatPlan`, `DirectorMasterPlan`, and `StoryboardSession` Pydantic models in `core/models.py`
- [x] T004 [P] Implement `StoryboardSessionManager` in `core/session_manager.py` (JSON session persistence and turn history tracking)
- [x] T005 [P] Setup unit test scaffolding in `tests/test_session_manager.py`, `tests/test_conditioning_engine.py`, and `tests/test_interactive_director.py`

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 - Interactive Storyboard Framing & Approval Gate (Priority: P1) 🎯 MVP

**Goal**: When a user inputs a concept prompt, rapidly synthesize a complete visual storyboard (scene beats, generated 9:16 keyframes, dialogue lines, and sound cues) and halt at an interactive approval gate before initiating video rendering.

**Independent Test**: Run `python -m core.cli direct --prompt "A brave astronaut discovering an ancient crystal on Mars"`. The terminal displays a complete multi-beat storyboard with keyframe paths, audio strategy, and pauses at `[A]pprove & Render Video | [M]odify Beat | [Q]uit > `, rendering zero video files until approved.

### Tests for User Story 1

- [x] T006 [P] [US1] Create unit tests for storyboard planning and approval gate pause in `tests/test_interactive_director.py`

### Implementation for User Story 1

- [x] T007 [US1] Implement `InteractiveDirector` in `core/interactive_director.py` (deconstructs prompt, plans beats, synthesizes 9:16 keyframes via `generate_local_keyframe`, and returns `DirectorMasterPlan`)
- [x] T008 [US1] Implement interactive REPL loop in `core/cli.py` (subcommand `direct` displaying formatted table, waiting for approval before invoking `render_project_to_video`)
- [x] T009 [US1] Add `--auto-approve` flag to `core/cli.py` for non-interactive automated scripting

**Checkpoint**: User Story 1 is fully functional and testable independently.

---

## Phase 4: User Story 2 - Conversational Delta Modification via Chat (Priority: P2)

**Goal**: Enable creators to request changes to any scene, dialogue line, visual element, pacing, or audio property through conversational feedback, applying surgical delta edits only to affected beats without re-generating unaffected assets.

**Independent Test**: In an active storyboard session, enter `modify 2 make the crystal glowing purple and remove the voiceover`. Beat 2's visual prompt and keyframe image regenerate in `<3s`, `dialogue_text` is cleared, and Beat 1 remains completely untouched.

### Tests for User Story 2

- [x] T010 [P] [US2] Create unit tests for conversational modification parsing and delta invalidation in `tests/test_interactive_director.py`

### Implementation for User Story 2

- [x] T011 [US2] Implement conversational instruction parser and delta modifier in `core/interactive_director.py` (`apply_modification(session_id, instruction)`)
- [x] T012 [US2] Implement delta keyframe cache invalidator in `core/session_manager.py` (regenerates only modified beat keyframes in `outputs/temp/`)
- [x] T013 [US2] Connect interactive CLI REPL `modify <beat_index> <instruction>` command in `core/cli.py`

**Checkpoint**: User Story 2 is fully functional and testable independently.

---

## Phase 5: User Story 3 - Multi-Modal Asset Ingestion & Autonomous Conditioning (Priority: P3)

**Goal**: Ingest user-provided reference assets (character headshots, environment plates, start/end frames) and autonomously determine the optimal diffusion conditioning strategy (`pure_t2v`, `start_frame_only`, `start_and_end_frame`, `chain_from_previous`, or `hard_cut`) per scene.

**Independent Test**: Run `python -m core.cli direct --prompt "Detective corners android. Action strike then arrest." --character "detective:assets/detective_scene1.jpg"`. Beat 1 anchors to the character plate, Beat 2 (whip pan cut) is classified as `hard_cut`, and Beat 3 (continuous arrest) is classified as `chain_from_previous`.

### Tests for User Story 3

- [x] T014 [P] [US3] Create unit tests for character reference binding and continuous chaining in `tests/test_conditioning_engine.py`

### Implementation for User Story 3

- [x] T015 [US3] Implement `core/conditioning_engine.py` (autonomous classifier for frame chaining, start/end frames, and editorial cuts)
- [x] T016 [US3] Implement terminal frame extractor for continuous chaining in `core/remotion_bridge.py` (`outputs/temp/last_frame_beat_{N-1}.jpg`)
- [x] T017 [US3] Add multi-modal CLI options `--character`, `--environment`, and `--start-frame` to `core/cli.py`

**Checkpoint**: User Story 3 is fully functional and testable independently.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, regression testing, and end-to-end validation

- [x] T018 [P] Update documentation and usage examples in `README.md`
- [x] T019 Run end-to-end regression test suite across all user stories via `pytest tests/`
- [x] T020 Run quickstart validation scenarios defined in `specs/003-interactive-storyboard-approval/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Can start immediately.
- **Foundational (Phase 2)**: Depends on Setup (Phase 1). Blocks all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2). Delivers MVP.
- **User Story 2 (Phase 4)**: Depends on User Story 1 (Phase 3).
- **User Story 3 (Phase 5)**: Depends on Foundational (Phase 2). Can execute in parallel with US1/US2.
- **Polish (Phase 6)**: Depends on US1, US2, and US3 completion.

### Parallel Opportunities

- `T001` and `T002` in Setup can run in parallel.
- `T004` and `T005` in Foundational can run in parallel.
- `T006`, `T010`, and `T014` test tasks can run in parallel.
- `T015` (Conditioning Engine) can be developed in parallel with `T011` (Delta Modifier).

---

## Implementation Strategy: MVP First

1. Complete **Phase 1: Setup** & **Phase 2: Foundational** (T001–T005).
2. Complete **Phase 3: User Story 1 (MVP)** (T006–T009).
3. **Validate MVP**: Run `python -m core.cli direct --prompt "A brave astronaut discovering an ancient crystal on Mars"` and verify the interactive approval gate pauses with full storyboard in under 5 seconds!
4. Complete **Phase 4: User Story 2 (Conversational Delta Modification)** (T010–T013).
5. Complete **Phase 5: User Story 3 (Multi-Modal & Autonomous Conditioning)** (T014–T017).
6. Complete **Phase 6: Polish & Verification** (T018–T020).
