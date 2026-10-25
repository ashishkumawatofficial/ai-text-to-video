# Data Model: RunPod Serverless Parallel Video Pipeline

**Feature Branch**: `005-runpod-serverless-pipeline`  
**Date**: 2026-10-24  
**Author**: Antigravity Studio Engine Team  

---

## 1. Domain Enums

### `BackendExecutionStrategy`
Defines the visual rendering engine target selected by the user or auto-router.
```python
from enum import Enum

class BackendExecutionStrategy(str, Enum):
    AUTO = "auto"              # Try Serverless -> Dedicated Pod -> Local Mock
    SERVERLESS = "serverless"  # RunPod Serverless (Parallel on-demand workers)
    POD = "pod"                # RunPod Dedicated ComfyUI Pod (Direct HTTP 8188)
    LOCAL = "local"            # Local High-Definition Keyframe Plate (Zero GPU)
```

### `ServerlessJobStatus`
Represents the lifecycle state of an individual cloud worker job.
```python
class ServerlessJobStatus(str, Enum):
    IN_QUEUE = "IN_QUEUE"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"
```

---

## 2. Core Entities & Schemas

### `ServerlessConfig`
Configuration parameters for connecting and executing against RunPod Serverless.
```python
from pydantic import BaseModel, Field
from typing import Optional

class ServerlessConfig(BaseModel):
    endpoint_id: str = Field(description="RunPod serverless endpoint ID (e.g., 'v2-xxxxxx')")
    api_key: str = Field(description="RunPod User API Key")
    timeout_sec: int = Field(default=600, ge=30, le=1800, description="Max polling timeout in seconds per worker")
    poll_interval_sec: float = Field(default=2.5, ge=1.0, le=10.0, description="Delay between status polls")
    max_concurrency: int = Field(default=4, ge=1, le=16, description="Max concurrent serverless worker requests")
    gpu_tier_rate_per_sec: float = Field(default=0.00021, description="USD rate per GPU second (default RTX 4090)")
```

### `ServerlessJob`
Represents a single narrative beat submitted to a serverless worker.
```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class ServerlessJob(BaseModel):
    job_id: str = Field(description="RunPod serverless task ID")
    beat_index: int = Field(description="0-indexed scene beat order in director plan")
    beat_name: str = Field(description="Descriptive beat title")
    status: ServerlessJobStatus = Field(default=ServerlessJobStatus.IN_QUEUE)
    execution_time_ms: float = Field(default=0.0, description="Reported GPU compute time in milliseconds")
    output_video_path: Optional[str] = Field(default=None, description="Local downloaded MP4 file path")
    error_message: Optional[str] = Field(default=None, description="Error detail if status == FAILED")
    submitted_at: float = Field(description="Unix timestamp when job was queued")
    completed_at: Optional[float] = Field(default=None, description="Unix timestamp when job completed")
```

### `ServerlessCostReport`
Financial and performance accounting for a completed multi-beat production run.
```python
class ServerlessCostReport(BaseModel):
    total_beats: int
    successful_beats: int
    wall_clock_duration_sec: float = Field(description="Real-world elapsed time from dispatch to final download")
    cumulative_gpu_seconds: float = Field(description="Sum of all individual worker execution times")
    estimated_cost_usd: float = Field(description="Calculated dollar cost based on active compute seconds")
    effective_concurrency: float = Field(description="cumulative_gpu_seconds / wall_clock_duration_sec")
```

### `ServerlessBatchSession`
Orchestrator context coordinating parallel multi-worker execution.
```python
from typing import List

class ServerlessBatchSession(BaseModel):
    session_id: str
    project_id: str
    config: ServerlessConfig
    jobs: List[ServerlessJob] = Field(default_factory=list)
    cost_report: Optional[ServerlessCostReport] = None
```

---

## 3. State Transitions

```text
[Start Dispatch] 
       │
       ▼
 [IN_QUEUE] ──────────(Worker Available)──────────► [IN_PROGRESS]
       │                                                 │
       ├─(Cancel Request)──► [CANCELLED]                 ├─(Worker Success)─► [COMPLETED]
       └─(Wait > Timeout)──► [TIMED_OUT]                 ├─(CUDA Error)─────► [FAILED]
                                                         └─(Cancel Request)─► [CANCELLED]
```
