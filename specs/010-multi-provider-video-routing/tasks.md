# Tasks: Multi-Provider Video Routing with Dynamic Cost Arbitrage & Multimodal Generation

**Feature Branch**: `010-multi-provider-video-routing`
**Date**: 2026-10-25
**Plan**: [plan.md](file:///Users/ashishkumavat/Projects/ai-text-to-video/specs/010-multi-provider-video-routing/plan.md)
**Spec**: [spec.md](file:///Users/ashishkumavat/Projects/ai-text-to-video/specs/010-multi-provider-video-routing/spec.md)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, directory structure, and shared dependencies.

- [X] T001 Create providers package directory structure in `core/providers/__init__.py`
- [X] T002 [P] Install and verify async HTTP client and testing dependencies in `requirements.txt`
- [X] T003 [P] Configure provider API environment keys (`FAL_KEY`, `APIDOT_API_KEY`, `KIE_API_KEY`) in `.env.example`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models, base provider abstract interface, and static documentation link bank.

**⚠️ CRITICAL**: Must be completed before any user story implementation begins.

- [X] T004 Implement domain enums and Pydantic schemas (`ProviderId`, `VideoModelProfile`, `ProviderPriceQuote`, `RenderingJobTicket`) in `core/models.py`
- [X] T005 [P] Implement abstract class `BaseVideoProvider` interface and custom provider exceptions in `core/providers/base_provider.py`
- [X] T006 [P] Implement official documentation link bank, pricing links, and failure insurance registry in `core/provider_registry.py`
- [X] T007 [P] Implement version-bound model profiles and character limit catalogs in `core/provider_registry.py`

**Checkpoint**: Foundation ready. User story implementation can now begin.

---

## Phase 3: User Story 1 - Dynamic Lowest-Cost Provider Routing & Pre-Flight Cost Audit (Priority: P1) 🎯 MVP

**Goal**: Inspect live quotes across fal.ai, apidot.ai, and kie.ai, route rendering to the cheapest verified provider, and auto-cascade with zero-cost guarantee on failure.

**Independent Test**: Can be tested via `pytest tests/test_cost_arbitrage.py` - validates rate queries, cheapest provider selection, and zero-cost failover.

### Tests for User Story 1
- [X] T008 [P] [US1] Create unit and mock tests for provider rate comparison and cheapest selection in `tests/test_cost_arbitrage.py`
- [X] T009 [P] [US1] Create unit tests for provider infrastructure failure (5xx) and zero-cost cascade in `tests/test_provider_failure_cascade.py`

### Implementation for User Story 1
- [X] T010 [P] [US1] Implement `FalProvider` adapter with async job polling and zero-cost error handling in `core/providers/fal_provider.py`
- [X] T011 [P] [US1] Implement `ApidotProvider` adapter with unified task polling and credit refund validation in `core/providers/apidot_provider.py`
- [X] T012 [P] [US1] Implement `KieProvider` adapter with task creation and status tracking in `core/providers/kie_provider.py`
- [X] T013 [P] [US1] Implement `ServerlessProvider` adapter wrapping existing Channel 1 RunPod execution in `core/providers/serverless_provider.py`
- [X] T014 [US1] Implement dynamic cost calculation, TTL quote caching (10 min), and lowest-cost ranking in `core/cost_arbitrage.py`
- [X] T015 [US1] Update `core/visual_router.py` to route Channel 2 beats through `core/cost_arbitrage.py` with automatic provider failover cascade

**Checkpoint**: At this point, User Story 1 is fully functional and delivers an independently testable MVP.

---

## Phase 4: User Story 2 - Model-Aware Prompt Adaptation & Character Limit Budgeting (Priority: P1)

**Goal**: Automatically compress and format scene prompts within target model version character and token limits without mutating narrative plot or actions.

**Independent Test**: Can be tested via `pytest tests/test_prompt_adapter.py` - verifies that prompts exceeding limits (e.g. 1,800 chars on Runway 1,000 char limit) are compressed safely.

### Tests for User Story 2
- [X] T016 [P] [US2] Create unit tests for model prompt length budgeting and semantic compression in `tests/test_prompt_adapter.py`

### Implementation for User Story 2
- [X] T017 [US2] Implement model-aware prompt analyzer and semantic compression logic in `core/prompt_adapter.py`
- [X] T018 [US2] Integrate token boundary budgeting for open-weights models (Wan 2.1, CogVideoX, Hunyuan) in `core/prompt_adapter.py`
- [X] T019 [US2] Connect prompt adaptation into the director generation pipeline in `core/story_writer.py`

**Checkpoint**: User Stories 1 and 2 work together; prompts never exceed model limits or get rejected.

---

## Phase 5: User Story 3 - Multimodal Generation (T2V, I2V, Dual Frame Pinning) (Priority: P2)

**Goal**: Support Text-to-Video, Image-to-Video (kinetic motion prompting), and First/Last frame transition interpolation.

**Independent Test**: Can be tested via `pytest tests/test_multimodal_router.py` - verifies motion-only prompt generation for I2V and anchor frame passing.

### Tests for User Story 3
- [X] T020 [P] [US3] Create tests for I2V motion prompt generation (suppression of static element descriptions) in `tests/test_multimodal_router.py`

### Implementation for User Story 3
- [X] T021 [US3] Implement motion prompt formula (`[Camera Vector] + [Subject Action] + [Environmental Kinetics]`) in `core/prompt_adapter.py`
- [X] T022 [US3] Update provider adapters (`fal_provider.py`, `apidot_provider.py`, `kie_provider.py`) to pass `start_frame` and `end_frame` assets
- [X] T023 [US3] Add multi-reference asset attachment (Seedance 2.0/2.5 reference images/videos) in `core/providers/`

**Checkpoint**: Multimodal generation works across T2V, I2V, and dual-frame interpolation.

---

## Phase 6: User Story 4 - Native Clip Audio Integration & Remotion Mastering Bypass (Priority: P2)

**Goal**: Inject dialogue tags/Foley when Audio is ON, and bypass Remotion synthetic voiceovers to prevent audio collisions on native audio clips.

**Independent Test**: Can be tested via `pytest tests/test_remotion_audio_bypass.py` - verifies that clips with embedded audio mute external TTS voiceover and duck background music.

### Tests for User Story 4
- [X] T024 [P] [US4] Create unit tests for Remotion audio props generation and bypass detection in `tests/test_remotion_audio_bypass.py`

### Implementation for User Story 4
- [X] T025 [US4] Implement model-specific audio tag injection (`<d>...</d>` for MiniMax, spoken cues for Kling/Seedance/Veo) in `core/prompt_adapter.py`
- [X] T026 [US4] Update Remotion bridge in `core/remotion_bridge.py` to inspect clip audio metadata and set `hasClipAudio: true`
- [X] T027 [P] [US4] Update Remotion TypeScript types in `remotion/src/types.ts` to add `hasClipAudio` and `audioVolume` to `SceneConfig`
- [X] T028 [US4] Update Remotion composition in `remotion/src/Composition.tsx` to un-mute `<Video />` when `hasClipAudio` is active
- [X] T029 [US4] Update Remotion audio mixer in `remotion/src/components/AudioMixer.tsx` to suppress synthetic voiceovers during native audio scenes

**Checkpoint**: Native clip audio plays with perfect fidelity; zero audio collisions or double-talking.

---

## Phase 7: User Story 5 - Real-Time Cost Transparency & Sensitive Provider Insights in Web Studio (Priority: P3)

**Goal**: Expose live comparison table of provider quotes, character limits, official docs links, and zero-cost failure guarantee badges in the Web Studio UI.

**Independent Test**: Can be tested by opening the Studio UI on port 5173, inspecting the Cost Insights modal and beat card badges.

### Implementation for User Story 5
- [X] T030 [P] [US5] Implement FastAPI endpoint `GET /api/providers/registry` in `core/server.py`
- [X] T031 [P] [US5] Implement FastAPI endpoint `GET /api/providers/models` in `core/server.py`
- [X] T032 [P] [US5] Implement FastAPI endpoint `POST /api/providers/quotes` in `core/server.py`
- [X] T033 [P] [US5] Implement frontend API service calls for provider registry and live quotes in `studio/src/services/api.ts`
- [X] T034 [US5] Create `CostTransparencyModal.tsx` in `studio/src/components/CostTransparencyModal.tsx` displaying live quotes, official links, and zero-cost badges
- [X] T035 [US5] Update `BeatCard.tsx` in `studio/src/components/BeatCard.tsx` with model selector, modality toggle (T2V/I2V), audio toggle, and character limit counter

**Checkpoint**: Studio creators have complete visual transparency over costs, provider selection, and prompt constraints.

---

## Phase 8: User Story 6 - Video Extending & On-Demand Video Upscaling (Priority: P3)

**Goal**: Enable incremental video extension (+4s/+5s continuation) and 4K super-resolution upscaling (Topaz / Real-ESRGAN).

**Independent Test**: Can be tested by extending a 5s clip and confirming incremental billing, plus verifying 4K upscaler invocation.

### Implementation for User Story 6
- [X] T036 [P] [US6] Implement video extending endpoints in provider adapters (`fal_provider.py`, `kie_provider.py`) in `core/providers/`
- [X] T037 [P] [US6] Implement Topaz Video AI and Real-ESRGAN upscaling workflows in `core/video_upscaler.py`
- [X] T038 [US6] Add FastAPI endpoints `POST /api/render/extend-job` and `POST /api/render/upscale-job` in `core/server.py`
- [X] T039 [US6] Add "Extend Video" and "4K Upscale" actions to `studio/src/components/BeatCard.tsx` and export pane

**Checkpoint**: All 6 user stories are fully implemented and integrated.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end validation, performance optimization, and cleanup.

- [X] T040 Run end-to-end validation scenarios documented in `specs/010-multi-provider-video-routing/quickstart.md`
- [X] T041 [P] Verify type safety and run static analysis across `core/` and `studio/`
- [X] T042 Verify zero-cost failure verification against mock 500 error responses
- [X] T043 Update project documentation and architecture guide in `README.md`

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (Phase 1)**: Can start immediately.
- **Foundational (Phase 2)**: Depends on Setup (T001-T003) - BLOCKS all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational (T004-T007). Delivers MVP.
- **User Story 2 (Phase 4)**: Depends on Foundational. Integrates with US1.
- **User Story 3 (Phase 5)**: Depends on US1 and US2.
- **User Story 4 (Phase 6)**: Depends on US1 and US3.
- **User Story 5 (Phase 7)**: Depends on US1, US2, US4.
- **User Story 6 (Phase 8)**: Depends on US1, US3.
- **Polish (Phase 9)**: Depends on all user story phases.

### Parallel Opportunities
- In Phase 1: T002 and T003 can run in parallel.
- In Phase 2: T005, T006, and T007 can run in parallel.
- In Phase 3: All 4 provider adapters (T010, T011, T012, T013) can be written in parallel.
- In Phase 6: Frontend Remotion types (T027) can be written in parallel with backend bridge updates (T026).
- In Phase 7: REST API endpoints (T030-T032) and frontend service definitions (T033) can be written in parallel.

---

## Implementation Strategy: MVP First

1. **Step 1**: Complete Setup (Phase 1) & Foundational (Phase 2).
2. **Step 2**: Implement User Story 1 (Phase 3) - Core provider adapters, cost arbitrage, and visual router.
3. **Step 3**: Validate MVP with `pytest tests/test_cost_arbitrage.py` - Proves lowest-cost routing works end-to-end.
4. **Step 4**: Incrementally deliver User Story 2 (Prompt Adapter), User Story 3 (Multimodal), User Story 4 (Remotion Audio Bypass), User Story 5 (Studio UI), and User Story 6 (Extending & Upscaling).
