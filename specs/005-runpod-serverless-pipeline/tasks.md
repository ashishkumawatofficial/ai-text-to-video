# Tasks: RunPod Serverless Parallel Video Pipeline

**Feature Branch**: `005-runpod-serverless-pipeline`  
**Input**: Feature specification from `specs/005-runpod-serverless-pipeline/spec.md` and architecture from `specs/005-runpod-serverless-pipeline/plan.md`  

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Environment variable configuration and project foundation for RunPod Serverless.

- [x] T001 Add `RUNPOD_SERVERLESS_ENDPOINT_ID` and `MAX_SERVERLESS_CONCURRENCY` helpers to `core/config.py`
- [x] T002 Add serverless configuration defaults and comments to `.env.example`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models, schemas, and base HTTP client that MUST be complete before ANY user story can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T003 Create `BackendExecutionStrategy`, `ServerlessJobStatus`, `ServerlessJob`, `ServerlessConfig`, and `ServerlessCostReport` models in `core/models.py`
- [x] T004 Implement base `RunPodServerlessClient` class with endpoint URL resolution and authentication headers in `core/runpod_serverless.py`
- [x] T005 Implement polymorphic output media parser (supporting both HTTP download URLs and base64 video payloads) in `core/runpod_serverless.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Parallel Multi-Beat Serverless Diffusion (Priority: P1) 🎯 MVP

**Goal**: Enable all narrative beats in a video storyboard to dispatch concurrently across independent cloud serverless workers, reducing turnaround time from ~40 minutes to under 3 minutes.

**Independent Test**: Execute a multi-beat project with `--backend serverless`; verify all beats run concurrently, all MP4 slices download to local cache, and Remotion compiles the master video without dropped frames.

### Tests for User Story 1 ⚠️

- [x] T006 [P] [US1] Unit test for Serverless client submission (`/run`) and polling (`/status`) in `tests/test_runpod_serverless.py`
- [x] T007 [P] [US1] Unit test for payload decoding (base64 vs URL stream) in `tests/test_runpod_serverless.py`

### Implementation for User Story 1

- [x] T008 [US1] Implement `run_job()` and `poll_job()` methods with exponential backoff in `core/runpod_serverless.py`
- [x] T009 [US1] Implement `dispatch_parallel_beats()` orchestrator with `asyncio.Semaphore` concurrency limiting in `core/runpod_serverless.py`
- [x] T010 [US1] Integrate `dispatch_parallel_beats()` into `InteractiveDirector.synthesize_video()` in `core/interactive_director.py`
- [x] T011 [US1] Integration test verifying concurrent serverless beat collection and Remotion props generation in `tests/integration/test_serverless_flow.py`

**Checkpoint**: At this point, User Story 1 is fully functional and delivers the core 10x speedup MVP independently.

---

## Phase 4: User Story 2 - Resilient Dual-Backend Routing & Auto-Failover (Priority: P2)

**Goal**: Seamlessly route visual generation between Serverless, Dedicated Pod, and Local Mock, with automatic failover if Serverless experiences capacity limits or cold start spikes.

**Independent Test**: Simulate an unavailable serverless endpoint; verify the system automatically falls back to the dedicated pod or local keyframe engine without crashing.

### Tests for User Story 2 ⚠️

- [x] T012 [P] [US2] Unit test for multi-tier visual routing and automatic failover cascade in `tests/test_visual_router.py`

### Implementation for User Story 2

- [x] T013 [US2] Update `route_and_execute_beat()` in `core/visual_router.py` to support `SERVERLESS`, `DEDICATED_POD`, and `LOCAL_MOCK` with automatic cascading
- [x] T014 [US2] Add `--backend` CLI parameter (`[auto, serverless, pod, local]`) to `direct` and `render` commands in `core/cli.py`
- [x] T015 [US2] Wire `--backend` option through `DirectPipeline` and `InteractiveDirector` in `core/pipeline.py` and `core/interactive_director.py`

**Checkpoint**: At this point, User Stories 1 AND 2 work independently with full cloud resilience.

---

## Phase 5: User Story 3 - Multi-Worker Live Progress Telemetry & Safe Cancellation (Priority: P2)

**Goal**: Display real-time progress for all concurrent cloud workers in the terminal and guarantee clean cloud job cancellation on `Ctrl+C` to prevent orphaned GPU billing.

**Independent Test**: Launch a multi-worker job and press `Ctrl+C`; verify that cloud cancellation requests are immediately dispatched to all active worker job IDs.

### Tests for User Story 3 ⚠️

- [x] T016 [P] [US3] Unit test for SIGINT signal trapping and batch cloud cancellation in `tests/test_runpod_serverless.py`

### Implementation for User Story 3

- [x] T017 [US3] Implement `cancel_job()` and `cancel_batch()` cloud cancellation methods in `core/runpod_serverless.py`
- [x] T018 [US3] Implement async signal interception handler to trigger `cancel_batch()` on user interrupt (`Ctrl+C`) in `core/runpod_serverless.py`
- [x] T019 [US3] Implement compact multi-worker terminal status display showing per-beat worker lifecycle states in `core/runpod_serverless.py`

**Checkpoint**: User Story 3 delivers real-time observability and wallet credit protection.

---

## Phase 6: User Story 4 - Cost Tracking & Per-Video Billing Transparency (Priority: P3)

**Goal**: Calculate exact compute seconds across all workers and report the precise dollar cost of each video generation run.

**Independent Test**: Complete a serverless generation; verify the summary displays total worker seconds and calculated USD cost matching the active GPU tier rate.

### Tests for User Story 4 ⚠️

- [x] T020 [P] [US4] Unit test for compute duration aggregation and cost report calculation in `tests/test_runpod_serverless.py`

### Implementation for User Story 4

- [x] T021 [US4] Implement `generate_cost_report()` in `core/runpod_serverless.py` calculating cumulative GPU seconds and USD cost
- [x] T022 [US4] Add financial summary banner display to the final CLI output in `core/cli.py`

**Checkpoint**: All user stories are independently functional and verified.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, regression validation, and final end-to-end verification.

- [x] T023 [P] Update `README.md` with `--backend` usage guide and serverless configuration instructions
- [x] T024 Run full test suite regression across all 39 existing unit and integration tests (`pytest tests/`)
- [x] T025 Execute end-to-end quickstart validation scenario in `specs/005-runpod-serverless-pipeline/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - US1 (P1 MVP): Core parallel execution (Top Priority)
  - US2 (P2): Resilient backend routing & auto-failover
  - US3 (P2): Live progress telemetry & cancellation
  - US4 (P3): Cost tracking & financial accounting
- **Polish (Phase 7)**: Depends on completion of desired user stories

### Parallel Opportunities

- T006 and T007 (US1 unit tests) can be developed in parallel with model definitions.
- T012 (US2 test), T016 (US3 test), and T020 (US4 test) can be authored in parallel.
- Documentation updates (T023) can run in parallel with final verification (T024, T025).

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Complete Phase 1: Setup (`core/config.py`, `.env.example`)
2. Complete Phase 2: Foundational (`core/models.py`, `core/runpod_serverless.py`)
3. Complete Phase 3: User Story 1 (`run_job`, `dispatch_parallel_beats`, `synthesize_video`)
4. **VALIDATE MVP**: Verify parallel 4-beat generation in under 180 seconds.

### Incremental Delivery
1. Add User Story 2 (Failover & `--backend` flag) ➔ Test cloud resilience
2. Add User Story 3 (Live telemetry & `Ctrl+C` cancellation) ➔ Test wallet credit safety
3. Add User Story 4 (Cost accounting) ➔ Test billing report accuracy
4. Complete Polish & full regression suite
