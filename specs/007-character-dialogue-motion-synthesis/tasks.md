# Tasks: Multi-Character Dialogue Attribution & Continuous Video Motion Synthesis

**Feature Branch**: `007-character-dialogue-motion-synthesis`  
**Specification**: [spec.md](spec.md)  
**Implementation Plan**: [plan.md](plan.md)  
**Status**: Ready for Execution

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup (Shared Infrastructure)
       │
       ▼
Phase 2: Foundational (Models, Types, Core Audio Primitives)
       │
       ├─────────────────────────────────────────────┐
       ▼                                             ▼
Phase 3: User Story 1 (P1) 🎯 MVP        Phase 4: User Story 2 (P1)
Multi-Character Spoken Dialogue          Fluid Continuous Video Animation
       │                                             │
       ├─────────────────────────────────────────────┘
       ▼
Phase 5: User Story 3 (P2)
Kinetic 4-Part Motion Prompting & Pacing Alignment
       │
       ▼
Phase 6: User Story 4 (P2)
Interactive Speaker & Voice Direction in Web Studio
       │
       ▼
Phase 7: Polish & Cross-Cutting Concerns
Validation Scenarios & Regression Testing
```

- **Phase 1 (Setup)**: Initial structure and test scaffolding. Can start immediately.
- **Phase 2 (Foundational)**: Data models in `core/models.py` and TypeScript interfaces in `studio/src/types/index.ts`. **BLOCKS** all User Stories.
- **Phase 3 (User Story 1 - P1)**: Core multi-character dialogue attribution and per-scene audio synthesis.
- **Phase 4 (User Story 2 - P1)**: ComfyUI Wan 2.1 3D temporal video latent workflow and keyframe conditioning to eliminate strobe flickering. Can run in parallel with US1 once Phase 2 is complete.
- **Phase 5 (User Story 3 - P2)**: Kinetic 4-part motion prompt structure and duration calculation in story writer.
- **Phase 6 (User Story 4 - P2)**: Web Studio card speaker badges, voice selectors, and `PATCH /api/storyboard/beat` API endpoint.
- **Phase 7 (Polish)**: End-to-end integration testing, quickstart verification, and build validation.

---

## Parallel Opportunities

- **Phase 1 & 2**: All model definitions and type definitions marked `[P]` can be developed concurrently across Python and TypeScript.
- **Phase 3 & 4 (US1 & US2)**: Once Phase 2 completes, User Story 1 (Audio & Dialogue) and User Story 2 (ComfyUI Diffusion & Latents) touch independent subsystems (`core/audio_engine.py` vs `core/runpod_client.py`) and can execute in parallel.
- **Phase 6 (US4 UI & API)**: Web Studio frontend components in `studio/` and FastAPI route in `core/server.py` can be authored concurrently.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Test scaffolding and environment readiness

- [X] T001 Verify virtual environment dependencies and ComfyUI serverless templates in `core/workflows/`
- [X] T002 [P] Create unit test scaffold for multi-character story models in `tests/unit/test_multi_character_models.py`
- [X] T003 [P] Create unit test scaffold for Wan 2.1 temporal video latents in `tests/unit/test_wan3_temporal_workflow.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models and schemas that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: Blocks all user stories until schema fields are aligned across backend and frontend.

- [X] T004 Add `CharacterProfile` model and update `SceneBeatPlan` with `speaker: Optional[str] = "Narrator"` in `core/models.py`
- [X] T005 [P] Update `StoryboardCard` model with `speaker: str = "Narrator"` and `voice_actor: str = "auto"` in `core/models.py`
- [X] T006 [P] Update TypeScript interface `StoryboardCard` with `speaker?: string` and `voice_actor?: string` in `studio/src/types/index.ts`
- [X] T007 Implement unit tests verifying `SceneBeatPlan` and `StoryboardCard` serialization and backward compatibility in `tests/unit/test_multi_character_models.py`

**Checkpoint**: Foundation ready — User Story 1 and User Story 2 can now begin in parallel.

---

## Phase 3: User Story 1 - Multi-Character Spoken Dialogue Attribution (Priority: P1) 🎯 MVP

**Goal**: Automatically identify distinct speaking characters in story generation, assign dialogue lines to specific speakers, and synthesize each line with a unique vocal persona tailored to that character's personality.

**Independent Test**: Provide a prompt with two conversing characters (e.g. two cows having tea). Verify that the plan assigns distinct `speaker` names and distinct `voice_persona` IDs to dialogue turns, and audio engine generates separate audio files for each character.

### Tests for User Story 1
- [X] T008 [P] [US1] Create unit test for LLM character speaker attribution in `tests/unit/test_story_writer_characters.py`
- [X] T009 [P] [US1] Create unit test for per-scene multi-speaker audio synthesis and timeline offsets in `tests/unit/test_multi_speaker_audio.py`

### Implementation for User Story 1
- [X] T010 [US1] Update `_build_system_prompt()` in `core/story_writer.py` to instruct Gemini to identify distinct character speakers, assign `speaker` names, and select distinct `voice_persona` IDs (e.g. `cartoon_animal`, `male_casual`, `female_sarcastic`, `deep_villain`, `kid`) per scene beat
- [X] T011 [US1] Update `synthesize_scene_dialogue()` in `core/audio_engine.py` to accept character voice personas, resolve neural voices via `VOICE_PERSONAS`, and cache audio clips with beat-specific identifiers
- [X] T012 [US1] Refactor `render_approved_session()` in `core/interactive_director.py` to synthesize dialogue beat-by-beat rather than concatenating all scenes into a single narrator monologue
- [X] T013 [US1] Assemble individual beat audio tracks with calculated start frame offsets in `core/interactive_director.py` for Remotion composition sequencing
- [X] T014 [US1] Ensure word-level kinetic subtitle tracks are generated per beat and mapped into the Remotion project data in `core/interactive_director.py`

**Checkpoint**: At this point, User Story 1 is fully functional: multi-character stories generate distinct voices sequentially with aligned subtitles.

---

## Phase 4: User Story 2 - Fluid Continuous Video Animation from Keyframe Anchors (Priority: P1)

**Goal**: Eliminate rapid 16 fps strobe flickering of disconnected still images by switching ComfyUI workflows to native 3D temporal video latents (`EmptyHunyuanLatentVideo` / `WanImageToVideo`) and anchoring motion directly to approved storyboard keyframe images.

**Independent Test**: Generate a video beat starting from an approved keyframe image. Verify that the output video preserves the keyframe character and environment from frame 0 and animates continuously without strobe flickering or terminal frame freezing.

### Tests for User Story 2
- [X] T015 [P] [US2] Create unit test for ComfyUI Wan 2.1 temporal video latent workflow builder in `tests/unit/test_wan3_temporal_workflow.py`
- [X] T016 [P] [US2] Create unit test for safe $4k+1$ frame count and duration calculation in `tests/unit/test_runpod_serverless_pacing.py`

### Implementation for User Story 2
- [X] T017 [US2] Replace node `"6"` `EmptyLatentImage` with `EmptyHunyuanLatentVideo` (dimensions: width, height, length, batch_size=1) in `core/workflows/wan3_omni_reference.json`
- [X] T018 [US2] Update `build_wan3_workflow_payload()` in `core/runpod_client.py` to inject `length`, `width`, `height`, and connect reference keyframe image to image conditioning nodes
- [X] T019 [US2] Update `core/runpod_serverless.py` to compute safe $4k+1$ frame counts (17, 33, 49, 65, 81 frames at 16 fps) based on beat duration so motion extends across the entire spoken dialogue
- [X] T020 [US2] Update video synthesis dispatch in `core/interactive_director.py` to pass calculated frame counts and approved keyframe file paths to the RunPod client
- [X] T021 [US2] Add motion interpolation fallback (minterpolate) in `core/interactive_director.py` if rendered video is shorter than dialogue audio, ensuring zero terminal frame freezes

**Checkpoint**: User Stories 1 AND 2 are complete: videos animate smoothly from keyframe artwork without strobe flickers, and characters speak with unique voices.

---

## Phase 5: User Story 3 - Kinetic 4-Part Motion Prompting & Pacing Alignment (Priority: P2)

**Goal**: Author diffusion video prompts decomposed into four kinetic layers (subject action, secondary interaction, environmental physics, camera kinetics) and match scene duration to spoken dialogue pacing.

**Independent Test**: Inspect generated beat prompts to verify presence of all four kinetic layers. Verify that scene duration accommodates dialogue duration plus 0.5s breathing padding.

### Tests for User Story 3
- [X] T022 [P] [US3] Create unit test verifying 4-part kinetic prompt structure in `tests/unit/test_kinetic_prompt_structure.py`

### Implementation for User Story 3
- [X] T023 [US3] Update prompt authoring rules in `core/story_writer.py` to enforce the 4-part kinetic prompt structure: 1) Subject Action (seconds 0–4), 2) Secondary Interaction, 3) Environmental Physics, 4) Camera Movement
- [X] T024 [US3] Add duration calculation logic in `core/story_writer.py` calculating scene duration as estimated dialogue words / 2.5 + 0.8s breathing room
- [X] T025 [US3] Update `core/director_chat.py` AI Director modifications to preserve the 4-part kinetic motion formulation during user chat refinements

**Checkpoint**: Story generation produces action-driven diffusion prompts that synchronize seamlessly with spoken dialogue pacing.

---

## Phase 6: User Story 4 - Interactive Speaker & Voice Direction in Web Studio (Priority: P2)

**Goal**: Provide visual attribution badges on Web Studio cards, let creators preview and select character voice personas per card, and persist modifications via API.

**Independent Test**: Open Web Studio, inspect card speaker badges, change a character's voice persona in the dropdown, click Approve & Synthesize, and verify the resulting video uses the chosen voice persona.

### Tests for User Story 4
- [X] T026 [P] [US4] Create contract test for `PATCH /api/storyboard/beat` in `tests/unit/test_storyboard_beat_api.py`

### Implementation for User Story 4
- [X] T027 [US4] Implement `PATCH /api/storyboard/beat` in `core/server.py` to update card speaker, voice persona, dialogue text, or visual prompt in memory and persist to session JSON
- [X] T028 [US4] Add `updateStoryboardBeat()` API client method in `studio/src/services/api.ts`
- [X] T029 [US4] Add Speaker badge (e.g. `[Cow 1]`) and Voice Persona dropdown selector to `studio/src/components/BeatCard.tsx`
- [X] T030 [US4] Wire character voice persona changes in `studio/src/components/BeatCard.tsx` to call `updateStoryboardBeat()` with auto-save feedback

**Checkpoint**: Creators have full visual and directorial control over character voices and dialogue attribution directly in Web Studio.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end integration, regression verification, and validation scenarios

- [X] T031 [P] Create end-to-end integration test verifying master video compilation with multi-character audio in `tests/integration/test_multi_character_video_e2e.py`
- [X] T032 Execute full pytest suite (`pytest tests/unit/ tests/test_*.py`) to guarantee zero regressions across all 57+ existing tests
- [X] T033 Execute TypeScript build (`npm run build` in `studio/`) to verify clean frontend compilation
- [X] T034 Run validation scenarios A, B, C, and D from `specs/007-character-dialogue-motion-synthesis/quickstart.md`
- [X] T035 Update project documentation and feature release notes in `README.md`
