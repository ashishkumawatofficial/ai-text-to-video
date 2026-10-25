# Quickstart & Verification Guide: RunPod Serverless Parallel Video Pipeline

**Feature Branch**: `005-runpod-serverless-pipeline`  
**Date**: 2026-10-24  

---

## Prerequisites & Environment Setup

Ensure your `.env` contains your RunPod credentials:
```env
RUNPOD_API_KEY=rpa_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
RUNPOD_SERVERLESS_ENDPOINT_ID=v2-xxxxxx
MAX_SERVERLESS_CONCURRENCY=4
COMFY_TIMEOUT_SEC=600
```

---

## Scenario 1: Serverless Health & Endpoint Inspection
Validates that the serverless endpoint is reachable, configured, and responsive before triggering renders.

```bash
python -c "
from core.runpod_serverless import check_serverless_health

health = check_serverless_health()
print('Endpoint ID:', health.endpoint_id)
print('Status:', health.status)
print('Workers Idle:', health.workers_idle)
print('Workers Running:', health.workers_running)
"
```
**Expected Outcome**:
```text
Endpoint ID: v2-xxxxxx
Status: HEALTHY
Workers Idle: 1
Workers Running: 0
```

---

## Scenario 2: Single-Beat Serverless Test Run
Dispatches one test beat to verify ComfyUI workflow execution, status polling, and MP4 download from the cloud worker.

```bash
python -c "
from core.runpod_serverless import RunPodServerlessClient
from core.models import Wan3WorkflowConfig
from core.runpod_client import build_wan3_workflow_payload

client = RunPodServerlessClient()
cfg = Wan3WorkflowConfig(prompt='A neon cybernetic drone flying through Tokyo rain', duration_frames=17)
workflow = build_wan3_workflow_payload(cfg)

output_path = client.execute_video_job(workflow, 'outputs/test_serverless_single.mp4')
print('Video successfully downloaded to:', output_path)
"
```
**Expected Outcome**:
```text
[RunPod Serverless] Submitting job to endpoint v2-xxxxxx...
[RunPod Serverless] Job queued: job_78ab9c (Status: IN_QUEUE)
[RunPod Serverless] Worker assigned: Status: IN_PROGRESS (Execution: 12.4s)
[RunPod Serverless] Job completed in 68.2s. Downloading MP4...
Video successfully downloaded to: outputs/test_serverless_single.mp4
```

---

## Scenario 3: Full 4-Beat Parallel Cinematic Diffusion (The Benchmark)
Executes a multi-beat cinematic story using `--backend serverless` to verify all beats dispatch and render concurrently.

```bash
python -m core.cli direct \
  --prompt "Cyberpunk detective in neon-lit Tokyo alleyway" \
  --aspect-ratio 16:9 \
  --backend serverless \
  --auto-approve
```
**Expected Outcome**:
```text
🚀 Auto-Approve enabled. Proceeding directly to master video synthesis...
🎙️ Synthesizing Voiceover & Extracting Subtitle Timestamps...
🎨 Routing Visual Scenes via Tri-Strategy Engine (Backend: SERVERLESS)...
   ⚡ [Parallel Dispatch] Launching 4 concurrent cloud worker jobs...
   ├── [Beat 1] Job job_01: IN_PROGRESS
   ├── [Beat 2] Job job_02: IN_PROGRESS
   ├── [Beat 3] Job job_03: IN_PROGRESS
   └── [Beat 4] Job job_04: IN_PROGRESS

   [All 4 Beats Completed in 84.3s wall-clock time!]
   💰 Total GPU Compute: 312.8s | Estimated Cost: $0.065 USD
🚀 Compiling Master Video in Remotion ➔ outputs/final_video.mp4
✅ Video Production Complete! File: outputs/final_video.mp4 (14.1 MB in 112.5s)
```
*Benchmark Target*: Under 180 seconds total turnaround (compared to > 2,400s on sequential dedicated pod).

---

## Scenario 4: Resilient Auto-Failover Verification
Verifies that if Serverless experiences a transient outage or capacity limits, the engine gracefully falls back to the dedicated pod or local plates with zero crashes.

```bash
python -c "
from core.visual_router import route_and_execute_beat
from core.models import SceneBeat, ImageRole

beat = SceneBeat(
    name='Test Failover Beat',
    duration_sec=3.0,
    visual_prompt='An astronaut walking on neon red sand',
    dialogue_text='Testing fallback resiliency'
)

# Simulate offline serverless endpoint
result = route_and_execute_beat(beat, 'outputs/test_failover.mp4', backend='auto', force_serverless_error=True)
print('Result produced cleanly via fallback:', result)
"
```
**Expected Outcome**:
```text
⚠️ Serverless execution unavailable (Capacity Limit / Connection Error). Cascading to Tier 2: Dedicated Pod.
✅ Video generated cleanly via fallback.
```

---

## Scenario 5: User Interrupt & Instant Cloud Cancellation
Verifies that pressing `Ctrl+C` halts local processing and immediately cancels in-flight jobs on RunPod so no user credits are burned.

```bash
# In terminal, launch direct command and hit Ctrl+C after 5 seconds:
python -m core.cli direct --prompt "High speed hoverbike chase" --backend serverless --auto-approve
```
**Expected Outcome**:
```text
^C
🛑 Caught interrupt signal (SIGINT). Cancelling 4 in-flight serverless cloud jobs...
   [Cancelled job_01] ✅
   [Cancelled job_02] ✅
   [Cancelled job_03] ✅
   [Cancelled job_04] ✅
All cloud workers terminated cleanly. Zero orphaned GPU billing.
```
