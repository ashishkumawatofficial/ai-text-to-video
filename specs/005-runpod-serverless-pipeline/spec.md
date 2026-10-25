# Feature Specification: RunPod Serverless Parallel Video Generation Pipeline

**Feature Branch**: `005-runpod-serverless-pipeline`  
**Created**: 2026-10-24  
**Status**: Draft  
**Input**: User description: "let's onboard serverless in our system check all corners so less debugging we have to after implementation"

---

## Executive Summary
The studio currently renders multi-beat cinematic narratives sequentially on a single dedicated GPU pod, resulting in 25–40 minute completion cycles and ongoing idle pod costs. This feature introduces **RunPod Serverless Parallel Video Diffusion**, allowing all narrative beats of a video project to dispatch concurrently across independent, on-demand serverless GPU workers. All beats render in parallel within 2 to 3 minutes total, billed strictly per-second of active compute with zero idle overhead.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Parallel Multi-Beat Serverless Diffusion (Priority: P1 - MVP)
As a creator using the CLI studio, I want all narrative beats of my storyboard to render concurrently on independent serverless GPU workers so that my entire multi-scene video completes in under 3 minutes instead of 30+ minutes.

**Why this priority**: Solves the fundamental turnaround speed bottleneck (40m -> 3m) and enables cost-effective, per-second billing with zero idle spend.

**Independent Test**:
Can be verified by executing a 4-beat narrative with `--backend serverless`. The director dispatches 4 concurrent jobs to the serverless endpoint, polls their completion in parallel, downloads all 4 video slices, and compiles the final video in Remotion in under 180 seconds.

**Acceptance Scenarios**:
1. **Given** a story with 4 approved beats and a configured serverless endpoint, **When** visual routing begins, **Then** the director submits 4 asynchronous execution jobs concurrently rather than in single-file order.
2. **Given** in-flight serverless jobs, **When** polling execution status, **Then** status updates are fetched in parallel with non-blocking async loops until all jobs return `COMPLETED`.
3. **Given** all jobs complete successfully, **When** video assets are collected, **Then** all video slices are downloaded to local disk, mapped to the respective timeline beats, and compiled cleanly in Remotion without dropped frames.

---

### User Story 2 - Resilient Dual-Backend Routing & Auto-Failover (Priority: P2)
As a director, I want the system to seamlessly switch between Serverless, Dedicated Pod, and Local Mock backends with automatic failover so that temporary cloud timeouts, cold-start spikes, or network drops never abort my production run.

**Why this priority**: Cloud serverless environments occasionally experience capacity spikes or cold start delays; automatic fallback guarantees zero lost work.

**Independent Test**:
Can be verified by simulating a 503 or timeout on the serverless endpoint during beat generation; the system automatically falls back to an available dedicated pod or local keyframe synthesis without crashing.

**Acceptance Scenarios**:
1. **Given** `--backend auto` (default), **When** a serverless endpoint is configured and active, **Then** the engine defaults to parallel serverless execution.
2. **Given** the serverless endpoint returns an error (HTTP 500/503, out-of-capacity, or queue timeout), **When** a beat fails on serverless, **Then** the system logs an alert and cascades to the dedicated pod endpoint.
3. **Given** both serverless and dedicated pods are unavailable or unreachable, **When** generation is requested, **Then** the system engages the local high-definition keyframe plate engine with 0% crashes.

---

### User Story 3 - Multi-Worker Live Progress Telemetry & Safe Cancellation (Priority: P2)
As a creator watching the terminal, I want a live multi-worker progress display showing the real-time status of every beat and clean cancellation so that I always know what the workers are doing and never burn GPU credits if I cancel.

**Why this priority**: Long-running asynchronous operations without observability cause anxiety; uncontrolled cancellations burn user wallet credits.

**Independent Test**:
Can be verified by running a 4-beat job and pressing `Ctrl+C` in the CLI during active generation; all in-flight serverless jobs immediately receive cancellation requests on the cloud.

**Acceptance Scenarios**:
1. **Given** multiple active serverless jobs, **When** generation is in progress, **Then** the CLI renders a compact, multi-line status table updating worker states (`IN_QUEUE`, `IN_PROGRESS`, `COMPLETED`, `FAILED`).
2. **Given** an in-flight serverless generation session, **When** the user presses `Ctrl+C` (SIGINT), **Then** the client catches the signal, sends `/cancel` commands to all active job IDs, and gracefully terminates with a summary.

---

### User Story 4 - Cost Tracking & Per-Video Billing Transparency (Priority: P3)
As a creator or studio manager, I want to see the exact compute duration and dollar cost breakdown of each generated video so that I can budget and scale production predictably.

**Why this priority**: Provides complete cost transparency and proves ROI compared to dedicated hourly pods.

**Independent Test**:
Can be verified by completing any serverless generation; the CLI summary prints exact GPU execution seconds, worker count, and calculated USD cost based on the worker GPU tier.

**Acceptance Scenarios**:
1. **Given** completed serverless jobs with reported execution runtimes, **When** the video production completes, **Then** the summary displays total worker seconds and estimated cost in USD (e.g., `4 beats rendered concurrently in 82s | Total compute cost: $0.068 USD`).

---

## Edge Cases & Failure Recovery

1. **Cold Start Latency (> 60s)**:
   - RunPod serverless workers loading a 14B or 1.3B model from network storage during cold start may take 45–90s before entering `IN_PROGRESS`.
   - *Mitigation*: The client polling loop treats `IN_QUEUE` as normal up to a configurable cold-start threshold (default: 180s) before raising a timeout.
2. **Mixed Worker Speeds (Straggler Beat)**:
   - 3 beats complete in 70s, but 1 beat takes 110s due to worker scheduling jitter.
   - *Mitigation*: Video assembly waits asynchronously for all beats using `asyncio.as_completed` and streams downloads as each individual worker finishes, rather than waiting for the entire batch to download at once.
3. **Payload Format Variances (Base64 vs Direct S3/Storage URLs)**:
   - Serverless ComfyUI output payloads can return binary files either as base64-encoded strings or as hosted file URLs.
   - *Mitigation*: Output parser inspects the payload structure; if URL, it streams via HTTP GET; if base64, it decodes directly into the destination file path.
4. **Rate Limiting / Concurrency Cap**:
   - The user's RunPod account might have a maximum concurrent worker limit (e.g., 3 concurrent GPUs when the video has 5 beats).
   - *Mitigation*: The job dispatcher uses an `asyncio.Semaphore(max_concurrency)` to queue surplus beats without overflowing account limits.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support executing video diffusion workflows against RunPod Serverless endpoints via `/run` (async start), `/status/{id}` (polling), and `/cancel/{id}` (cancellation) endpoints.
- **FR-002**: System MUST dispatch all narrative beats in a storyboard concurrently using asynchronous non-blocking network calls.
- **FR-003**: System MUST provide a `--backend` CLI parameter with options `[serverless, pod, auto, local]` defaulting to `auto`.
- **FR-004**: In `auto` mode, the system MUST prioritize `serverless` if a valid endpoint ID is configured; if missing or unreachable, it MUST fall back to `pod`, and finally to `local`.
- **FR-005**: System MUST support parsing serverless ComfyUI responses returned as both hosted HTTP download URLs and base64 encoded media blobs.
- **FR-006**: System MUST enforce a configurable worker concurrency semaphore (`MAX_SERVERLESS_CONCURRENCY`, default: 4) to honor account limits.
- **FR-007**: System MUST intercept user interrupt signals (SIGINT / `Ctrl+C`) during serverless rendering and issue cloud cancellation requests for all outstanding job IDs.
- **FR-008**: System MUST measure worker execution runtimes and report the total GPU compute time and estimated cost in USD upon completion.
- **FR-009**: System MUST preserve 100% backward compatibility with existing dedicated ComfyUI pod workflows and Remotion rendering pipeline.
- **FR-010**: System MUST validate and sanitize input prompt payloads before submission to prevent serverless validation rejection.

---

### Key Entities

- **ServerlessJob**: Represents an individual beat dispatched to a serverless worker. Attributes: `job_id`, `beat_index`, `status` (`IN_QUEUE`, `IN_PROGRESS`, `COMPLETED`, `FAILED`, `CANCELLED`), `execution_time_sec`, `output_url`, `error_message`.
- **ServerlessBatchSession**: Aggregates all concurrent jobs for a video project. Attributes: `session_id`, `project_id`, `jobs: List[ServerlessJob]`, `total_compute_sec`, `estimated_cost_usd`, `start_time`, `end_time`.
- **BackendExecutionStrategy**: Enum determining the rendering target: `SERVERLESS`, `DEDICATED_POD`, `LOCAL_MOCK`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: **10x Turnaround Speedup**: A 4-beat cinematic video project renders all visual scenes in under 180 seconds total (compared to > 2,400 seconds on a single sequential pod).
- **SC-002**: **90%+ Cost Reduction**: Compute cost per 20-second video project on serverless stays under $0.10 USD (versus hourly dedicated pod burn).
- **SC-003**: **Zero-Crash Resilience**: System achieves 100% successful video compilation across 10 consecutive runs with 0 unhandled exceptions, falling back cleanly if the serverless endpoint is unavailable.
- **SC-004**: **Instant Cancellation**: Upon user SIGINT (`Ctrl+C`), 100% of in-flight serverless jobs receive cancellation requests within 3 seconds, preventing orphaned GPU billing.
- **SC-005**: **Zero Pipeline Regression**: 100% of existing tests pass with zero breaking changes to previous story writer, interactive director, and Remotion video synthesis modules.

---

## Assumptions

- The user provides `RUNPOD_API_KEY` and a configured `RUNPOD_SERVERLESS_ENDPOINT_ID` in `.env` (or via environment variable).
- The serverless endpoint runs a standard ComfyUI worker image (e.g., `runpod/worker-comfy:latest` or custom image) with the Wan 2.1 models available in container or attached network volume.
- The default target aspect ratio and workflow node definitions match the verified ComfyUI native format established in Feature 002/004.
- Network bandwidth is sufficient to stream concurrent MP4 downloads (~1–3 MB per beat).
