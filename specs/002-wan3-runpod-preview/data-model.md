# Phase 1 Data Model: Wan 3.0 ComfyUI Recipe, RunPod Integration, and Local Visual Mock Preview

**Feature**: `specs/002-wan3-runpod-preview`  
**Date**: 2026-10-23  
**Status**: Completed  

---

## Domain Entities & Schema Definitions

### 1. `Wan3WorkflowConfig` (Pydantic Model)

Represents parameters passed to the Wan 3.0 ComfyUI workflow template.

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class Wan3WorkflowConfig(BaseModel):
    model_checkpoint: str = Field(default="wan3.0_i2v_14b_fp8.safetensors")
    prompt: str = Field(description="Visual motion prompt describing scene action")
    negative_prompt: str = Field(default="blurry, low quality, distorted anatomy, jitter, artifacts")
    width: int = Field(default=720, ge=480, le=1920)
    height: int = Field(default=1280, ge=480, le=1920)
    duration_frames: int = Field(default=150, ge=30, le=900, description="1s to 30s @ 30fps")
    steps: int = Field(default=25, ge=10, le=50)
    cfg: float = Field(default=6.5, ge=1.0, le=15.0)
    seed: int = Field(default=42)
    reference_images: List[str] = Field(
        default_factory=list,
        max_length=10,
        description="Up to 10 image paths for character/scene conditioning"
    )
    motion_bucket_id: Optional[int] = Field(default=127, ge=1, le=255)
```

---

### 2. `RunPodHealthReport` (Pydantic Model)

Represents diagnostic connection results returned by `core/runpod_client.py` and CLI `health`.

```python
class RunPodHealthReport(BaseModel):
    url: str
    is_reachable: bool
    latency_ms: float
    gpu_name: Optional[str] = None
    vram_total_gb: Optional[float] = None
    vram_free_gb: Optional[float] = None
    comfyui_version: Optional[str] = None
    available_checkpoints: List[str] = Field(default_factory=list)
    has_wan3: bool = False
    has_wan2: bool = False
    has_ipadapter: bool = False
    status_summary: str
```

---

### 3. `LocalKeyframeAsset` (Pydantic Model)

Represents locally cached visual illustrations generated when remote diffusion is offline.

```python
class LocalKeyframeAsset(BaseModel):
    scene_id: str
    prompt: str
    cache_path: str
    width: int = 1080
    height: int = 1920
    is_cached: bool = False
    source_generator: str = Field(default="local_mock")
```

---

### 4. `KenBurnsAnimationProps` (Remotion Model)

Configuration for 2.5D camera zoom and pan applied to static plates in `StoryTemplate.tsx`.

```typescript
export interface KenBurnsAnimationProps {
  startScale: number; // e.g. 1.0
  endScale: number;   // e.g. 1.12
  startXPercent: number; // e.g. 0%
  endXPercent: number;   // e.g. -3%
  startYPercent: number; // e.g. 0%
  endYPercent: number;   // e.g. 2%
  direction: 'in' | 'out' | 'pan_left' | 'pan_right';
}
```
