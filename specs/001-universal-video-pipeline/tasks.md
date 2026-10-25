# Tasks: Universal Multi-Genre Video Generation Pipeline

**Feature Branch**: `001-universal-video-pipeline`  
**Input**: [spec.md](file:///Users/ashishkumavat/Projects/ai-text-to-video/specs/001-universal-video-pipeline/spec.md), [plan.md](file:///Users/ashishkumavat/Projects/ai-text-to-video/specs/001-universal-video-pipeline/plan.md), [data-model.md](file:///Users/ashishkumavat/Projects/ai-text-to-video/specs/001-universal-video-pipeline/data-model.md), [contracts/](file:///Users/ashishkumavat/Projects/ai-text-to-video/specs/001-universal-video-pipeline/contracts/)  

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, directory structure, and foundational dependency configurations.

- [X] T001 Create project directory structure (`core/`, `remotion/`, `assets/`, `outputs/`, `tests/`) per implementation plan
- [X] T002 [P] Initialize Python dependencies configuration in `requirements.txt` (`pydantic>=2.7`, `edge-tts>=6.1`, `faster-whisper>=1.0`, `pillow`, `opencv-python`, `requests`, `websockets`, `pytest`)
- [X] T003 [P] Initialize Remotion project configuration in `remotion/package.json`, `remotion/tsconfig.json`, and `remotion/remotion.config.ts`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models, audio synthesis, GPU client, and Remotion shared UI components that MUST be complete before ANY user story can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 [P] Implement Pydantic v2 data models for all core entities in `core/models.py` (`VideoProject`, `StoryboardBeat`, `ImageAsset`, `ContinuityLink`, `CharacterProfile`, `SubtitleTrack`, `AudioAsset`, `RenderOutput`)
- [X] T005 [P] Implement Audio Engine (Edge-TTS voice synthesis + Faster-Whisper word-level timestamp extraction) in `core/audio_engine.py`
- [X] T006 [P] Implement Sound Effects Mixer and speech-level volume ducking in `core/sfx_mixer.py`
- [X] T007 [P] Implement RunPod ComfyUI REST/WebSocket client for remote GPU dispatch in `core/runpod_client.py`
- [X] T008 [P] Implement Tail-to-Head Frame Extractor (`Frame -1 ➔ Frame 0`) in `core/chain_manager.py`
- [X] T009 Implement Tri-Strategy Anti-Reroll Visual Routing Engine in `core/visual_router.py`
- [X] T010 Scaffold Remotion root composition and types in `remotion/src/Root.tsx` and `remotion/src/types.ts`
- [X] T011 [P] Implement reusable Kinetic Word-by-Word Subtitles component in `remotion/src/components/KineticSubtitles.tsx`
- [X] T012 [P] Implement reusable AudioMixer with automatic speech ducking in `remotion/src/components/AudioMixer.tsx`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Multi-Genre Content Generation from Prompt (Priority: P1) 🎯 MVP

**Goal**: Core end-to-end orchestration accepting a prompt or manifest, synthesizing audio with timestamps, routing scenes, compiling in Remotion, and exporting a finished vertical MP4.

**Independent Test**: Provide a prompt or manifest, run `python -m core.pipeline`, and verify a complete 1080x1920 MP4 is produced with audio, synchronized kinetic captions, and sequenced video clips.

### Tests for User Story 1 ⚠️
- [X] T013 [P] [US1] Create unit tests for director manifest parsing and validation against schema in `tests/unit/test_manifest.py`
- [X] T014 [P] [US1] Create unit tests for audio engine and whisper alignment in `tests/unit/test_audio_engine.py`

### Implementation for User Story 1
- [X] T015 [US1] Implement LLM Director engine for Autonomous Prompt-to-Storyboard deconstruction in `core/director.py`
- [X] T016 [US1] Implement Directed Studio Mode manifest parser & validator in `core/manifest_parser.py`
- [X] T017 [US1] Implement Remotion render props bridge (translates `VideoProject` to Remotion JSON payload) in `core/remotion_bridge.py`
- [X] T018 [US1] Implement main pipeline orchestrator CLI in `core/pipeline.py`
- [X] T019 [US1] Implement Remotion Master Composition timeline sequencer (`<Series>` of scenes) in `remotion/src/Composition.tsx`
- [X] T020 [US1] Integration test: End-to-end validation of basic prompt-to-MP4 flow in `tests/integration/test_mvp_pipeline.py`

**Checkpoint**: At this point, User Story 1 is fully functional and testable as an MVP!

---

## Phase 4: User Story 2 - Interactive Brain Teasers and Riddles (Priority: P2)

**Goal**: Zero-hallucination programmatic riddle pipeline (Strategy 1 & 2) with rock-solid static plates, 7-second countdown dial with tick sound, and transparent sprite/interpolation solution reveal.

**Independent Test**: Run `python -m core.pipeline --manifest specs/001-universal-video-pipeline/examples/riddle_manifest.json` and verify 0% wood-grain shift, animated countdown clock, and transparent pouring arm.

### Tests for User Story 2 ⚠️
- [X] T021 [P] [US2] Create unit test for SpriteLayer keyframing and transparency verification in `tests/unit/test_sprites.py`

### Implementation for User Story 2
- [X] T022 [P] [US2] Implement SVG Radial Countdown Dial component with frame-accurate tick sounds in `remotion/src/components/CountdownDial.tsx`
- [X] T023 [P] [US2] Implement SpriteLayer component with alpha-channel animation in `remotion/src/components/SpriteLayer.tsx`
- [X] T024 [US2] Implement RiddleTemplate composition (Question plate ➔ Countdown dial ➔ Reveal sequence) in `remotion/src/templates/RiddleTemplate.tsx`
- [X] T025 [US2] Create sample riddle manifest with stationary plate and clean sprites in `specs/001-universal-video-pipeline/examples/riddle_manifest.json`
- [X] T026 [US2] Integration test: Verify deterministic riddle video generation without background distortion in `tests/integration/test_riddle_flow.py`

**Checkpoint**: At this point, User Stories 1 AND 2 both work independently.

---

## Phase 5: User Story 3 - Character Consistency in Cartoons & Narrative Stories (Priority: P3)

**Goal**: Narrative storytelling with consistent character identity, expressive emotion, and dialogue pacing using user reference images and RunPod ComfyUI I2V/IP-Adapter.

**Independent Test**: Generate a 3-scene story with a character reference image and verify facial/costume identity is preserved across all cuts.

### Implementation for User Story 3
- [X] T027 [P] [US3] Implement ComfyUI workflow template for IP-Adapter Character Consistency in `core/workflows/comfy_character_i2v.json`
- [X] T028 [US3] Implement Character Profile manager and prompt injector in `core/character_manager.py`
- [X] T029 [US3] Implement StoryTemplate composition (narrative transitions, letterboxing, emotional color grading) in `remotion/src/templates/StoryTemplate.tsx`
- [X] T030 [US3] Create sample story manifest with character reference image in `specs/001-universal-video-pipeline/examples/story_studio_manifest.json`
- [X] T031 [US3] Integration test: Verify multi-scene story generation with character reference anchoring in `tests/integration/test_story_flow.py`

**Checkpoint**: User Stories 1, 2, and 3 are all independently functional.

---

## Phase 6: User Story 4 - High-Octane Action & Dynamic Motion Sequencing (Priority: P4)

**Goal**: Fast-paced action sequences with dynamic camera movements, impact sound design, screen shake, and Tail-to-Head Frame Chaining for seamless continuity.

**Independent Test**: Run a 2-clip combat action sequence and verify that Frame -1 of Clip 1 is passed as Frame 0 to Clip 2 with zero jump cut.

### Implementation for User Story 4
- [X] T032 [P] [US4] Implement camera shake and impact flash effects component in `remotion/src/components/ImpactEffects.tsx`
- [X] T033 [US4] Implement ActionTemplate composition (dynamic cuts, screen shake, speed ramping) in `remotion/src/templates/ActionTemplate.tsx`
- [X] T034 [US4] Wire `chain_manager.py` into `pipeline.py` to automate Tail-to-Head Frame Chaining between consecutive action shots
- [X] T035 [US4] Create sample action manifest with sequential frame chaining in `specs/001-universal-video-pipeline/examples/action_manifest.json`
- [X] T036 [US4] Integration test: Verify Tail-to-Head Frame Chaining continuity in `tests/integration/test_action_chaining.py`

**Checkpoint**: All 4 user stories are functional and verified.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: CLI usability, caching, documentation, and quickstart verification.

- [X] T037 [P] Implement unified CLI interface with rich console progress logging in `core/cli.py`
- [X] T038 [P] Implement intermediate artifact cleanup and cache management in `core/cache.py`
- [X] T039 Execute and validate all scenarios in `specs/001-universal-video-pipeline/quickstart.md`
- [X] T040 Finalize documentation and architecture diagrams in `README.md`

---

## Dependencies & Execution Order

### Phase Dependencies
1. **Setup (Phase 1)**: Can start immediately.
2. **Foundational (Phase 2)**: Depends on Phase 1. Blocks all User Stories.
3. **User Stories (Phases 3–6)**: Depend on Phase 2. Can be developed sequentially (P1 ➔ P2 ➔ P3 ➔ P4) or in parallel.
4. **Polish (Phase 7)**: Depends on target user stories being complete.

### Parallel Opportunities
- In Phase 1: `T002` and `T003` can run in parallel.
- In Phase 2: `T004`, `T005`, `T006`, `T007`, `T008`, `T011`, and `T012` can run in parallel.
- In Phase 3 (US1): `T013` and `T014` can run in parallel.
- In Phase 4 (US2): `T021`, `T022`, and `T023` can run in parallel.
- In Phase 5 (US3): `T027` and `T029` can run in parallel.
- In Phase 6 (US4): `T032` can run in parallel with template scaffolding.

---

## Implementation Strategy (MVP First)

1. **Step 1**: Complete Phase 1 (Setup) and Phase 2 (Foundational).
2. **Step 2**: Complete Phase 3 (User Story 1 - MVP).
3. **Step 3**: Validate MVP with a 1-shot vertical video test using `core/pipeline.py`.
4. **Step 4**: Progressively deliver User Story 2 (Riddles), User Story 3 (Stories), and User Story 4 (Action).
