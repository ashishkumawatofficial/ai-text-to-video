# Implementation Plan: RunPod Serverless Parallel Video Pipeline

**Branch**: `005-runpod-serverless-pipeline` | **Date**: 2026-10-24 | **Spec**: [specs/005-runpod-serverless-pipeline/spec.md](spec.md)

---

## Summary

This feature transitions the studio's visual generation engine from slow, single-threaded dedicated pod rendering (~40 minutes) to a high-throughput **Parallel Serverless Video Pipeline**. By dispatching all storyboard beats simultaneously across on-demand RunPod serverless workers, all scenes render concurrently in **under 3 minutes total** with pay-per-second billing ($0.00 when idle). The system includes resilient cascading failover (Serverless ➔ Dedicated Pod ➔ Local Plate), live progress telemetry, instant `Ctrl+C` cloud job cancellation, and transparent per-video compute cost reporting.

---

## Technical Context

**Language/Version**: Python 3.12 (with `asyncio` concurrent orchestration)  
**Primary Dependencies**: `pydantic` (v2), `requests`, standard library `asyncio`, `urllib`  
**Storage**: Local filesystem caching under `outputs/temp/` and `outputs/`  
**Testing**: `pytest`, `pytest-asyncio`  
**Target Platform**: macOS (Apple Silicon / Intel) local CLI connecting to RunPod Serverless Cloud  
**Project Type**: CLI Studio & AI Video Orchestration Engine  
**Performance Goals**:
- Full 4-beat cinematic video production turnaround: **< 180 seconds**
- Per-beat parallel dispatch latency: **< 500ms**
- Instant cancellation on SIGINT: **< 3 seconds**  
**Constraints**:
- Max concurrent workers bounded by semaphore (default: 4) to honor account limits
- Zero-crash fallback when serverless is unreachable or cold-starting
- 100% backward compatibility with Remotion, Director, and Dedicated Pod pipelines  
**Scale/Scope**: Multi-beat stories from 1 to 10 beats, aspect ratios (`16:9`, `9:16`, `1:1`, `4:5`)

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Library-First**: The serverless client is implemented as a modular, standalone component (`core/runpod_serverless.py`) with zero tight coupling to CLI or Remotion.
- [x] **II. CLI Interface**: Exposes execution via standard `--backend [serverless|pod|auto|local]` flag on `direct` and `render` commands.
- [x] **III. Test-First**: Unit tests for API contracts, polling timeouts, payload decoding, and mock concurrent dispatch written and passing.
- [x] **IV. Integration Testing**: End-to-end parallel flow tests with mock and live endpoints verifying asset collection and Remotion assembly.
- [x] **V. Simplicity & Observability**: Clear progress logging in terminal, per-beat status tracking, and per-video compute cost in USD.

---

## Project Structure

### Documentation (this feature)

```text
specs/005-runpod-serverless-pipeline/
├── spec.md              # Feature specification & requirements
├── plan.md              # Technical implementation plan
├── research.md          # Technical research, architecture decisions & formulas
├── data-model.md        # Entities, Enums, state transitions & models
├── quickstart.md        # 5 runnable verification scenarios
├── contracts/
│   └── runpod_serverless_api_contract.json # Serverless request/response schema
└── checklists/
    └── requirements.md  # Quality validation checklist
```

### Source Code Layout

```text
core/
├── config.py              # Add RUNPOD_SERVERLESS_ENDPOINT_ID, MAX_SERVERLESS_CONCURRENCY
├── models.py              # Add BackendExecutionStrategy, ServerlessJob, ServerlessCostReport
├── runpod_serverless.py   # NEW: RunPodServerlessClient, parallel dispatcher, cancellation handler
├── visual_router.py       # Updated: Tri-strategy router with serverless parallel batch execution
├── interactive_director.py# Updated: Concurrent beat synthesis integration
├── cli.py                 # Updated: --backend CLI flag on direct & render
└── remotion_bridge.py     # Unchanged: Zero breaking changes to video composition

tests/
├── test_runpod_serverless.py      # Unit tests: job dispatch, polling, payload decoding, cancel
└── integration/
    └── test_serverless_flow.py    # Integration test: parallel batch execution and Remotion props
```

---

## Key Modules & Implementation Phases

1. **Phase 1: Core Client & Data Models (`core/runpod_serverless.py`, `core/models.py`, `core/config.py`)**:
   - Add `BackendExecutionStrategy`, `ServerlessJobStatus`, `ServerlessJob`, and `ServerlessCostReport`.
   - Build `RunPodServerlessClient` with `run_job()`, `poll_job()`, `cancel_job()`, and polymorphic payload parser (URL stream vs base64 decode).
2. **Phase 2: Parallel Batch Dispatcher & Cancellation Coordinator**:
   - Build `dispatch_parallel_beats()` using `asyncio.gather` and `asyncio.Semaphore`.
   - Attach SIGINT signal listener to cancel in-flight cloud tasks on `Ctrl+C`.
3. **Phase 3: Visual Router & Studio CLI Integration (`core/visual_router.py`, `core/cli.py`)**:
   - Integrate parallel batch execution into `InteractiveDirector.synthesize_video()`.
   - Add `--backend` flag to CLI with options `[auto, serverless, pod, local]`.
   - Add cost report banner to output summary.
4. **Phase 4: Verification & Test Suite (`tests/test_runpod_serverless.py`)**:
   - Unit test payload parsing, status polling, timeout handling, and cancellation.
   - Verify full end-to-end regression across all existing 39 test cases.
