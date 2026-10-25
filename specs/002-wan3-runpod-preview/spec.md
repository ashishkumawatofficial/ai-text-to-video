# Feature Specification: Wan 3.0 ComfyUI Recipe, RunPod Integration, and Local Visual Mock Preview

**Feature Directory**: `specs/002-wan3-runpod-preview`

**Created**: 2026-10-23

**Status**: Draft

**Input**: User description: "Add Wan 3.0 Workflow Recipe: Add the ComfyUI API workflow mapping for Wan 3.0 (with Omni-Reference support for up to 10 character/scene images) into core/comfyui_workflows/. Setup RunPod Connection: Guide you through deploying the RunPod ComfyUI template (or Serverless endpoint) and setting your RUNPOD_COMFY_URL. Local Visual Mock Preview: Enable instant Text-to-Image scene illustration locally so you can see full visual storyboard videos on your Mac without waiting for a GPU pod."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Instant Local Visual Mock & Ken Burns Storyboard Generation (Priority: P1)

As a video creator working locally without an active cloud GPU pod, I want the studio to automatically generate high-definition visual keyframe illustrations for each scene beat and animate them with cinematic 2.5D camera motions (pan/zoom) and clean riddle puzzle plates, so that I can immediately preview a fully illustrated, moving video on my local machine in under 30 seconds at $0.00 cost.

**Why this priority**: Creators need immediate visual feedback and complete, watchable storyboard videos without requiring expensive cloud GPUs or complex remote infrastructure setup.

**Independent Test**: Run `python -m core.cli render --prompt "A clever cyber detective uncovers a secret data core in the rain"` with no GPU connected. The output video must contain vibrant illustrated scene backgrounds with continuous camera movement, kinetic subtitles, and synchronized audio, with zero blank placeholder plates.

**Acceptance Scenarios**:
1. **Given** a text prompt and no reachable ComfyUI server, **When** the render command executes, **Then** each storyboard beat receives an illustrated visual scene, rendered with smooth pan/zoom camera animation in the final MP4.
2. **Given** a riddle manifest with missing sprite files, **When** the riddle video is compiled, **Then** the system automatically generates deterministic, crisp vector/SVG puzzle assets (e.g. 6 glasses with liquid state) and a visual countdown ring rather than text placeholders.

---

### User Story 2 - Wan 3.0 Omni-Reference Video Generation Recipe (Priority: P2)

As a director producing narrative or action sequences, I want the video pipeline to support Wan 3.0 via an automated ComfyUI workflow recipe that accepts up to 10 reference images (character identity, wardrobe, setting, start/end frames), so that my generated scenes maintain character continuity and cinematic realism across extended continuous durations up to 30 seconds.

**Why this priority**: Wan 3.0 provides state-of-the-art multi-asset conditioning and native long-form generation, eliminating the need to stitch fragmented 3-second clips and solving character identity drift.

**Independent Test**: Dispatch a multi-scene beat with 3 character reference images to the Wan 3.0 workflow recipe. The resulting ComfyUI payload must correctly map all image references into the multi-conditioning nodes and produce continuous video output matching the specified duration.

**Acceptance Scenarios**:
1. **Given** a storyboard beat with multiple character profile images and reference plates, **When** visual routing dispatches to Wan 3.0, **Then** the workflow dynamically populates up to 10 image slots and formats the visual prompt with reference tags.
2. **Given** a target beat duration between 2 and 30 seconds, **When** the workflow is queued, **Then** Wan 3.0 generates the entire continuous scene at the requested frame length.

---

### User Story 3 - RunPod Cloud Connection & Health Diagnostics (Priority: P3)

As a creator connecting to cloud GPU resources, I want a dedicated CLI diagnostic command that verifies the health of my RunPod ComfyUI or Serverless endpoint, reports network latency, detects available VRAM, and lists loaded model checkpoints, so that I can verify my remote inference setup before kicking off heavy rendering jobs.

**Why this priority**: Prevents silent job failures, provides clear feedback on connection issues, and gives creators confidence that their cloud GPU is ready.

**Independent Test**: Run `python -m core.cli health`. The CLI outputs clear connection status, ping latency, GPU specifications, and lists whether Wan 3.0 or fallback models are loaded.

**Acceptance Scenarios**:
1. **Given** a valid and reachable `RUNPOD_COMFY_URL`, **When** `python -m core.cli health` is run, **Then** it prints a green healthy status report displaying server uptime, GPU model, available VRAM, and loaded model checkpoints.
2. **Given** an invalid or offline URL, **When** the health check is run, **Then** it prints a clear diagnostic error message with actionable troubleshooting steps.

---

### Edge Cases

- **ComfyUI Server Timeout or Disconnect**: If a remote GPU pod disconnects mid-generation or times out during a long render, the system MUST gracefully log the failure, switch the affected beat to the local visual mock generator, and complete the video render rather than aborting.
- **Reference Image Over-Subscription**: If a storyboard beat supplies more than 10 reference images, the pipeline MUST prioritize character identity anchors first, followed by start/end frames, truncating lowest-priority background references to avoid workflow crashes.
- **Network Rate Limits on Local Keyframing**: If local text-to-image keyframing encounters an offline network state or rate limit, the pipeline MUST fall back to procedural SVG/canvas gradient mood backgrounds with thematic typography.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide an automated local visual generator that generates high-definition keyframe imagery for every storyboard beat when remote diffusion inference is unconfigured or unreachable.
- **FR-002**: The video compositor MUST apply continuous 2.5D camera motion (smooth pan, zoom, or dolly) to static visual keyframes in narrative scenes, preventing static freeze-frames.
- **FR-003**: The riddle composition template MUST render deterministic visual puzzle assets (including glasses, liquid levels, and animated countdown indicators) regardless of external image asset availability.
- **FR-004**: The system MUST include a validated ComfyUI API workflow recipe for Wan 3.0 supporting up to 10 reference image conditioning inputs.
- **FR-005**: The visual router MUST dynamically map character identity images, scene references, and start/end frames into the Wan 3.0 multi-reference slots.
- **FR-006**: The pipeline MUST support continuous scene generation durations from 2 up to 30 seconds for Wan 3.0 workflows.
- **FR-007**: The CLI MUST provide a `health` subcommand to test connectivity to the configured RunPod ComfyUI or Serverless endpoint.
- **FR-008**: The health check command MUST report ping latency, server accessibility, and GPU memory metrics.
- **FR-009**: The system MUST support an environment variable `RUNPOD_COMFY_URL` to configure the remote inference host.
- **FR-010**: The pipeline MUST log clear notifications whenever falling back from cloud diffusion to local visual mock rendering.

---

### Key Entities

- **VisualStoryboardBeat**: An individual scene unit containing timing, dialogue, visual description, camera dynamics, and assigned reference images.
- **ImageReferenceCollection**: An ordered list of up to 10 images tagged by semantic role (character face, wardrobe, scene background, start frame, end frame).
- **ModelWorkflowRecipe**: A modular JSON node graph template defining inference parameters, model checkpoints, and conditioning inputs for ComfyUI.
- **InferenceEndpointHealth**: Status data capturing reachability, round-trip latency, GPU model name, free VRAM, and loaded model weights.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A prompt-to-video render run locally without GPU completes in under **30 seconds** with 100% of scenes visually illustrated (zero blank placeholder plates).
- **SC-002**: Static visual keyframes exhibit visible, smooth continuous camera motion (pan/zoom) across 100% of their duration frames in Remotion.
- **SC-003**: The Wan 3.0 workflow recipe accepts and correctly binds between 1 and 10 reference images without graph serialization errors.
- **SC-004**: The `health` command returns a diagnostic report within **3 seconds** when querying a responsive cloud endpoint.
- **SC-005**: In the event of remote cloud failure, the pipeline falls back to local visual generation without crashing, achieving a **100% render completion rate**.

---

## Assumptions

- Local text-to-image preview utilizes lightweight, unmetered web or local synthesis endpoints requiring zero API keys for basic storyboard drafting.
- Users deploying RunPod ComfyUI instances have access to an NVIDIA GPU pod (RTX 4090 or higher) with at least 24 GB of VRAM for Wan 3.0 FP8 inference.
- Video aspect ratio defaults to 9:16 vertical (1080x1920) for mobile short-form video unless explicitly overridden in the storyboard manifest.
