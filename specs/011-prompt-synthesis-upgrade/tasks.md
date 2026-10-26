# Implementation Tasks: Model-Aware Prompt Synthesis & Gemini Upgrade

**Feature**: `011-prompt-synthesis-upgrade`  
**Plan**: [plan.md](file:///Users/ashishkumavat/Projects/ai-text-to-video/specs/011-prompt-synthesis-upgrade/plan.md)  
**Spec**: [spec.md](file:///Users/ashishkumavat/Projects/ai-text-to-video/specs/011-prompt-synthesis-upgrade/spec.md)  

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Test scaffolding and environment readiness

- [x] T001 [P] Create test scaffolding in `tests/test_prompt_compiler.py` and `tests/test_negative_prompts.py`
- [x] T002 Verify google-genai and openai SDK dependencies in `core/config.py` and `requirements.txt`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core model entities, aliasing tables, and profile expansions required by all user stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 [P] Add `AudioSyntaxType`, `NegativePromptStrategy`, and `CompiledRenderPrompt` entities to `core/models.py`
- [x] T004 [P] Implement `LLM_MODEL_ALIASES` and `resolve_llm_model(model_name)` to forward-alias deprecated 2.5/2.0 Gemini models in `core/models.py`
- [x] T005 Expand `VideoModelProfile` dataclass with `audio_syntax`, `negative_prompt_strategy`, and provider endpoints/rates in `core/provider_registry.py`

**Checkpoint**: Foundation ready — user story implementation can proceed in parallel or prioritized sequence.

---

## Phase 3: User Story 1 - Latest Gemini Frontier Model Cascade (Priority: P1) 🎯 MVP

**Goal**: Upgrade story synthesis cascade to use `gemini-3.8-flash` as primary Tier 1 engine and alias deprecated 2.5 models seamlessly.

**Independent Test**: Execute `pytest tests/test_story_writer.py tests/test_gemini_key_chain.py` and verify `gemini-3.8-flash` is used as primary and legacy 2.5 requests alias without error.

### Tests for User Story 1
- [x] T006 [P] [US1] Unit test for Gemini 3.8 cascade ordering and legacy model aliasing in `tests/test_story_writer.py`

### Implementation for User Story 1
- [x] T007 [US1] Update `ModelCascadeConfig.gemini_models` default factory to place `gemini-3.8-flash` as Tier 1 in `core/models.py`
- [x] T008 [US1] Update `StoryWriterGateway.synthesize_story` to pass models through `resolve_llm_model` in `core/story_writer.py`
- [x] T009 [P] [US1] Update API verification probe to test `gemini-3.8-flash` in `core/api_verifier.py`
- [x] T010 [P] [US1] Update CLI help descriptions and interactive director chat defaults to `gemini-3.8-flash` in `core/cli.py` and `core/director_chat.py`

**Checkpoint**: At this point, User Story 1 is complete. Storyboard creation runs on Gemini 3.8 Flash with 100% backward compatibility.

---

## Phase 4: User Story 2 - Model-Specific Late-Stage Prompt Compilation (Priority: P1)

**Goal**: Eliminate premature `kling-v1.5` prompt budgeting at story generation; compile prompts at render execution time tailored to the active target model.

**Independent Test**: Execute `pytest tests/test_prompt_compiler.py` and verify prompt compilation dynamically formats for Wan 2.1, Kling, MiniMax H3, and Runway without changing storyboard records.

### Tests for User Story 2
- [x] T011 [P] [US2] Contract test validating prompt compilation schema against `specs/011-prompt-synthesis-upgrade/contracts/prompt_compiler_contract.json` in `tests/test_prompt_compiler.py`

### Implementation for User Story 2
- [x] T012 [US2] Remove premature hardcoded `adapt_prompt(model_id="kling-v1.5")` from `StoryWriterGateway._apply_aspect_ratio_styling` in `core/story_writer.py`
- [x] T013 [US2] Implement `PromptCompiler.compile_beat(...)` handling token budgeting, safe character truncation, and model audio syntax in `core/prompt_adapter.py`
- [x] T014 [US2] Integrate `PromptCompiler` into `route_and_execute_beat` at render execution time in `core/visual_router.py`
- [x] T015 [US2] Wire `PromptCompiler` into isolated single beat execution in `_render_single_beat_core` in `core/server.py`

**Checkpoint**: User Stories 1 and 2 are functional. Prompts adapt to any of the 41 models at the moment of generation.

---

## Phase 5: User Story 3 - Pure-Motion Kinetic Prompting for Image-to-Video Continuity (Priority: P2)

**Goal**: In I2V mode, strip static attire and scene descriptions to eliminate prompt fighting while preserving active object interactions.

**Independent Test**: Execute `pytest tests/test_prompt_adapter.py -k "kinetic"` and verify static descriptions are pruned while action verbs and prepositions remain.

### Tests for User Story 3
- [x] T016 [P] [US3] Unit test for kinetic action preposition preservation ("strikes with", "holding", "interacts with") in `tests/test_prompt_adapter.py`

### Implementation for User Story 3
- [x] T017 [US3] Refine kinetic regex patterns in `PromptAdapter._apply_kinetic_i2v_transform` to preserve action prepositions in `core/prompt_adapter.py`
- [x] T018 [US3] Add fallback motion vector injection ("slow atmospheric push-in, subtle ambient motion") when all prompt tokens are static in `core/prompt_adapter.py`

**Checkpoint**: User Story 3 complete. Image-to-Video generation no longer morphs faces or clothing.

---

## Phase 6: User Story 4 - Context-Aware Dynamic Negative Prompting (Priority: P2)

**Goal**: Replace static negative strings with dynamic negative prompts calibrated for photorealistic cinematic, 3D animation, and stylized riddles.

**Independent Test**: Execute `pytest tests/test_negative_prompts.py` and verify cinematic renders have 0 instances of `"realistic photography"` in negative prompts.

### Tests for User Story 4
- [x] T019 [P] [US4] Unit test for genre-aware negative prompt synthesis across cinematic and animated styles in `tests/test_negative_prompts.py`

### Implementation for User Story 4
- [x] T020 [US4] Implement `NegativePromptCompiler.build_negative_prompt(genre, art_style, strategy)` in `core/prompt_adapter.py`
- [x] T021 [US4] Replace hardcoded static negative prompt in RunPod serverless payload builder in `core/server.py`
- [x] T022 [US4] Wire dynamic negative prompt into multi-provider dispatch payloads in `core/visual_router.py` and `core/providers/fal_provider.py`

**Checkpoint**: User Story 4 complete. Photorealistic live-action renders are not degraded by contradictory negative tags.

---

## Phase 7: User Story 5 - Multi-Reference Character Consistency Across Hard Cuts (Priority: P3)

**Goal**: Bind character reference images into provider payloads for models supporting multi-reference inputs across hard cuts.

**Independent Test**: Execute `pytest tests/unit/test_multiframe_provider_payloads.py` and verify `reference_images` are passed up to model capacity.

### Tests for User Story 5
- [x] T023 [P] [US5] Unit test verifying reference image payload serialization in `tests/unit/test_multiframe_provider_payloads.py`

### Implementation for User Story 5
- [x] T024 [US5] Update `route_and_execute_beat` in `core/visual_router.py` to extract `ImageRole.CHARACTER_IMAGE` assets into `reference_images` when `supports_reference_images=True`
- [x] T025 [US5] Update provider adapters (`core/providers/fal_provider.py`, `core/providers/apidot_provider.py`, `core/providers/kie_provider.py`) to serialize reference images using `profile.reference_param_name`

**Checkpoint**: User Story 5 complete. Character identity remains consistent across camera angle cuts.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Verification, documentation updates, and regression testing

- [x] T026 [P] Update model documentation and examples in `README.md`
- [x] T027 Run full test suite across story writer, prompt compiler, and negative prompts (`pytest tests/`)
- [x] T028 Validate end-to-end Studio execution via `quickstart.md` validation scenarios

---

## Dependencies & Execution Order

```
Phase 1: Setup (T001, T002)
       │
       ▼
Phase 2: Foundational (T003, T004, T005) ──► BLOCKS all stories
       │
       ├────────────────────────────────────────┐
       ▼                                        ▼
Phase 3: US1 - Gemini 3.8 (T006-T010) [MVP]  Phase 4: US2 - Late Prompt Compiler (T011-T015)
       │                                        │
       ▼                                        ▼
Phase 5: US3 - Kinetic I2V (T016-T018)       Phase 6: US4 - Dynamic Negatives (T019-T022)
       │                                        │
       └───────────────────┬────────────────────┘
                           ▼
Phase 7: US5 - Multi-Reference Consistency (T023-T025)
                           │
                           ▼
Phase 8: Polish & Regression Testing (T026-T028)
```

---

## Parallel Execution Examples

### Parallel Example: User Story 1
```bash
# Launch test and implementation tasks concurrently:
Task: "T006 [P] [US1] Unit test for Gemini 3.8 cascade ordering in tests/test_story_writer.py"
Task: "T009 [P] [US1] Update API verification probe in core/api_verifier.py"
Task: "T010 [P] [US1] Update CLI help descriptions in core/cli.py"
```

### Parallel Example: User Story 2 & 4
```bash
# Launch contract and unit tests concurrently:
Task: "T011 [P] [US2] Contract test in tests/test_prompt_compiler.py"
Task: "T019 [P] [US4] Unit test in tests/test_negative_prompts.py"
```

---

## Implementation Strategy

1. **MVP First (User Story 1)**:
   - Complete Phase 1 (Setup) and Phase 2 (Foundational).
   - Implement Phase 3 (Gemini 3.8 Flash Upgrade).
   - Verify immediately via `pytest tests/test_story_writer.py`.
2. **Incremental Delivery**:
   - Deliver Phase 4 (Late-Stage Prompt Compilation) $\rightarrow$ Eliminates premature Kling formatting.
   - Deliver Phase 5 (Kinetic I2V) & Phase 6 (Dynamic Negatives) $\rightarrow$ Eliminates prompt fighting and raises First-Take Yield.
   - Deliver Phase 7 (Multi-Reference Binding) $\rightarrow$ Enables cross-cut character consistency.
3. **Zero-Reroll Quality**: Every task validates against the Anti-Reroll Cost Efficiency principle in the Constitution.
