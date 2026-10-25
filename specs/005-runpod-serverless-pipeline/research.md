# Research & Technical Decisions: RunPod Serverless Parallel Video Pipeline

**Feature Branch**: `005-runpod-serverless-pipeline`  
**Date**: 2026-10-24  
**Author**: Antigravity Studio Engine Team  

---

## 1. RunPod Serverless REST API Architecture

### Context
Dedicated RunPod pods expose ComfyUI directly on an HTTP port (e.g., port 8188 via proxy), requiring long-running instances billed 24/7. RunPod Serverless operates via a managed API Gateway with on-demand container orchestration, auto-scaling worker pools from 0 to N.

### Protocol Specification
- **Async Job Submission**:
  - `POST https://api.runpod.ai/v2/{endpoint_id}/run`
  - Headers: `Authorization: Bearer {RUNPOD_API_KEY}`, `Content-Type: application/json`
  - Body:
    ```json
    {
      "input": {
        "workflow": { ...comfyui_graph... },
        "images": []
      }
    }
    ```
  - Response: `{"id": "job_abc123", "status": "IN_QUEUE"}`
- **Job Status Polling**:
  - `GET https://api.runpod.ai/v2/{endpoint_id}/status/{job_id}`
  - Status lifecycle: `IN_QUEUE` ➔ `IN_PROGRESS` ➔ `COMPLETED` | `FAILED` | `CANCELLED` | `TIMED_OUT`
  - Execution runtime metrics included in response: `executionTime` (milliseconds).
- **Job Cancellation**:
  - `POST https://api.runpod.ai/v2/{endpoint_id}/cancel/{job_id}`
  - Immediately signals worker container to abort and halts credit deductions.

### Decision
Implement `RunPodServerlessClient` in `core/runpod_serverless.py` adhering to this official protocol, with async HTTP execution powered by standard library or lightweight `urllib`/`requests` wrappers with `asyncio.to_thread` to maintain zero external library bloat.

---

## 2. Parallel Multi-Beat Execution Engine

### Context
Multi-beat narrative stories (e.g., 4 beats, 20s total) currently render sequentially on 1 GPU pod (Clip 1 ➔ Clip 2 ➔ Clip 3 ➔ Clip 4), taking 25–40 minutes. Serverless allows concurrent horizontal scaling across multiple independent GPUs.

### Technical Approach
- **Concurrent Dispatch**:
  - Use `asyncio.gather` to launch all beat jobs simultaneously.
  - Employ an `asyncio.Semaphore(max_concurrency)` (default: 4, configurable via `MAX_SERVERLESS_CONCURRENCY`) to prevent overflowing account GPU limits if a project has 6+ beats.
- **Independent Asynchronous Polling**:
  - Each job is monitored via an independent polling coroutine.
  - As soon as Job $i$ completes, its video slice is downloaded immediately in the background rather than blocking on other workers.
- **Expected Turnaround**:
  - Sequential execution: $T_{\text{total}} = \sum_{i=1}^N T_i \approx 4 \times 90\text{s} = 360\text{s}$ (or up to 2,400s with heavy settings).
  - Parallel serverless execution: $T_{\text{total}} = \max(T_1, T_2, \dots, T_N) + T_{\text{remotion}} \approx 90\text{s} + 15\text{s} \approx 105\text{s}$!

---

## 3. Output Payload Normalization (Base64 vs Remote URL)

### Context
RunPod ComfyUI Serverless workers return generated video files in two possible schemas depending on container volume configuration:
1. **Direct Signed Storage URLs**: `{"output": {"videos": [{"url": "https://...", "filename": "wan2_video.mp4"}]}}`
2. **Base64 Encoded Strings**: `{"output": {"message": "data:video/mp4;base64,AAAA..."}}` or binary dictionaries.

### Decision
The response parser must support polymorphic output formats:
- If a URL is detected (starts with `http://` or `https://`), initiate a streaming download to `dest_path`.
- If a base64 string or data URI is detected, decode using `base64.b64decode` directly into `dest_path`.
- If an unhandled format or missing video output is returned, raise a descriptive `ServerlessOutputError` containing the raw output keys for fast diagnostics.

---

## 4. Dual-Mode Visual Router & Resilient Fallback Cascade

### Context
Studio reliability must remain 100% resilient. A cloud service outage, network drop, or serverless cold-start timeout must never ruin an active creative session.

### Cascade Hierarchy
```text
Tier 1: RunPod Serverless (Parallel, On-Demand, Pay-per-Second)
   │ (failover on 401, 404, 503, out-of-quota, or cold-start timeout)
   ▼
Tier 2: Dedicated RunPod Pod (Direct HTTP on port 8188)
   │ (failover on connection refused, offline pod, or CUDA OOM)
   ▼
Tier 3: Local Keyframe Engine (Zero-GPU deterministic high-definition plate)
```

### Decision
`VisualRouter` in `core/visual_router.py` will inspect `--backend` flag (`auto`, `serverless`, `pod`, `local`):
- `auto`: Tries Tier 1 ➔ Tier 2 ➔ Tier 3.
- `serverless`: Explicitly requires Tier 1, with automatic fallback to Tier 2 on failure.
- `pod`: Explicitly targets dedicated pod port 8188.
- `local`: Pure offline local preview (instant).

---

## 5. Graceful Cancellation & Signal Interception (`Ctrl+C`)

### Context
In serverless architectures, submitting a batch of jobs commits cloud workers. If a user presses `Ctrl+C` in their terminal, a naive client disconnects locally while cloud GPUs continue rendering in the background, wasting account credits.

### Decision
Register an `asyncio` SIGINT/SIGTERM handler in the batch coordinator:
1. Intercept `KeyboardInterrupt` / SIGINT.
2. Iterate through all tracked active `job_id`s in `IN_QUEUE` or `IN_PROGRESS` status.
3. Fire `POST /cancel/{job_id}` concurrently across all active jobs.
4. Print: `🛑 Caught interrupt. Successfully cancelled 3 in-flight Serverless worker jobs. Zero orphaned GPU billing.`
5. Exit cleanly with code 130.

---

## 6. Cost Accounting & Telemetry Calculation

### Rates
- Standard RunPod Serverless GPU rates (approximate):
  - **RTX 4090 (24GB)**: ~$0.00021 / sec (~$0.75 / hr)
  - **A100 (80GB)**: ~$0.00045 / sec (~$1.64 / hr)
  - **L40S (48GB)**: ~$0.00025 / sec (~$0.90 / hr)

### Calculation Formula
$$\text{Total Cost} = \sum_{i=1}^N \left( \frac{\text{executionTimeMs}_i}{1000} \times \text{RatePerSec} \right)$$
For a 4-beat video where each worker runs for 75 seconds on RTX 4090:
$$\text{Cost} = 4 \times 75 \times 0.00021 = \$0.063 \text{ USD!}$$
Display this cost metric prominently in the CLI completion summary table.
