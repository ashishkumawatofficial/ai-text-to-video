# Phase 0 Research: Wan 3.0 ComfyUI Recipe, RunPod Integration, and Local Visual Mock Preview

**Feature**: `specs/002-wan3-runpod-preview`  
**Date**: 2026-10-23  
**Status**: Completed  

---

## Technical Decisions & Architecture Findings

### Decision 1: Wan 3.0 ComfyUI API Graph Schema & Omni-Reference Mapping

- **Context**: Wan 3.0 supports multi-modal Omni-Referencing (feeding up to 10 character, setting, wardrobe, and anchor images using `@` reference syntax) and long-duration continuous video generation (up to 30 seconds / 900 frames @ 30fps).
- **Decision**: Design `core/workflows/wan3_omni_reference.json` as a standardized ComfyUI API execution graph with:
  1. `WanVideoCheckpointLoader` pointing to `wan3.0_i2v_14b_fp8.safetensors` (or fallback `wan2.1_i2v_14b`).
  2. A dedicated `BatchImageLoader` / `MultiReferenceLoader` supporting up to 10 image paths dynamically mapped into Wan 3.0's multi-conditioning latent cross-attention layer.
  3. `EmptyWanLatentVideo` allowing parameterization of `width: 720` (or `1080`), `height: 1280` (or `1920`), and `length: duration_frames` (up to 900 frames).
  4. Video export node `VHS_VideoCombine` encoding H.264 MP4 with constant rate factor (CRF: 19) for Remotion ingestion.
- **Alternatives Considered**:
  - *Hardcoded single-image IP-Adapter*: Rejected because it restricts character continuity to 1 image and does not support Wan 3.0's native multi-asset `@` tagging.
  - *Third-party proprietary API wrapper*: Rejected to preserve our zero-cost, unmetered self-hosted GPU architecture.

---

### Decision 2: RunPod Remote Diagnostics & Connection Protocol

- **Context**: Content creators need instant visibility into whether their RunPod ComfyUI pod or Serverless endpoint is online, reachable, has sufficient VRAM, and contains the required Wan 3.0 weights before triggering video jobs.
- **Decision**: Implement a lightweight diagnostic probe in `core/runpod_client.py` invoked via `python -m core.cli health`:
  1. Probe `GET {base_url}/system_stats` to verify HTTP connectivity and calculate network round-trip latency in milliseconds.
  2. Parse the returned hardware payload for `devices[0].name` (e.g. `NVIDIA GeForce RTX 4090`), `vram_total`, and `vram_free`.
  3. Probe `GET {base_url}/object_info/CheckpointLoaderSimple` to list all available checkpoint filenames on the server and check if `wan3` or `wan2` is loaded.
  4. Output a clear terminal table and return exit code 0 (healthy) or 1 (offline/error).
- **Alternatives Considered**:
  - *Running a test render on startup*: Rejected because generating a test video takes 15–30s and wastes GPU compute unnecessarily.

---

### Decision 3: Local Visual Mock Keyframe Engine (Zero-GPU Fallback)

- **Context**: When creators run `--prompt` on Mac or without an active cloud GPU, the pipeline must never output blank black placeholder plates (`Scene: scene_1`).
- **Decision**: Implement `core/local_visual_mock.py`:
  1. Primary Provider: Lightweight Text-to-Image synthesis using an unmetered, public gateway (Pollinations AI / HuggingFace public inference endpoint) with fallback to deterministic prompt-hashed procedural scene plates.
  2. Local File Cache: Cache generated keyframe illustrations in `outputs/temp/keyframe_{hash}.jpg` so repeated renders never re-download or re-generate existing scene artwork.
  3. Seamless Bridge: Inject the generated keyframe path as the scene beat's `mediaSrc` in `core/remotion_bridge.py`.
- **Alternatives Considered**:
  - *Local SDXL on Mac*: Takes 45–90s per image on M1/M2/M3 using CoreML and requires 6GB download.
  - *Static colored rectangles*: Rejected because it fails the aesthetic WOW factor rule.

---

### Decision 4: Remotion 2.5D Ken Burns Camera Pan & Zoom

- **Context**: Static image plates feel lifeless in narrative stories. A cinematic story needs continuous motion.
- **Decision**: Update `remotion/src/templates/StoryTemplate.tsx`:
  1. Use Remotion's `interpolate()` and `useCurrentFrame()` to calculate continuous scaling (from `scale(1.0)` to `scale(1.12)`) and slow directional panning (`translateX` and `translateY` offset by 2–4%).
  2. Add subtle vignette and atmospheric particle layers so every keyframe feels alive and dynamic.
- **Alternatives Considered**:
  - *3D WebGL mesh displacement*: Overkill for 2D keyframe storytelling and increases headless render times.

---

### Decision 5: Deterministic Riddle Puzzle Asset Synthesis

- **Context**: The riddle manifest pointed to `assets/processed/reference_1080.png`, which was removed during workspace cleanup, causing the riddle video to render a plain placeholder box.
- **Decision**:
  1. Provide a clean, high-resolution procedural generator in `scripts/generate_riddle_assets.py` that builds the 9:16 reference plate depicting the 6 glasses (Glasses 1, 2, 3 full with blue liquid; Glasses 4, 5, 6 empty with clear reflections) at 1080x1920.
  2. In `remotion/src/templates/RiddleTemplate.tsx`, enhance the fallback so if an image path is missing, it renders an inline SVG layout of the 6 glasses directly in React, guaranteeing 100% visual uptime with 0% chance of a blank screen.
